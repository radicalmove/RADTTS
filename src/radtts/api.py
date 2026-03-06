"""FastAPI service exposing RADTTS pipeline endpoints."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

from radtts.models import (
    CaptionRequest,
    ClipRequest,
    PauseConfig,
    ProjectReferenceAudioUploadRequest,
    ProjectCreateRequest,
    SimpleSynthesisRequest,
    SynthesisRequest,
    TranscribeRequest,
    WorkerInviteRequest,
    WorkerInviteResponse,
    WorkerJobCompleteRequest,
    WorkerJobFailRequest,
    WorkerPullRequest,
    WorkerPullResponse,
    WorkerRegisterRequest,
    WorkerSynthesisEnqueueRequest,
)
from radtts.pipeline import RADTTSPipeline
from radtts.constants import DEFAULT_PRESETS, MODEL_MODE_ALIASES, SUPPORTED_BASE_MODELS
from radtts.worker_manager import WorkerManager
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
    from starlette.middleware.sessions import SessionMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is not installed. Install with 'pip install -e .[api]'.") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


PROJECTS_ROOT = Path(os.environ.get("RADTTS_PROJECTS_ROOT", "projects"))
MODULE_ROOT = Path(__file__).resolve().parent
AUTH_REQUIRED = _env_bool("RADTTS_AUTH_REQUIRED", False)
SESSION_SECRET = os.environ.get("RADTTS_SESSION_SECRET", "radtts-dev-session-secret")
SESSION_SECURE = _env_bool("RADTTS_SESSION_SECURE", False)
PSYCHEK_LOGIN_URL = os.environ.get("PSYCHEK_LOGIN_URL", "http://127.0.0.1:8000/login")
BRIDGE_SECRET = os.environ.get("RADTTS_BRIDGE_SECRET", SESSION_SECRET)
BRIDGE_MAX_AGE_SECONDS = int(os.environ.get("RADTTS_BRIDGE_MAX_AGE_SECONDS", "120"))
WORKER_SECRET = os.environ.get("RADTTS_WORKER_SECRET", SESSION_SECRET)
WORKER_INVITE_MAX_AGE_SECONDS = int(os.environ.get("RADTTS_WORKER_INVITE_MAX_AGE_SECONDS", "86400"))
SCOPE_PROJECTS_BY_USER = _env_bool("RADTTS_SCOPE_PROJECTS_BY_USER", True)


def _infer_psychek_admin_url(login_url: str) -> str:
    cleaned = login_url.strip()
    if cleaned.endswith("/login"):
        return f"{cleaned[:-len('/login')]}/admin"
    return f"{cleaned.rstrip('/')}/admin"


PSYCHEK_ADMIN_URL = os.environ.get("PSYCHEK_ADMIN_URL", "").strip() or _infer_psychek_admin_url(PSYCHEK_LOGIN_URL)

pipeline = RADTTSPipeline(projects_root=PROJECTS_ROOT)
worker_manager = WorkerManager(
    projects_root=PROJECTS_ROOT,
    worker_secret=WORKER_SECRET,
    invite_max_age_seconds=WORKER_INVITE_MAX_AGE_SECONDS,
)
app = FastAPI(title="RADTTS API", version="0.1.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=SESSION_SECURE,
)
app.mount("/static", StaticFiles(directory=MODULE_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(MODULE_ROOT / "templates"))


def _bridge_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(BRIDGE_SECRET, salt="app-bridge-radtts-v1")


def _current_user(request: Request) -> dict | None:
    user = request.session.get("user")
    if isinstance(user, dict):
        return user
    return None


def _require_auth(request: Request) -> None:
    if AUTH_REQUIRED and _current_user(request) is None:
        raise HTTPException(status_code=401, detail="authentication required")


def _login_redirect() -> RedirectResponse:
    query = urlencode({"target_app": "radtts"})
    separator = "&" if "?" in PSYCHEK_LOGIN_URL else "?"
    return RedirectResponse(f"{PSYCHEK_LOGIN_URL}{separator}{query}", status_code=302)


def _scope_prefix(request: Request) -> str | None:
    user = _current_user(request)
    if not user:
        return None
    sub = str(user.get("sub") or "").strip()
    email = str(user.get("email") or "").strip().lower()
    identity = f"{sub}|{email}".strip("|")
    if not identity:
        return None
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"u{digest}"


def _current_user_key_and_label(request: Request) -> tuple[str | None, str | None]:
    user = _current_user(request)
    if not user:
        return None, None

    user_key = _scope_prefix(request)
    if not user_key:
        return None, None

    label = str(user.get("display_name") or user.get("email") or user.get("sub") or user_key).strip()
    return user_key, label or user_key


def _scope_project_id(request: Request, project_id: str) -> str:
    if not SCOPE_PROJECTS_BY_USER:
        return project_id
    prefix = _scope_prefix(request)
    if not prefix:
        return project_id
    scoped = f"{prefix}__{project_id}"
    if project_id.startswith(f"{prefix}__"):
        return project_id
    return scoped


def _descope_project_id(request: Request, project_id: str) -> str:
    if not SCOPE_PROJECTS_BY_USER:
        return project_id
    prefix = _scope_prefix(request)
    if not prefix:
        return project_id
    marker = f"{prefix}__"
    if project_id.startswith(marker):
        return project_id[len(marker):]
    return project_id


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "reference_audio.wav"


def _safe_audio_extension(filename: str) -> str:
    suffix = Path(_safe_filename(filename)).suffix.lower()
    if suffix in {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}:
        return suffix
    return ".wav"


def _slug_text(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower())
    return slug.strip("-")


def _build_output_name(text: str, output_name: str | None) -> str:
    if output_name and output_name.strip():
        raw = output_name.strip()
    else:
        prefix = _slug_text(" ".join(text.split()[:8]))[:32] or "generated-audio"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        raw = f"{prefix}-{stamp}"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("._-")
    return cleaned or f"generated-audio-{uuid.uuid4().hex[:8]}"


def _inject_fillers(text: str, *, add_ums: bool, add_ahs: bool) -> str:
    filler_pool: list[str] = []
    if add_ums:
        filler_pool.append("Um,")
    if add_ahs:
        filler_pool.append("Ah,")
    if not filler_pool:
        return text

    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    if len(parts) <= 1:
        return text
    rng = random.Random(hashlib.sha256(text.encode("utf-8")).hexdigest())
    patched: list[str] = []
    for idx, sentence in enumerate(parts):
        if idx > 0 and len(sentence) > 20 and rng.random() < 0.22:
            filler = filler_pool[rng.randrange(len(filler_pool))]
            patched.append(f"{filler} {sentence}")
        else:
            patched.append(sentence)
    return " ".join(patched)


def _reference_cache_file(project_manifests_dir: Path) -> Path:
    return project_manifests_dir / "reference_audio_cache.json"


def _load_reference_cache(project_manifests_dir: Path) -> dict[str, dict[str, str]]:
    cache_path = _reference_cache_file(project_manifests_dir)
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, dict[str, str]] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, dict):
            normalized[key] = {str(k): str(v) for k, v in value.items() if isinstance(k, str)}
    return normalized


def _write_reference_cache(project_manifests_dir: Path, cache: dict[str, dict[str, str]]) -> None:
    cache_path = _reference_cache_file(project_manifests_dir)
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _resolve_reference_audio_path(project_root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    try:
        candidate = Path(raw_path).resolve()
    except Exception:  # noqa: BLE001
        return None
    try:
        candidate.relative_to(project_root)
    except ValueError:
        return None
    if not candidate.exists():
        return None
    return candidate


def _project_cache_entries(
    request: Request,
    *,
    scoped_project_id: str,
) -> list[dict[str, str | bool]]:
    paths = pipeline.project_manager.get_paths(scoped_project_id)
    project_root = paths.root.resolve()
    if not project_root.exists():
        return []

    cache = _load_reference_cache(paths.manifests)
    visible_project_id = _descope_project_id(request, scoped_project_id)
    items: list[dict[str, str | bool]] = []

    for audio_hash, entry in cache.items():
        if not isinstance(audio_hash, str) or not isinstance(entry, dict):
            continue

        reference_path = _resolve_reference_audio_path(project_root, entry.get("audio_path"))
        if reference_path is None:
            continue

        source_filename = str(entry.get("source_filename") or reference_path.name)
        updated_at = str(entry.get("updated_at") or entry.get("reference_text_updated_at") or "")
        owner_key = str(entry.get("owner_key") or "")
        owner_label = str(entry.get("owner_label") or "")
        saved_path = str(entry.get("audio_path") or reference_path)
        artifact_url = f"/projects/{visible_project_id}/artifact?path={quote(str(reference_path), safe='')}"
        items.append(
            {
                "audio_hash": audio_hash,
                "source_filename": source_filename,
                "saved_path": saved_path,
                "updated_at": updated_at,
                "has_reference_text": bool(str(entry.get("reference_text") or "").strip()),
                "artifact_url": artifact_url,
                "project_id": visible_project_id,
                "owner_key": owner_key,
                "owner_label": owner_label,
            }
        )
    return items


def _find_reference_audio_for_hash(
    request: Request,
    *,
    scoped_project_id: str,
    audio_hash: str,
) -> tuple[dict[str, str], Path, str] | None:
    # 1) Prefer current project cache so team samples in project remain usable.
    current_paths = pipeline.project_manager.get_paths(scoped_project_id)
    current_entry = _load_reference_cache(current_paths.manifests).get(audio_hash)
    if isinstance(current_entry, dict):
        current_path = _resolve_reference_audio_path(current_paths.root.resolve(), current_entry.get("audio_path"))
        if current_path is not None:
            return ({str(k): str(v) for k, v in current_entry.items()}, current_path, scoped_project_id)

    # 2) Fallback: same user can reuse samples from their other projects.
    user_key, _ = _current_user_key_and_label(request)
    if not user_key:
        return None

    for candidate_project_id in pipeline.list_projects():
        if candidate_project_id == scoped_project_id:
            continue
        candidate_paths = pipeline.project_manager.get_paths(candidate_project_id)
        candidate_entry = _load_reference_cache(candidate_paths.manifests).get(audio_hash)
        if not isinstance(candidate_entry, dict):
            continue
        candidate_owner_key = str(candidate_entry.get("owner_key") or "")
        legacy_owner_match = not candidate_owner_key and candidate_project_id.startswith(f"{user_key}__")
        if candidate_owner_key != user_key and not legacy_owner_match:
            continue
        candidate_path = _resolve_reference_audio_path(candidate_paths.root.resolve(), candidate_entry.get("audio_path"))
        if candidate_path is None:
            continue
        return ({str(k): str(v) for k, v in candidate_entry.items()}, candidate_path, candidate_project_id)
    return None


@app.get("/auth/bridge")
def auth_bridge(request: Request, token: str):
    try:
        payload = _bridge_serializer().loads(token, max_age=BRIDGE_MAX_AGE_SECONDS)
    except SignatureExpired as exc:
        raise HTTPException(status_code=401, detail="bridge token expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="invalid bridge token") from exc

    request.session["user"] = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "display_name": payload.get("display_name"),
        "is_admin": bool(payload.get("is_admin", False)),
        "issuer": payload.get("issuer"),
    }
    return RedirectResponse(url="/", status_code=302)


@app.get("/auth/logout")
def auth_logout(request: Request):
    request.session.clear()
    return _login_redirect()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if AUTH_REQUIRED and _current_user(request) is None:
        return _login_redirect()

    current_user = _current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "models": SUPPORTED_BASE_MODELS,
            "model_modes": MODEL_MODE_ALIASES,
            "presets": DEFAULT_PRESETS,
            "auth_required": AUTH_REQUIRED,
            "current_user": current_user,
            "psychek_admin_url": PSYCHEK_ADMIN_URL,
        },
    )


@app.post("/projects")
def create_project(request: Request, req: ProjectCreateRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    payload = pipeline.create_project(scoped_req)
    payload["project_id"] = req.project_id
    return payload


@app.get("/projects")
def list_projects(request: Request):
    _require_auth(request)
    scoped_prefix = _scope_prefix(request) if SCOPE_PROJECTS_BY_USER else None
    scoped_marker = f"{scoped_prefix}__" if scoped_prefix else None

    projects: list[dict[str, str]] = []
    for project_id in pipeline.list_projects():
        if scoped_marker:
            if not project_id.startswith(scoped_marker):
                continue
            visible_project_id = project_id[len(scoped_marker) :]
        else:
            visible_project_id = project_id
        projects.append({"project_id": visible_project_id})

    return {"projects": projects}


@app.post("/projects/{project_id}/reference-audio")
def upload_reference_audio(request: Request, project_id: str, req: ProjectReferenceAudioUploadRequest):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, project_id)

    try:
        paths = pipeline.project_manager.ensure_project(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    try:
        audio_bytes = base64.b64decode(req.audio_b64.encode("utf-8"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="invalid audio_b64 payload") from exc

    audio_hash = hashlib.sha256(audio_bytes).hexdigest()
    owner_key, owner_label = _current_user_key_and_label(request)
    ext = _safe_audio_extension(req.filename)
    output_path = paths.assets_reference_audio / f"reference-{audio_hash[:16]}{ext}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        output_path.write_bytes(audio_bytes)

    cache = _load_reference_cache(paths.manifests)
    entry = cache.get(audio_hash, {})
    entry.update(
        {
            "audio_hash": audio_hash,
            "audio_path": str(output_path),
            "source_filename": _safe_filename(req.filename),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "owner_key": owner_key or "",
            "owner_label": owner_label or "",
            "project_id": project_id,
        }
    )
    cache[audio_hash] = entry
    _write_reference_cache(paths.manifests, cache)

    artifact_url = f"/projects/{project_id}/artifact?path={quote(str(output_path), safe='')}"
    return {
        "project_id": project_id,
        "audio_hash": audio_hash,
        "filename": output_path.name,
        "saved_path": str(output_path),
        "artifact_url": artifact_url,
    }


@app.get("/projects/{project_id}/reference-audio")
def list_reference_audio(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, project_id)

    try:
        pipeline.project_manager.ensure_project(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    user_key, _ = _current_user_key_and_label(request)
    items: list[dict[str, str | bool]] = []
    seen_hashes: set[str] = set()

    # Include all samples currently attached to this project (supports multi-user projects).
    for sample in _project_cache_entries(request, scoped_project_id=scoped_project_id):
        row = {**sample, "scope": "project"}
        items.append(row)
        sample_hash = str(sample.get("audio_hash") or "")
        if sample_hash:
            seen_hashes.add(sample_hash)

    # Include this user's own samples from other projects as reusable library entries.
    if user_key:
        for candidate_project_id in pipeline.list_projects():
            if candidate_project_id == scoped_project_id:
                continue
            for sample in _project_cache_entries(request, scoped_project_id=candidate_project_id):
                sample_hash = str(sample.get("audio_hash") or "")
                if not sample_hash or sample_hash in seen_hashes:
                    continue
                sample_owner_key = str(sample.get("owner_key") or "")
                legacy_owner_match = not sample_owner_key and candidate_project_id.startswith(f"{user_key}__")
                if sample_owner_key != user_key and not legacy_owner_match:
                    continue
                row = {**sample, "scope": "library"}
                items.append(row)
                seen_hashes.add(sample_hash)

    items.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    return {"project_id": project_id, "samples": items}


@app.post("/transcribe")
def transcribe(request: Request, req: TranscribeRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    return pipeline.transcribe(scoped_req)


@app.post("/clip")
def clip(request: Request, req: ClipRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    return pipeline.clip(scoped_req)


@app.post("/synthesize")
def synthesize(request: Request, req: SynthesisRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    return pipeline.synthesize(scoped_req)


@app.post("/synthesize/simple")
def synthesize_simple(request: Request, req: SimpleSynthesisRequest):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, req.project_id)

    try:
        paths = pipeline.project_manager.ensure_project(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    reference_cache = _load_reference_cache(paths.manifests)
    project_root = paths.root.resolve()
    reference_hash = ""
    source_filename = ""
    owner_key, owner_label = _current_user_key_and_label(request)

    if req.reference_audio_hash:
        reference_hash = req.reference_audio_hash.strip().lower()
        found = _find_reference_audio_for_hash(
            request,
            scoped_project_id=scoped_project_id,
            audio_hash=reference_hash,
        )
        if not found:
            raise HTTPException(status_code=404, detail="saved reference audio not found")

        found_entry, found_reference_path, source_project_id = found
        source_filename = str(found_entry.get("source_filename") or found_reference_path.name)
        source_ext = _safe_audio_extension(source_filename)
        reference_path = (paths.assets_reference_audio / f"reference-{reference_hash[:16]}{source_ext}").resolve()
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        if not reference_path.exists():
            reference_path.write_bytes(found_reference_path.read_bytes())

        cached_entry = {
            **found_entry,
            "audio_hash": reference_hash,
            "audio_path": str(reference_path),
            "source_filename": source_filename,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "owner_key": str(found_entry.get("owner_key") or owner_key or ""),
            "owner_label": str(found_entry.get("owner_label") or owner_label or ""),
            "project_id": project_id,
            "origin_project_id": _descope_project_id(request, source_project_id),
        }
        reference_cache[reference_hash] = cached_entry
        _write_reference_cache(paths.manifests, reference_cache)
    else:
        cached_entry = {}
        if not req.reference_audio_b64 or not req.reference_audio_filename:
            raise HTTPException(
                status_code=422,
                detail="Provide either reference_audio_b64+reference_audio_filename or reference_audio_hash",
            )

        try:
            reference_audio = base64.b64decode(req.reference_audio_b64.encode("utf-8"), validate=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="invalid reference_audio_b64 payload") from exc

        reference_hash = hashlib.sha256(reference_audio).hexdigest()
        source_filename = _safe_filename(req.reference_audio_filename)
        cached_entry = reference_cache.get(reference_hash, {})

        reference_path = _resolve_reference_audio_path(project_root, cached_entry.get("audio_path"))
        if reference_path is None:
            reference_ext = _safe_audio_extension(req.reference_audio_filename)
            reference_path = (paths.assets_reference_audio / f"reference-{reference_hash[:16]}{reference_ext}").resolve()
            reference_path.parent.mkdir(parents=True, exist_ok=True)
            if not reference_path.exists():
                reference_path.write_bytes(reference_audio)

        refreshed_entry = {
            **cached_entry,
            "audio_hash": reference_hash,
            "audio_path": str(reference_path),
            "source_filename": source_filename,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "owner_key": owner_key or "",
            "owner_label": owner_label or "",
            "project_id": project_id,
        }
        reference_cache[reference_hash] = refreshed_entry
        _write_reference_cache(paths.manifests, reference_cache)
        cached_entry = refreshed_entry

    cached_reference_text = cached_entry.get("reference_text")
    reference_text = cached_reference_text if isinstance(cached_reference_text, str) and cached_reference_text.strip() else None

    output_name = _build_output_name(req.text, req.output_name)

    model_id = MODEL_MODE_ALIASES["quality"] if req.quality == "high" else MODEL_MODE_ALIASES["fast"]
    add_ums = req.add_ums or req.add_fillers
    add_ahs = req.add_ahs or req.add_fillers
    scripted_text = _inject_fillers(req.text, add_ums=add_ums, add_ahs=add_ahs)
    min_gap = round(max(0.15, req.average_gap_seconds * 0.7), 3)
    max_gap = round(min(2.5, req.average_gap_seconds * 1.3), 3)

    synth_req = SynthesisRequest(
        project_id=scoped_project_id,
        text=scripted_text,
        reference_audio_path=reference_path,
        reference_text=reference_text,
        model_id=model_id,
        max_new_tokens=1400 if req.quality == "high" else 1000,
        chunk_mode="sentence",
        pause_config=PauseConfig(
            strategy="random_uniform_with_length_adjustment",
            min_seconds=min_gap,
            max_seconds=max_gap,
            seed=None,
        ),
        output_format=req.output_format,
        output_name=output_name,
        generate_transcript=req.generate_transcript,
        voice_clone_authorized=req.voice_clone_authorized,
    )

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    def run_local_job() -> None:
        try:
            job = pipeline.orchestrator.run_synthesis_job(synth_req, job_id=job_id)
            metadata_path_raw = job.outputs.get("metadata_path") if isinstance(job.outputs, dict) else None
            if not isinstance(metadata_path_raw, str):
                return

            metadata_path = Path(metadata_path_raw)
            if not metadata_path.exists():
                return

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            reference_text_value = metadata.get("reference_text")
            if not isinstance(reference_text_value, str) or not reference_text_value.strip():
                return

            latest_cache = _load_reference_cache(paths.manifests)
            latest_entry = latest_cache.get(reference_hash, {})
            latest_entry.update(
                {
                    "audio_hash": reference_hash,
                    "audio_path": str(reference_path),
                    "source_filename": source_filename,
                    "reference_text": reference_text_value.strip(),
                    "reference_text_updated_at": datetime.now(timezone.utc).isoformat(),
                    "owner_key": str(latest_entry.get("owner_key") or owner_key or ""),
                    "owner_label": str(latest_entry.get("owner_label") or owner_label or ""),
                }
            )
            latest_cache[reference_hash] = latest_entry
            _write_reference_cache(paths.manifests, latest_cache)
        except Exception:
            # Job failure details are persisted in manifest by orchestrator.
            return

    thread = threading.Thread(target=run_local_job, name=f"radtts-{job_id}", daemon=True)
    thread.start()

    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0.0,
        "project_id": req.project_id,
        "output_name": output_name,
    }


@app.post("/synthesize/worker")
def synthesize_worker(request: Request, req: WorkerSynthesisEnqueueRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    job_id = worker_manager.enqueue_synthesis_job(scoped_req)
    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued_remote",
        "worker_mode": True,
    }


@app.post("/captions")
def captions(request: Request, req: CaptionRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    return pipeline.captions(scoped_req)


@app.get("/projects/{project_id}/outputs")
def list_project_outputs(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, project_id)
    try:
        rows = pipeline.list_outputs(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    outputs: list[dict[str, object]] = []
    for item in reversed(rows):
        audio_path = str(item.get("output_file") or "")
        captions_raw = item.get("captions") if isinstance(item.get("captions"), dict) else {}
        captions = {key: str(value) for key, value in (captions_raw or {}).items()}
        folder_path = str(Path(audio_path).parent) if audio_path else ""

        audio_download_url = (
            f"/projects/{project_id}/artifact?path={quote(audio_path, safe='')}" if audio_path else None
        )
        srt_path = captions.get("srt")
        srt_download_url = (
            f"/projects/{project_id}/artifact?path={quote(srt_path, safe='')}" if srt_path else None
        )

        outputs.append(
            {
                "job_id": item.get("job_id"),
                "created_at": item.get("created_at"),
                "output_name": Path(audio_path).stem if audio_path else None,
                "audio_path": audio_path,
                "folder_path": folder_path,
                "audio_download_url": audio_download_url,
                "captions": captions,
                "srt_download_url": srt_download_url,
            }
        )

    return {"project_id": project_id, "outputs": outputs}


@app.get("/projects/{project_id}/artifact")
def get_project_artifact(request: Request, project_id: str, path: str):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, project_id)
    try:
        project_paths = pipeline.project_manager.ensure_project(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    raw_path = Path(path)
    candidate = raw_path if raw_path.is_absolute() else (Path.cwd() / raw_path)
    candidate = candidate.resolve()

    project_root = project_paths.root.resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="artifact path is outside project") from exc

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")

    return FileResponse(path=candidate, filename=candidate.name)


@app.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str, project_id: str):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, project_id)
    job = pipeline.get_job(scoped_project_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if isinstance(job, dict) and isinstance(job.get("project_id"), str):
        job["project_id"] = _descope_project_id(request, job["project_id"])
    return job


@app.post("/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str, project_id: str):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, project_id)
    payload = pipeline.cancel_job(scoped_project_id, job_id)
    if isinstance(payload, dict) and isinstance(payload.get("project_id"), str):
        payload["project_id"] = _descope_project_id(request, payload["project_id"])
    return payload


@app.get("/workers")
def list_workers(request: Request):
    _require_auth(request)
    workers = worker_manager.list_workers()
    return {"workers": [worker.model_dump(mode="json") for worker in workers]}


@app.post("/workers/invite", response_model=WorkerInviteResponse)
def worker_invite(request: Request, req: WorkerInviteRequest):
    _require_auth(request)
    token = worker_manager.issue_invite_token(req.capabilities)
    install_command = (
        "radtts-worker "
        f"--server-url {str(request.base_url).rstrip('/')} "
        f"--invite-token {token}"
    )
    return WorkerInviteResponse(
        invite_token=token,
        expires_in_seconds=WORKER_INVITE_MAX_AGE_SECONDS,
        install_command=install_command,
    )


@app.post("/workers/register")
def worker_register(req: WorkerRegisterRequest):
    return worker_manager.register_worker(req).model_dump(mode="json")


@app.post("/workers/pull", response_model=WorkerPullResponse)
def worker_pull(req: WorkerPullRequest):
    job = worker_manager.pull_job(req)
    return WorkerPullResponse(job=job)


@app.post("/workers/jobs/{job_id}/complete")
def worker_complete(job_id: str, req: WorkerJobCompleteRequest):
    worker_manager.complete_job(job_id, req)
    return {"job_id": job_id, "status": "completed"}


@app.post("/workers/jobs/{job_id}/fail")
def worker_fail(job_id: str, req: WorkerJobFailRequest):
    worker_manager.fail_job(job_id, req)
    return {"job_id": job_id, "status": "failed"}


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is not installed. Install with 'pip install -e .[api]'.") from exc

    host = os.environ.get("RADTTS_HOST", "127.0.0.1")
    port = int(os.environ.get("RADTTS_PORT", "8080"))
    uvicorn.run("radtts.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
