"""FastAPI service exposing RADTTS pipeline endpoints."""

from __future__ import annotations

import base64
import hashlib
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


def _scope_project_id(request: Request, project_id: str) -> str:
    prefix = _scope_prefix(request)
    if not prefix:
        return project_id
    scoped = f"{prefix}__{project_id}"
    if project_id.startswith(f"{prefix}__"):
        return project_id
    return scoped


def _descope_project_id(request: Request, project_id: str) -> str:
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


def _inject_fillers(text: str) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    if len(parts) <= 1:
        return text
    rng = random.Random(hashlib.sha256(text.encode("utf-8")).hexdigest())
    fillers = ["Um,", "Ah,"]
    patched: list[str] = []
    for idx, sentence in enumerate(parts):
        if idx > 0 and len(sentence) > 20 and rng.random() < 0.22:
            filler = fillers[0] if rng.random() < 0.5 else fillers[1]
            patched.append(f"{filler} {sentence}")
        else:
            patched.append(sentence)
    return " ".join(patched)


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
    scoped_prefix = _scope_prefix(request)
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

    safe_name = _safe_filename(req.filename)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_path = paths.assets_reference_audio / f"reference-{stamp}-{safe_name}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes)

    artifact_url = f"/projects/{project_id}/artifact?path={quote(str(output_path), safe='')}"
    return {
        "project_id": project_id,
        "filename": output_path.name,
        "saved_path": str(output_path),
        "artifact_url": artifact_url,
    }


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

    try:
        reference_audio = base64.b64decode(req.reference_audio_b64.encode("utf-8"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="invalid reference_audio_b64 payload") from exc

    output_name = _build_output_name(req.text, req.output_name)
    reference_filename = _safe_filename(req.reference_audio_filename)
    reference_path = paths.assets_reference_audio / f"{output_name}_{reference_filename}"
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.write_bytes(reference_audio)

    model_id = MODEL_MODE_ALIASES["quality"] if req.quality == "high" else MODEL_MODE_ALIASES["fast"]
    scripted_text = _inject_fillers(req.text) if req.add_fillers else req.text
    min_gap = round(max(0.15, req.average_gap_seconds * 0.7), 3)
    max_gap = round(min(2.5, req.average_gap_seconds * 1.3), 3)

    synth_req = SynthesisRequest(
        project_id=scoped_project_id,
        text=scripted_text,
        reference_audio_path=reference_path,
        reference_text=None,
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
        voice_clone_authorized=req.voice_clone_authorized,
    )

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    def run_local_job() -> None:
        try:
            pipeline.orchestrator.run_synthesis_job(synth_req, job_id=job_id)
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
