"""FastAPI service exposing RADTTS pipeline endpoints."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import re
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request as URLRequest, urlopen

from radtts.models import (
    BuiltInVoicePreviewRequest,
    CaptionRequest,
    ClipRequest,
    PauseConfig,
    ProjectAccessGrantRequest,
    ProjectAccessRevokeRequest,
    ProjectReferenceAudioUploadRequest,
    ProjectCreateRequest,
    ProjectReferenceAudioDeleteRequest,
    ProjectScriptDeleteRequest,
    ProjectScriptRestoreRequest,
    ProjectScriptSaveRequest,
    ProjectUiSettings,
    SimpleSynthesisRequest,
    SynthesisRequest,
    TranscribeRequest,
    OutputFormat,
    VoiceSource,
    WorkerInviteRequest,
    WorkerInviteResponse,
    WorkerJobCompleteRequest,
    WorkerJobFailRequest,
    WorkerJobProgressRequest,
    WorkerPullRequest,
    WorkerPullResponse,
    WorkerRegisterRequest,
    WorkerSynthesisEnqueueRequest,
)
from radtts.orchestrator import PipelineOrchestrator
from radtts.pipeline import RADTTSPipeline
from radtts.constants import (
    BUILTIN_MODEL_MODE_ALIASES,
    DEFAULT_PRESETS,
    MODEL_MODE_ALIASES,
    QWEN_CUSTOM_VOICE_SPEAKERS,
    SUPPORTED_BASE_MODELS,
)
from radtts.worker_manager import WorkerManager
from radtts.worker_setup import normalize_helper_profile
from radtts.utils.audio import probe_duration_seconds
from radtts.utils.text import recommended_generation_timeout_seconds
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
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


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


PROJECTS_ROOT = Path(os.environ.get("RADTTS_PROJECTS_ROOT", "projects"))
MODULE_ROOT = Path(__file__).resolve().parent
AUTH_REQUIRED = _env_bool("RADTTS_AUTH_REQUIRED", False)
SESSION_SECRET = os.environ.get("RADTTS_SESSION_SECRET", "radtts-dev-session-secret")
SESSION_SECURE = _env_bool("RADTTS_SESSION_SECURE", False)
APP_ENV = os.environ.get("APP_ENV", "").strip().lower()
PSYCHEK_LOGIN_URL = os.environ.get("PSYCHEK_LOGIN_URL", "http://127.0.0.1:8000/login")
BRIDGE_SECRET = os.environ.get("RADTTS_BRIDGE_SECRET", SESSION_SECRET)
BRIDGE_MAX_AGE_SECONDS = int(os.environ.get("RADTTS_BRIDGE_MAX_AGE_SECONDS", "120"))
WORKER_SECRET = os.environ.get("RADTTS_WORKER_SECRET", SESSION_SECRET)
WORKER_INVITE_MAX_AGE_SECONDS = int(os.environ.get("RADTTS_WORKER_INVITE_MAX_AGE_SECONDS", "86400"))
SCOPE_PROJECTS_BY_USER = _env_bool("RADTTS_SCOPE_PROJECTS_BY_USER", True)
SIMPLE_SYNTH_DEFAULT_TO_WORKER = _env_bool("RADTTS_SIMPLE_SYNTH_DEFAULT_TO_WORKER", True)
WORKER_FALLBACK_TO_LOCAL = _env_bool("RADTTS_WORKER_FALLBACK_TO_LOCAL", True)
WORKER_FALLBACK_TIMEOUT_SECONDS = max(5, _env_int("RADTTS_WORKER_FALLBACK_TIMEOUT_SECONDS", 40))
WORKER_ONLINE_WINDOW_SECONDS = max(10, _env_int("RADTTS_WORKER_ONLINE_WINDOW_SECONDS", 30))
LOCAL_FALLBACK_GENERATION_TIMEOUT_SECONDS = max(
    300,
    _env_int("RADTTS_LOCAL_FALLBACK_GENERATION_TIMEOUT_SECONDS", 600),
)
LOCAL_FALLBACK_MAX_NEW_TOKENS = max(
    128,
    _env_int("RADTTS_LOCAL_FALLBACK_MAX_NEW_TOKENS", 600),
)
WORKER_RUNNING_STALL_TIMEOUT_SECONDS = max(
    WORKER_FALLBACK_TIMEOUT_SECONDS + 60,
    _env_int("RADTTS_WORKER_RUNNING_STALL_TIMEOUT_SECONDS", 180),
)
WORKER_MODEL_LOAD_STALL_TIMEOUT_SECONDS = max(
    WORKER_RUNNING_STALL_TIMEOUT_SECONDS,
    _env_int("RADTTS_WORKER_MODEL_LOAD_STALL_TIMEOUT_SECONDS", 600),
)
WORKER_FIRST_CHUNK_STALL_TIMEOUT_SECONDS = max(
    WORKER_MODEL_LOAD_STALL_TIMEOUT_SECONDS,
    _env_int("RADTTS_WORKER_FIRST_CHUNK_STALL_TIMEOUT_SECONDS", 900),
)
WORKER_RECENT_WINDOW_SECONDS = max(
    WORKER_ONLINE_WINDOW_SECONDS,
    min(WORKER_MODEL_LOAD_STALL_TIMEOUT_SECONDS, 180),
)
WORKER_RECENT_QUEUE_GRACE_SECONDS = max(
    WORKER_FALLBACK_TIMEOUT_SECONDS,
    WORKER_RECENT_WINDOW_SECONDS,
)
WORKER_BUSY_QUEUE_GRACE_SECONDS = max(
    WORKER_RECENT_QUEUE_GRACE_SECONDS,
    _env_int(
        "RADTTS_WORKER_BUSY_QUEUE_GRACE_SECONDS",
        max(WORKER_MODEL_LOAD_STALL_TIMEOUT_SECONDS * 2, WORKER_RUNNING_STALL_TIMEOUT_SECONDS * 4),
    ),
)
SCRIPT_VERSION_HISTORY_LIMIT = max(10, _env_int("RADTTS_SCRIPT_VERSION_HISTORY_LIMIT", 60))
SCOPED_PROJECT_RE = re.compile(r"^u[0-9a-f]{12}__.+$")
BUILTIN_VOICE_PREVIEW_TEXT = "Hello, this is a quick built-in voice preview."
BUILTIN_VOICE_PREVIEW_CACHE_DIR = PROJECTS_ROOT / ".builtin_voice_previews"


def _worker_helper_profile() -> str:
    if APP_ENV == "development":
        return "dev"
    if APP_ENV == "production":
        return "prod"
    return normalize_helper_profile(APP_ENV or "default")


def _infer_psychek_admin_url(login_url: str) -> str:
    cleaned = login_url.strip()
    if cleaned.endswith("/login"):
        return f"{cleaned[:-len('/login')]}/admin"
    return f"{cleaned.rstrip('/')}/admin"


def _infer_psychek_app_url(login_url: str) -> str:
    cleaned = login_url.strip()
    if cleaned.endswith("/login"):
        return cleaned[:-len("/login")] or "/"
    return cleaned.rstrip("/")


PSYCHEK_ADMIN_URL = os.environ.get("PSYCHEK_ADMIN_URL", "").strip() or _infer_psychek_admin_url(PSYCHEK_LOGIN_URL)
PSYCHEK_APP_URL = os.environ.get("PSYCHEK_APP_URL", "").strip() or _infer_psychek_app_url(PSYCHEK_LOGIN_URL)
PSYCHEK_SHAREABLE_USERS_URL = (
    os.environ.get("PSYCHEK_SHAREABLE_USERS_URL", "").strip()
    or f"{PSYCHEK_APP_URL.rstrip('/')}/api/v1/integrations/shareable-users"
)
PSYCHEK_INTEGRATION_API_KEY = os.environ.get("PSYCHEK_INTEGRATION_API_KEY", "").strip() or BRIDGE_SECRET
RADCAST_APP_URL = os.environ.get("RADCAST_APP_URL", "").strip()

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


def _looks_scoped_project_id(project_id: str) -> bool:
    return bool(SCOPED_PROJECT_RE.match(project_id.strip()))


def _display_project_id(project_id: str) -> str:
    value = project_id.strip()
    if _looks_scoped_project_id(value) and "__" in value:
        return value.split("__", 1)[1]
    return value


def _worker_availability_snapshot() -> dict[str, int | str | None]:
    def _parse_seen_at(value: str | None) -> datetime | None:
        raw_seen = str(value or "").strip()
        if not raw_seen:
            return None
        try:
            last_seen = datetime.fromisoformat(raw_seen)
        except ValueError:
            return None
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        return last_seen

    now = datetime.now(timezone.utc)
    workers = worker_manager.list_workers()
    queued_jobs = 0
    running_worker_jobs = 0
    for entry in worker_manager._read_list(worker_manager.jobs_path):
        status = str(entry.get("status") or "").strip().lower()
        assigned_worker_id = str(entry.get("assigned_worker_id") or "").strip().lower()
        if status == "queued":
            queued_jobs += 1
            continue
        if status == "running" and assigned_worker_id and assigned_worker_id != "local-fallback":
            running_worker_jobs += 1

    online = 0
    recent = 0
    latest_live_seen_at: datetime | None = None
    latest_recent_seen_at: datetime | None = None

    for worker in workers:
        last_seen = _parse_seen_at(worker.last_seen_at)
        if last_seen is None:
            continue
        age_seconds = (now - last_seen).total_seconds()
        if age_seconds <= WORKER_RECENT_WINDOW_SECONDS:
            recent += 1
            if latest_recent_seen_at is None or last_seen > latest_recent_seen_at:
                latest_recent_seen_at = last_seen
        if age_seconds <= WORKER_ONLINE_WINDOW_SECONDS:
            online += 1
            if latest_live_seen_at is None or last_seen > latest_live_seen_at:
                latest_live_seen_at = last_seen

    stale = max(0, len(workers) - online)

    return {
        "worker_total_count": len(workers),
        "worker_online_count": online,
        "worker_live_count": online,
        "worker_recent_count": recent,
        "worker_registered_count": len(workers),
        "worker_stale_count": stale,
        "worker_running_job_count": running_worker_jobs,
        "worker_queued_job_count": queued_jobs,
        "worker_online_window_seconds": WORKER_ONLINE_WINDOW_SECONDS,
        "worker_recent_window_seconds": WORKER_RECENT_WINDOW_SECONDS,
        "worker_last_live_seen_at": latest_live_seen_at.isoformat() if latest_live_seen_at else None,
        "worker_last_recent_seen_at": latest_recent_seen_at.isoformat() if latest_recent_seen_at else None,
    }


def _worker_queue_fallback_timeout_seconds(worker_snapshot: dict[str, int | str | None] | None = None) -> int:
    snapshot = worker_snapshot or _worker_availability_snapshot()
    recent = max(0, int(snapshot.get("worker_recent_count") or 0))
    running_jobs = max(0, int(snapshot.get("worker_running_job_count") or 0))
    if recent > 0:
        if running_jobs >= recent:
            return WORKER_BUSY_QUEUE_GRACE_SECONDS
        return WORKER_RECENT_QUEUE_GRACE_SECONDS
    return WORKER_FALLBACK_TIMEOUT_SECONDS




def _path_mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except FileNotFoundError:
        return None


def _project_last_activity_at(scoped_project_id: str) -> datetime:
    paths = pipeline.project_manager.get_paths(scoped_project_id)
    timestamps: list[datetime] = []

    root_mtime = _path_mtime(paths.root)
    if root_mtime is not None:
        timestamps.append(root_mtime)

    for manifest_path in paths.manifests.glob("*.json"):
        manifest_mtime = _path_mtime(manifest_path)
        if manifest_mtime is not None:
            timestamps.append(manifest_mtime)

    if not timestamps:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return max(timestamps)


def _coerce_project_settings(payload: object) -> ProjectUiSettings:
    data = payload if isinstance(payload, dict) else {}

    selected_audio_hash = str(data.get("selected_audio_hash") or "").strip() or None
    if selected_audio_hash and len(selected_audio_hash) < 16:
        selected_audio_hash = None

    voice_source_raw = str(data.get("voice_source") or VoiceSource.REFERENCE.value).strip().lower()
    try:
        voice_source = VoiceSource(voice_source_raw)
    except ValueError:
        voice_source = VoiceSource.REFERENCE

    built_in_speaker = str(data.get("built_in_speaker") or "").strip() or None
    quality = "high" if str(data.get("quality") or "").strip().lower() == "high" else "normal"

    output_format_raw = str(data.get("output_format") or OutputFormat.MP3.value).strip().lower()
    try:
        output_format = OutputFormat(output_format_raw)
    except ValueError:
        output_format = OutputFormat.MP3

    try:
        average_gap_seconds = float(data.get("average_gap_seconds", 0.8))
    except (TypeError, ValueError):
        average_gap_seconds = 0.8
    average_gap_seconds = max(0.15, min(2.5, average_gap_seconds))

    return ProjectUiSettings(
        selected_audio_hash=selected_audio_hash,
        voice_source=voice_source,
        built_in_speaker=built_in_speaker,
        quality=quality,
        add_ums=bool(data.get("add_ums", False)),
        add_ahs=bool(data.get("add_ahs", False)),
        generate_transcript=bool(data.get("generate_transcript", False)),
        output_format=output_format,
        average_gap_seconds=average_gap_seconds,
    )


def _load_project_settings(scoped_project_id: str) -> ProjectUiSettings:
    metadata = pipeline.project_manager.load_project_metadata(scoped_project_id)
    return _coerce_project_settings(metadata.get("ui_settings"))


def _write_project_settings(scoped_project_id: str, settings: ProjectUiSettings) -> ProjectUiSettings:
    pipeline.project_manager.update_project_metadata(
        scoped_project_id,
        {"ui_settings": settings.model_dump(mode="json")},
    )
    return settings


def _inferred_owner_key_from_project_id(scoped_project_id: str) -> str:
    if "__" not in scoped_project_id:
        return ""
    prefix, _ = scoped_project_id.split("__", 1)
    return prefix if prefix.startswith("u") and len(prefix) == 13 else ""


def _project_access_file(scoped_project_id: str) -> Path:
    return pipeline.project_manager.get_paths(scoped_project_id).manifests / "access.json"


def _load_project_access(scoped_project_id: str) -> dict[str, object]:
    access_path = _project_access_file(scoped_project_id)
    try:
        payload = json.loads(access_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        payload = {}
    except json.JSONDecodeError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
    owner_key = str(owner.get("user_key") or "").strip()
    owner_email = str(owner.get("email") or "").strip().lower()
    owner_label = str(owner.get("display_name") or owner.get("email") or owner.get("sub") or owner_key).strip()

    inferred_owner_key = _inferred_owner_key_from_project_id(scoped_project_id)
    if not owner_key and inferred_owner_key:
        owner_key = inferred_owner_key
        if not owner_label:
            owner_label = owner_key

    collaborators_raw = payload.get("collaborators") if isinstance(payload.get("collaborators"), list) else []
    collaborators: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in collaborators_raw:
        if not isinstance(row, dict):
            continue
        email = str(row.get("email") or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        collaborators.append(
            {
                "email": email,
                "granted_at": str(row.get("granted_at") or ""),
                "granted_by": str(row.get("granted_by") or ""),
            }
        )

    return {
        "owner": {
            "user_key": owner_key,
            "email": owner_email,
            "display_name": owner_label,
        },
        "collaborators": collaborators,
        "updated_at": str(payload.get("updated_at") or ""),
    }


def _write_project_access(scoped_project_id: str, access: dict[str, object]) -> None:
    access_path = _project_access_file(scoped_project_id)
    access_path.parent.mkdir(parents=True, exist_ok=True)
    access_path.write_text(json.dumps(access, indent=2), encoding="utf-8")


def _bootstrap_owner_access_if_missing(request: Request, scoped_project_id: str) -> None:
    access_path = _project_access_file(scoped_project_id)
    if access_path.exists():
        return
    user = _current_user(request) or {}
    user_key, user_label = _current_user_key_and_label(request)
    access = {
        "owner": {
            "user_key": user_key or _inferred_owner_key_from_project_id(scoped_project_id),
            "email": str(user.get("email") or "").strip().lower(),
            "display_name": user_label or "",
        },
        "collaborators": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_project_access(scoped_project_id, access)


def _resolve_access_for_user(request: Request, scoped_project_id: str) -> dict[str, object]:
    access = _load_project_access(scoped_project_id)
    session_user = _current_user(request)
    user = session_user or {}
    has_user = session_user is not None
    user_key, _ = _current_user_key_and_label(request)
    user_email = str(user.get("email") or "").strip().lower()
    is_admin = bool(user.get("is_admin", False)) if has_user else False

    owner = access.get("owner") if isinstance(access.get("owner"), dict) else {}
    owner_key = str(owner.get("user_key") or "")
    owner_email = str(owner.get("email") or "").strip().lower()

    collaborator_emails: set[str] = set()
    for row in access.get("collaborators", []):
        if isinstance(row, dict):
            email = str(row.get("email") or "").strip().lower()
            if email:
                collaborator_emails.add(email)

    is_owner = bool(
        (user_key and owner_key and user_key == owner_key)
        or (user_email and owner_email and user_email == owner_email)
    )
    is_collaborator = bool(user_email and user_email in collaborator_emails)
    if has_user:
        can_access = is_admin or is_owner or is_collaborator
    else:
        can_access = not AUTH_REQUIRED
    can_manage = is_admin or is_owner

    return {
        "can_access": can_access,
        "can_manage": can_manage,
        "is_owner": is_owner,
        "is_collaborator": is_collaborator,
        "is_admin": is_admin,
        "owner": owner,
        "collaborators": access.get("collaborators", []),
    }


def _resolve_project_id_for_request(request: Request, project_id: str) -> str:
    requested = project_id.strip()
    if not requested:
        raise HTTPException(status_code=404, detail="project not found")

    candidate_ids: list[str] = []
    if not SCOPE_PROJECTS_BY_USER:
        candidate_ids.append(requested)
    else:
        if _looks_scoped_project_id(requested):
            candidate_ids.append(requested)
        else:
            candidate_ids.append(_scope_project_id(request, requested))
            for candidate in pipeline.list_projects():
                if _display_project_id(candidate) == requested:
                    candidate_ids.append(candidate)

    seen: set[str] = set()
    existing: list[str] = []
    for candidate in candidate_ids:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            pipeline.project_manager.ensure_project(candidate)
        except FileNotFoundError:
            continue
        existing.append(candidate)

    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    for candidate in existing:
        access = _resolve_access_for_user(request, candidate)
        if bool(access.get("can_access")):
            return candidate

    raise HTTPException(status_code=403, detail="project access denied")


def _shareable_users_lookup_url(*, exclude_email: str = "") -> str:
    base_url = str(PSYCHEK_SHAREABLE_USERS_URL or "").strip()
    if not base_url:
        raise HTTPException(status_code=503, detail="shareable users are not configured")
    if not exclude_email:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'exclude_email': exclude_email})}"


def _extract_integration_error(exc: HTTPError) -> str:
    detail = f"HTTP {exc.code}"
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return detail
    if isinstance(payload, dict):
        return str(payload.get("error") or payload.get("detail") or detail)
    return detail


def _fetch_shareable_users(*, exclude_email: str = "") -> list[dict[str, object]]:
    headers = {"Accept": "application/json"}
    if PSYCHEK_INTEGRATION_API_KEY:
        headers["Authorization"] = f"Bearer {PSYCHEK_INTEGRATION_API_KEY}"
    request = URLRequest(_shareable_users_lookup_url(exclude_email=exclude_email), headers=headers, method="GET")

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = _extract_integration_error(exc)
        if exc.code in {401, 403}:
            raise HTTPException(status_code=503, detail="shareable users authentication failed") from exc
        if exc.code == 404:
            raise HTTPException(status_code=503, detail="shareable users are unavailable") from exc
        raise HTTPException(status_code=502, detail=f"could not load shareable users: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"could not load shareable users: {exc.reason}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="invalid shareable users response") from exc

    rows = payload.get("users") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise HTTPException(status_code=502, detail="invalid shareable users response")

    users: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        email = str(row.get("email") or "").strip().lower()
        if not email:
            continue
        users.append(
            {
                "id": row.get("id"),
                "username": str(row.get("username") or "").strip(),
                "display_name": str(row.get("display_name") or "").strip(),
                "email": email,
            }
        )
    return users


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


def _script_versions_file(project_manifests_dir: Path) -> Path:
    return project_manifests_dir / "script_versions.json"


def _script_preview(text: str, *, max_chars: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return f"{compact[: max_chars - 1].rstrip()}…"


def _builtin_voice_preview_cache_path(*, model_id: str, speaker: str, preview_text: str) -> Path:
    digest = hashlib.sha1(f"{model_id}|{speaker}|{preview_text}".encode("utf-8")).hexdigest()
    return BUILTIN_VOICE_PREVIEW_CACHE_DIR / f"{digest}.wav"


def _builtin_voice_preview_url(speaker: str) -> str:
    return f"/static/builtin_voice_previews/{speaker}.mp3"


def _normalize_script_entry(raw: dict[str, object]) -> dict[str, object] | None:
    version_id = str(raw.get("version_id") or "").strip()
    if not version_id:
        return None

    text = str(raw.get("text") or "")
    source = str(raw.get("source") or "autosave").strip() or "autosave"
    saved_at = str(raw.get("saved_at") or "")
    try:
        word_count = int(raw.get("word_count") or len(re.findall(r"\S+", text)))
    except (TypeError, ValueError):
        word_count = len(re.findall(r"\S+", text))

    try:
        char_count = int(raw.get("char_count") or len(text))
    except (TypeError, ValueError):
        char_count = len(text)
    preview = str(raw.get("preview") or _script_preview(text))

    return {
        "version_id": version_id,
        "saved_at": saved_at,
        "source": source,
        "text": text,
        "word_count": word_count,
        "char_count": char_count,
        "preview": preview,
    }


def _load_script_versions(project_manifests_dir: Path) -> dict[str, object]:
    versions_path = _script_versions_file(project_manifests_dir)
    try:
        payload = json.loads(versions_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        payload = {}
    except json.JSONDecodeError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    raw_versions = payload.get("versions")
    versions: list[dict[str, object]] = []
    if isinstance(raw_versions, list):
        for raw in raw_versions:
            if not isinstance(raw, dict):
                continue
            normalized = _normalize_script_entry(raw)
            if normalized is not None:
                versions.append(normalized)

    if len(versions) > SCRIPT_VERSION_HISTORY_LIMIT:
        versions = versions[-SCRIPT_VERSION_HISTORY_LIMIT:]

    version_ids = {str(row["version_id"]) for row in versions}
    current_version_id = str(payload.get("current_version_id") or "").strip()
    if current_version_id not in version_ids:
        current_version_id = str(versions[-1]["version_id"]) if versions else ""

    return {
        "current_version_id": current_version_id,
        "versions": versions,
    }


def _write_script_versions(project_manifests_dir: Path, payload: dict[str, object]) -> None:
    versions_path = _script_versions_file(project_manifests_dir)
    versions_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _script_version_metadata(version: dict[str, object]) -> dict[str, object]:
    try:
        word_count = int(version.get("word_count") or 0)
    except (TypeError, ValueError):
        word_count = 0

    try:
        char_count = int(version.get("char_count") or 0)
    except (TypeError, ValueError):
        char_count = 0

    return {
        "version_id": str(version.get("version_id") or ""),
        "saved_at": str(version.get("saved_at") or ""),
        "source": str(version.get("source") or ""),
        "word_count": word_count,
        "char_count": char_count,
        "preview": str(version.get("preview") or ""),
    }


def _find_script_entry(rows: list[dict[str, object]], version_id: str) -> dict[str, object] | None:
    for row in rows:
        if str(row.get("version_id") or "") == version_id:
            return row
    return None


def _script_payload_for_response(script_versions: dict[str, object]) -> dict[str, object]:
    versions = script_versions.get("versions")
    rows = versions if isinstance(versions, list) else []
    current_version_id = str(script_versions.get("current_version_id") or "")

    current_entry = _find_script_entry(rows, current_version_id)

    if current_entry is None and rows:
        tail = rows[-1]
        if isinstance(tail, dict):
            current_entry = tail
            current_version_id = str(tail.get("version_id") or "")

    metadata: list[dict[str, object]] = []
    for row in reversed(rows):
        if isinstance(row, dict):
            metadata.append(_script_version_metadata(row))

    return {
        "current_version_id": current_version_id,
        "text": str((current_entry or {}).get("text") or ""),
        "versions": metadata,
    }


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
    visible_project_id = _display_project_id(scoped_project_id)
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
        duration_seconds = None
        cached_duration = entry.get("duration_seconds")
        if cached_duration is not None:
            try:
                duration_seconds = float(cached_duration)
            except (TypeError, ValueError):
                duration_seconds = None
        if duration_seconds is None:
            try:
                duration_seconds = round(probe_duration_seconds(reference_path), 3)
            except Exception:
                duration_seconds = None
        artifact_url = f"/projects/{visible_project_id}/artifact?path={quote(str(reference_path), safe='')}"
        items.append(
            {
                "audio_hash": audio_hash,
                "source_filename": source_filename,
                "saved_path": saved_path,
                "updated_at": updated_at,
                "duration_seconds": duration_seconds,
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


def _read_reference_text_from_job_outputs(outputs: dict[str, object] | None) -> str | None:
    if not isinstance(outputs, dict):
        return None
    metadata_path_raw = outputs.get("metadata_path")
    if not isinstance(metadata_path_raw, str):
        return None

    metadata_path = Path(metadata_path_raw)
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    reference_text_value = metadata.get("reference_text")
    if not isinstance(reference_text_value, str) or not reference_text_value.strip():
        return None
    return reference_text_value.strip()


def _upsert_reference_cache_entry(
    *,
    paths,
    audio_hash: str,
    audio_path: Path,
    source_filename: str,
    owner_key: str,
    owner_label: str,
    reference_text: str | None = None,
) -> None:
    latest_cache = _load_reference_cache(paths.manifests)
    latest_entry = latest_cache.get(audio_hash, {})
    latest_entry.update(
        {
            "audio_hash": audio_hash,
            "audio_path": str(audio_path),
            "source_filename": source_filename,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "owner_key": str(latest_entry.get("owner_key") or owner_key or ""),
            "owner_label": str(latest_entry.get("owner_label") or owner_label or ""),
        }
    )
    if reference_text:
        latest_entry.update(
            {
                "reference_text": reference_text,
                "reference_text_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    latest_cache[audio_hash] = latest_entry
    _write_reference_cache(paths.manifests, latest_cache)


def _iso_age_seconds(value: str | None) -> float | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())


def _run_local_synthesis_from_worker_payload(
    *,
    worker_payload: WorkerSynthesisEnqueueRequest,
    job_id: str,
    owner_key: str = "",
    owner_label: str = "",
) -> None:
    try:
        paths = pipeline.project_manager.ensure_project(worker_payload.project_id)
    except FileNotFoundError:
        return

    fallback_max_new_tokens = min(worker_payload.max_new_tokens, LOCAL_FALLBACK_MAX_NEW_TOKENS)
    reference_hash = ""
    source_filename = ""
    reference_path = None

    if worker_payload.voice_source == VoiceSource.REFERENCE:
        try:
            reference_bytes = base64.b64decode(worker_payload.reference_audio_b64.encode("utf-8"), validate=True)
        except Exception:  # noqa: BLE001
            return

        reference_hash = hashlib.sha256(reference_bytes).hexdigest()
        source_filename = _safe_filename(worker_payload.reference_audio_filename)
        reference_ext = _safe_audio_extension(source_filename)
        reference_path = (paths.assets_reference_audio / f"reference-{reference_hash[:16]}{reference_ext}").resolve()
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        if not reference_path.exists():
            reference_path.write_bytes(reference_bytes)

    synth_req = SynthesisRequest(
        project_id=worker_payload.project_id,
        text=worker_payload.text,
        voice_source=worker_payload.voice_source,
        reference_audio_path=reference_path,
        reference_text=worker_payload.reference_text,
        model_id=worker_payload.model_id,
        built_in_speaker=worker_payload.built_in_speaker,
        built_in_instruct=worker_payload.built_in_instruct,
        max_new_tokens=fallback_max_new_tokens,
        chunk_mode=worker_payload.chunk_mode,
        pause_config=worker_payload.pause_config,
        output_format=worker_payload.output_format,
        output_name=worker_payload.output_name,
        generate_transcript=worker_payload.generate_transcript,
        voice_clone_authorized=True,
    )
    fallback_generation_timeout_seconds = recommended_generation_timeout_seconds(
        worker_payload.text,
        chunk_mode=worker_payload.chunk_mode,
        max_new_tokens=fallback_max_new_tokens,
        minimum_seconds=LOCAL_FALLBACK_GENERATION_TIMEOUT_SECONDS,
        voice_source=worker_payload.voice_source,
        reference_duration_seconds=probe_duration_seconds(reference_path) if reference_path is not None else None,
    )

    try:
        fallback_orchestrator = PipelineOrchestrator(
            projects_root=pipeline.project_manager.projects_root,
            stage_timeouts={"generation": fallback_generation_timeout_seconds},
            stage_retries={"generation": 0},
        )
        fallback_orchestrator._cancelled = pipeline.orchestrator._cancelled
        job = fallback_orchestrator.run_synthesis_job(synth_req, job_id=job_id)
    except Exception:
        return

    if worker_payload.voice_source == VoiceSource.REFERENCE and reference_path is not None:
        resolved_reference_text = _read_reference_text_from_job_outputs(job.outputs)
        _upsert_reference_cache_entry(
            paths=paths,
            audio_hash=reference_hash,
            audio_path=reference_path,
            source_filename=source_filename,
            owner_key=owner_key,
            owner_label=owner_label,
            reference_text=resolved_reference_text,
        )


def _claim_and_launch_local_fallback(
    *,
    job_id: str,
    reason: str,
    owner_key: str = "",
    owner_label: str = "",
    allowed_statuses: set[str] | None = None,
) -> bool:
    worker_payload = worker_manager.claim_job_for_local_fallback(
        job_id,
        reason=reason,
        allowed_statuses=allowed_statuses,
    )
    if worker_payload is None:
        return False

    thread = threading.Thread(
        target=lambda: _run_local_synthesis_from_worker_payload(
            worker_payload=worker_payload,
            job_id=job_id,
            owner_key=owner_key,
            owner_label=owner_label,
        ),
        name=f"radtts-fallback-{job_id}",
        daemon=True,
    )
    thread.start()
    return True


def _schedule_worker_fallback_watch(
    *,
    job_id: str,
    owner_key: str = "",
    owner_label: str = "",
    fallback_timeout_seconds: int | None = None,
) -> None:
    if not WORKER_FALLBACK_TO_LOCAL:
        return

    timeout_seconds = max(
        WORKER_FALLBACK_TIMEOUT_SECONDS,
        int(fallback_timeout_seconds or WORKER_FALLBACK_TIMEOUT_SECONDS),
    )

    def _watcher() -> None:
        time.sleep(timeout_seconds)
        reason = (
            f"No worker accepted this job after {timeout_seconds}s. "
            "Switching to local server fallback."
        )
        _claim_and_launch_local_fallback(
            job_id=job_id,
            reason=reason,
            owner_key=owner_key,
            owner_label=owner_label,
            allowed_statuses={"queued"},
        )

    watcher = threading.Thread(
        target=_watcher,
        name=f"radtts-fallback-watch-{job_id}",
        daemon=True,
    )
    watcher.start()


def _cancel_existing_project_worker_jobs(scoped_project_id: str) -> list[str]:
    reason = "Cancelled because a newer job was submitted for this project."
    return worker_manager.cancel_project_jobs(scoped_project_id, reason=reason)


def _maybe_trigger_worker_fallback(
    request: Request,
    *,
    scoped_project_id: str,
    job_payload: dict[str, object],
) -> bool:
    if not SIMPLE_SYNTH_DEFAULT_TO_WORKER or not WORKER_FALLBACK_TO_LOCAL:
        return False
    if str(job_payload.get("project_id") or "") != scoped_project_id:
        return False

    status = str(job_payload.get("status") or "")
    stage = str(job_payload.get("stage") or "")
    age_seconds = _iso_age_seconds(str(job_payload.get("created_at") or ""))
    job_id = str(job_payload.get("id") or "")
    if not job_id:
        return False

    owner_key, owner_label = _current_user_key_and_label(request)

    if status == "queued" and stage == "queued_remote":
        try:
            queue_timeout_seconds = max(
                WORKER_FALLBACK_TIMEOUT_SECONDS,
                int(job_payload.get("queue_fallback_timeout_seconds") or WORKER_FALLBACK_TIMEOUT_SECONDS),
            )
        except (TypeError, ValueError):
            queue_timeout_seconds = WORKER_FALLBACK_TIMEOUT_SECONDS
        if age_seconds is None or age_seconds < queue_timeout_seconds:
            return False
        reason = (
            f"No worker accepted this job after {queue_timeout_seconds}s. "
            "Switching to local server fallback."
        )
        return _claim_and_launch_local_fallback(
            job_id=job_id,
            reason=reason,
            owner_key=owner_key or "",
            owner_label=owner_label or "",
            allowed_statuses={"queued"},
        )

    running_worker_stages = {"worker_running", "model_load", "generation", "stitching", "captioning"}
    if status == "running" and stage in running_worker_stages:
        activity_age_seconds = _iso_age_seconds(
            str(job_payload.get("activity_at") or job_payload.get("updated_at") or "")
        )
        logs = job_payload.get("logs")
        log_lines = logs if isinstance(logs, list) else []
        has_generation_chunk_progress = any(
            isinstance(line, str) and re.search(r"generation chunk \d+/\d+", line, flags=re.IGNORECASE)
            for line in log_lines
        )
        stage_timeout_seconds = (
            WORKER_MODEL_LOAD_STALL_TIMEOUT_SECONDS
            if stage == "model_load"
            else (
                WORKER_FIRST_CHUNK_STALL_TIMEOUT_SECONDS
                if stage == "generation" and not has_generation_chunk_progress
                else WORKER_RUNNING_STALL_TIMEOUT_SECONDS
            )
        )
        if activity_age_seconds is None or activity_age_seconds < stage_timeout_seconds:
            return False
        reason = (
            f"Helper device stopped reporting progress for over {stage_timeout_seconds}s. "
            "Switching to local server fallback."
        )
        return _claim_and_launch_local_fallback(
            job_id=job_id,
            reason=reason,
            owner_key=owner_key or "",
            owner_label=owner_label or "",
            allowed_statuses={"running"},
        )

    return False


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
            "app_env": APP_ENV,
            "auth_required": AUTH_REQUIRED,
            "current_user": current_user,
            "psychek_app_url": PSYCHEK_APP_URL,
            "psychek_admin_url": PSYCHEK_ADMIN_URL,
            "radcast_app_url": RADCAST_APP_URL,
        },
    )


@app.post("/projects")
def create_project(request: Request, req: ProjectCreateRequest):
    _require_auth(request)
    scoped_project_id = _scope_project_id(request, req.project_id)
    scoped_req = req.model_copy(update={"project_id": scoped_project_id})
    payload = pipeline.create_project(scoped_req)
    _bootstrap_owner_access_if_missing(request, scoped_project_id)
    payload["project_id"] = req.project_id
    payload["project_ref"] = scoped_project_id
    return payload


@app.get("/projects")
def list_projects(request: Request):
    _require_auth(request)
    projects: list[tuple[datetime, dict[str, object]]] = []
    for scoped_project_id in pipeline.list_projects():
        access = _resolve_access_for_user(request, scoped_project_id)
        if not bool(access.get("can_access")):
            continue

        visible_project_id = _display_project_id(scoped_project_id)
        owner = access.get("owner") if isinstance(access.get("owner"), dict) else {}
        owner_label = str(owner.get("display_name") or owner.get("email") or owner.get("user_key") or "")
        last_activity_at = _project_last_activity_at(scoped_project_id)
        projects.append(
            (
                last_activity_at,
                {
                    "project_id": visible_project_id,
                    "project_ref": scoped_project_id,
                    "shared": not bool(access.get("is_owner")),
                    "owner_label": owner_label,
                    "updated_at": last_activity_at.isoformat(),
                },
            )
        )

    projects.sort(key=lambda item: (item[0], str(item[1].get("project_id") or "")), reverse=True)
    return {"projects": [payload for _, payload in projects]}


@app.post("/projects/{project_id}/reference-audio")
def upload_reference_audio(request: Request, project_id: str, req: ProjectReferenceAudioUploadRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)

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
            "project_id": _display_project_id(scoped_project_id),
        }
    )
    cache[audio_hash] = entry
    _write_reference_cache(paths.manifests, cache)

    artifact_url = f"/projects/{project_id}/artifact?path={quote(str(output_path), safe='')}"
    return {
        "project_id": _display_project_id(scoped_project_id),
        "audio_hash": audio_hash,
        "filename": output_path.name,
        "saved_path": str(output_path),
        "artifact_url": artifact_url,
    }


@app.get("/projects/{project_id}/reference-audio")
def list_reference_audio(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)

    pipeline.project_manager.ensure_project(scoped_project_id)

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
    return {"project_id": _display_project_id(scoped_project_id), "samples": items}


@app.post("/projects/{project_id}/reference-audio/delete")
def delete_reference_audio(request: Request, project_id: str, req: ProjectReferenceAudioDeleteRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    target_project_id = req.source_project_id.strip() if req.source_project_id else project_id
    target_scoped_project_id = _resolve_project_id_for_request(request, target_project_id)
    target_paths = pipeline.project_manager.ensure_project(target_scoped_project_id)

    audio_hash = req.audio_hash.strip().lower()
    cache = _load_reference_cache(target_paths.manifests)
    entry = cache.get(audio_hash)
    if not isinstance(entry, dict):
        raise HTTPException(status_code=404, detail="saved sample not found")

    saved_path = str(entry.get("audio_path") or "")
    del cache[audio_hash]
    _write_reference_cache(target_paths.manifests, cache)

    still_referenced = False
    for candidate_project_id in pipeline.list_projects():
        candidate_paths = pipeline.project_manager.get_paths(candidate_project_id)
        candidate_entry = _load_reference_cache(candidate_paths.manifests).get(audio_hash)
        if isinstance(candidate_entry, dict):
            still_referenced = True
            break

    removed_file = False
    if not still_referenced and saved_path:
        candidate_path = _resolve_reference_audio_path(target_paths.root.resolve(), saved_path)
        if candidate_path is not None and candidate_path.exists():
            candidate_path.unlink(missing_ok=True)
            removed_file = True

    return {
        "project_id": _display_project_id(scoped_project_id),
        "deleted": True,
        "audio_hash": audio_hash,
        "source_project_id": _display_project_id(target_scoped_project_id),
        "removed_file": removed_file,
    }


@app.get("/projects/{project_id}/script")
def get_project_script(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    paths = pipeline.project_manager.ensure_project(scoped_project_id)

    payload = _script_payload_for_response(_load_script_versions(paths.manifests))
    return {
        "project_id": _display_project_id(scoped_project_id),
        **payload,
    }


@app.get("/projects/{project_id}/settings")
def get_project_settings(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    settings = _load_project_settings(scoped_project_id)
    return {
        "project_id": _display_project_id(scoped_project_id),
        "settings": settings.model_dump(mode="json"),
    }


@app.put("/projects/{project_id}/settings")
def update_project_settings(request: Request, project_id: str, req: ProjectUiSettings):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    settings = _write_project_settings(scoped_project_id, req)
    return {
        "project_id": _display_project_id(scoped_project_id),
        "settings": settings.model_dump(mode="json"),
    }


@app.post("/projects/{project_id}/script")
def save_project_script(request: Request, project_id: str, req: ProjectScriptSaveRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    paths = pipeline.project_manager.ensure_project(scoped_project_id)

    text = str(req.text or "")
    source = str(req.source or "autosave").strip()[:32] or "autosave"
    script_versions = _load_script_versions(paths.manifests)
    rows = script_versions.get("versions") if isinstance(script_versions.get("versions"), list) else []
    current_version_id = str(script_versions.get("current_version_id") or "")
    current_entry = _find_script_entry(rows, current_version_id)

    if current_entry is not None and str(current_entry.get("text") or "") == text:
        payload = _script_payload_for_response(script_versions)
        return {
            "project_id": _display_project_id(scoped_project_id),
            "saved": False,
            **payload,
        }

    saved_at = datetime.now(timezone.utc).isoformat()
    version_id = f"script_{uuid.uuid4().hex[:12]}"
    if source == "autosave" and current_entry is not None and str(current_entry.get("source") or "") == "autosave":
        existing_version_id = str(current_entry.get("version_id") or "").strip()
        if existing_version_id:
            version_id = existing_version_id
            rows = [
                row
                for row in rows
                if str((row or {}).get("version_id") or "").strip() != existing_version_id
            ]

    version = {
        "version_id": version_id,
        "saved_at": saved_at,
        "source": source,
        "text": text,
        "word_count": len(re.findall(r"\S+", text)),
        "char_count": len(text),
        "preview": _script_preview(text),
    }
    rows.append(version)
    if len(rows) > SCRIPT_VERSION_HISTORY_LIMIT:
        rows = rows[-SCRIPT_VERSION_HISTORY_LIMIT:]
    script_versions = {
        "current_version_id": str(version["version_id"]),
        "versions": rows,
    }
    _write_script_versions(paths.manifests, script_versions)

    payload = _script_payload_for_response(script_versions)
    return {
        "project_id": _display_project_id(scoped_project_id),
        "saved": True,
        **payload,
    }


@app.post("/projects/{project_id}/script/restore")
def restore_project_script(request: Request, project_id: str, req: ProjectScriptRestoreRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    paths = pipeline.project_manager.ensure_project(scoped_project_id)

    script_versions = _load_script_versions(paths.manifests)
    rows = script_versions.get("versions") if isinstance(script_versions.get("versions"), list) else []
    version_id = req.version_id.strip()
    target_entry = _find_script_entry(rows, version_id)
    if target_entry is None:
        raise HTTPException(status_code=404, detail="script version not found")

    script_versions = {
        "current_version_id": version_id,
        "versions": rows,
    }
    _write_script_versions(paths.manifests, script_versions)

    payload = _script_payload_for_response(script_versions)
    return {
        "project_id": _display_project_id(scoped_project_id),
        "restored": True,
        **payload,
    }


@app.post("/projects/{project_id}/script/delete")
def delete_project_script_version(request: Request, project_id: str, req: ProjectScriptDeleteRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    paths = pipeline.project_manager.ensure_project(scoped_project_id)

    script_versions = _load_script_versions(paths.manifests)
    rows = script_versions.get("versions") if isinstance(script_versions.get("versions"), list) else []
    version_id = req.version_id.strip()
    remaining_rows = [
        row
        for row in rows
        if str((row or {}).get("version_id") or "") != version_id
    ]
    if len(remaining_rows) == len(rows):
        raise HTTPException(status_code=404, detail="script version not found")

    current_version_id = str(script_versions.get("current_version_id") or "").strip()
    if current_version_id == version_id:
        current_version_id = str((remaining_rows[-1] or {}).get("version_id") or "") if remaining_rows else ""

    updated_payload = {
        "current_version_id": current_version_id,
        "versions": remaining_rows,
    }
    _write_script_versions(paths.manifests, updated_payload)

    payload = _script_payload_for_response(updated_payload)
    return {
        "project_id": _display_project_id(scoped_project_id),
        "deleted": True,
        "deleted_version_id": version_id,
        **payload,
    }


@app.get("/projects/{project_id}/access")
def get_project_access(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    access = _resolve_access_for_user(request, scoped_project_id)
    owner = access.get("owner") if isinstance(access.get("owner"), dict) else {}
    collaborators = access.get("collaborators") if isinstance(access.get("collaborators"), list) else []
    return {
        "project_id": _display_project_id(scoped_project_id),
        "project_ref": scoped_project_id,
        "can_manage": bool(access.get("can_manage")),
        "owner": {
            "display_name": str(owner.get("display_name") or ""),
            "email": str(owner.get("email") or ""),
        },
        "collaborators": collaborators,
    }


@app.get("/projects/{project_id}/shareable-users")
def get_project_shareable_users(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    access = _resolve_access_for_user(request, scoped_project_id)
    if not bool(access.get("can_manage")):
        raise HTTPException(status_code=403, detail="project access denied")

    current_user = _current_user(request) or {}
    exclude_email = str(current_user.get("email") or "").strip().lower()
    return {
        "project_id": _display_project_id(scoped_project_id),
        "project_ref": scoped_project_id,
        "users": _fetch_shareable_users(exclude_email=exclude_email),
    }


@app.post("/projects/{project_id}/access/grant")
def grant_project_access(request: Request, project_id: str, req: ProjectAccessGrantRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    access = _resolve_access_for_user(request, scoped_project_id)
    if not bool(access.get("can_manage")):
        raise HTTPException(status_code=403, detail="project access denied")

    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="valid email is required")

    access_doc = _load_project_access(scoped_project_id)
    owner = access_doc.get("owner") if isinstance(access_doc.get("owner"), dict) else {}
    owner_email = str(owner.get("email") or "").strip().lower()
    if owner_email and email == owner_email:
        return {
            "project_id": _display_project_id(scoped_project_id),
            "project_ref": scoped_project_id,
            "collaborators": access_doc.get("collaborators", []),
            "updated": False,
        }

    collaborators_raw = access_doc.get("collaborators") if isinstance(access_doc.get("collaborators"), list) else []
    collaborators: list[dict[str, str]] = []
    found = False
    granted_by = str((_current_user(request) or {}).get("email") or (_current_user(request) or {}).get("sub") or "").strip()
    for row in collaborators_raw:
        if not isinstance(row, dict):
            continue
        existing_email = str(row.get("email") or "").strip().lower()
        if not existing_email:
            continue
        if existing_email == email:
            found = True
            collaborators.append(
                {
                    "email": existing_email,
                    "granted_at": str(row.get("granted_at") or datetime.now(timezone.utc).isoformat()),
                    "granted_by": str(row.get("granted_by") or granted_by),
                }
            )
        else:
            collaborators.append(
                {
                    "email": existing_email,
                    "granted_at": str(row.get("granted_at") or ""),
                    "granted_by": str(row.get("granted_by") or ""),
                }
            )

    if not found:
        collaborators.append(
            {
                "email": email,
                "granted_at": datetime.now(timezone.utc).isoformat(),
                "granted_by": granted_by,
            }
        )

    access_doc["collaborators"] = collaborators
    access_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_project_access(scoped_project_id, access_doc)

    return {
        "project_id": _display_project_id(scoped_project_id),
        "project_ref": scoped_project_id,
        "collaborators": collaborators,
        "updated": not found,
    }


@app.post("/projects/{project_id}/access/revoke")
def revoke_project_access(request: Request, project_id: str, req: ProjectAccessRevokeRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    access = _resolve_access_for_user(request, scoped_project_id)
    if not bool(access.get("can_manage")):
        raise HTTPException(status_code=403, detail="project access denied")

    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="valid email is required")

    access_doc = _load_project_access(scoped_project_id)
    collaborators_raw = access_doc.get("collaborators") if isinstance(access_doc.get("collaborators"), list) else []
    collaborators = [
        {
            "email": str(row.get("email") or "").strip().lower(),
            "granted_at": str(row.get("granted_at") or ""),
            "granted_by": str(row.get("granted_by") or ""),
        }
        for row in collaborators_raw
        if isinstance(row, dict) and str(row.get("email") or "").strip().lower() and str(row.get("email") or "").strip().lower() != email
    ]

    access_doc["collaborators"] = collaborators
    access_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_project_access(scoped_project_id, access_doc)

    return {
        "project_id": _display_project_id(scoped_project_id),
        "project_ref": scoped_project_id,
        "collaborators": collaborators,
        "updated": True,
    }


@app.post("/transcribe")
def transcribe(request: Request, req: TranscribeRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _resolve_project_id_for_request(request, req.project_id)})
    return pipeline.transcribe(scoped_req)


@app.post("/clip")
def clip(request: Request, req: ClipRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _resolve_project_id_for_request(request, req.project_id)})
    return pipeline.clip(scoped_req)


@app.post("/synthesize")
def synthesize(request: Request, req: SynthesisRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _resolve_project_id_for_request(request, req.project_id)})
    return pipeline.synthesize(scoped_req)


@app.post("/synthesize/simple")
def synthesize_simple(request: Request, req: SimpleSynthesisRequest):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, req.project_id)

    try:
        paths = pipeline.project_manager.ensure_project(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    owner_key, owner_label = _current_user_key_and_label(request)
    reference_cache = _load_reference_cache(paths.manifests)
    project_root = paths.root.resolve()
    reference_hash = ""
    source_filename = ""
    reference_path = None
    reference_text = None
    cached_entry: dict[str, object] = {}

    if req.voice_source == VoiceSource.REFERENCE:
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
                "project_id": _display_project_id(scoped_project_id),
                "origin_project_id": _display_project_id(source_project_id),
            }
            reference_cache[reference_hash] = cached_entry
            _write_reference_cache(paths.manifests, reference_cache)
        else:
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
                "project_id": _display_project_id(scoped_project_id),
            }
            reference_cache[reference_hash] = refreshed_entry
            _write_reference_cache(paths.manifests, reference_cache)
            cached_entry = refreshed_entry

        cached_reference_text = cached_entry.get("reference_text")
        reference_text = cached_reference_text if isinstance(cached_reference_text, str) and cached_reference_text.strip() else None

    output_name = _build_output_name(req.text, req.output_name)
    if req.voice_source == VoiceSource.BUILTIN:
        model_id = BUILTIN_MODEL_MODE_ALIASES["quality"] if req.quality == "high" else BUILTIN_MODEL_MODE_ALIASES["fast"]
    else:
        model_id = MODEL_MODE_ALIASES["quality"] if req.quality == "high" else MODEL_MODE_ALIASES["fast"]
    add_ums = req.add_ums or req.add_fillers
    add_ahs = req.add_ahs or req.add_fillers
    scripted_text = _inject_fillers(req.text, add_ums=add_ums, add_ahs=add_ahs)
    min_gap = round(max(0.15, req.average_gap_seconds * 0.7), 3)
    max_gap = round(min(2.5, req.average_gap_seconds * 1.3), 3)
    pause_config = PauseConfig(
        strategy="random_uniform_with_length_adjustment",
        min_seconds=min_gap,
        max_seconds=max_gap,
        seed=None,
    )
    max_new_tokens = 1400 if req.quality == "high" else 1000

    def run_local_job(*, job_id: str) -> None:
        synth_req = SynthesisRequest(
            project_id=scoped_project_id,
            text=scripted_text,
            voice_source=req.voice_source,
            reference_audio_path=reference_path,
            reference_text=reference_text,
            model_id=model_id,
            built_in_speaker=req.built_in_speaker,
            built_in_instruct=req.built_in_instruct,
            max_new_tokens=max_new_tokens,
            chunk_mode="sentence",
            pause_config=pause_config,
            output_format=req.output_format,
            output_name=output_name,
            generate_transcript=req.generate_transcript,
            voice_clone_authorized=req.voice_clone_authorized,
        )
        try:
            job = pipeline.orchestrator.run_synthesis_job(synth_req, job_id=job_id)
        except Exception:
            # Job failure details are persisted in manifest by orchestrator.
            return

        if req.voice_source == VoiceSource.REFERENCE and reference_path is not None:
            resolved_reference_text = _read_reference_text_from_job_outputs(job.outputs)
            _upsert_reference_cache_entry(
                paths=paths,
                audio_hash=reference_hash,
                audio_path=reference_path,
                source_filename=source_filename,
                owner_key=owner_key or "",
                owner_label=owner_label or "",
                reference_text=resolved_reference_text,
            )

    if SIMPLE_SYNTH_DEFAULT_TO_WORKER:
        _cancel_existing_project_worker_jobs(scoped_project_id)
        worker_payload: dict[str, object] = {
            "project_id": scoped_project_id,
            "text": scripted_text,
            "voice_source": req.voice_source,
            "reference_text": reference_text,
            "model_id": model_id,
            "built_in_speaker": req.built_in_speaker,
            "built_in_instruct": req.built_in_instruct,
            "max_new_tokens": max_new_tokens,
            "chunk_mode": "sentence",
            "pause_config": pause_config,
            "output_format": req.output_format,
            "output_name": output_name,
            "generate_transcript": req.generate_transcript,
            "voice_clone_authorized": True,
        }
        if req.voice_source == VoiceSource.REFERENCE and reference_path is not None:
            worker_payload["reference_audio_b64"] = base64.b64encode(reference_path.read_bytes()).decode("utf-8")
            worker_payload["reference_audio_filename"] = source_filename or reference_path.name
        worker_req = WorkerSynthesisEnqueueRequest(**worker_payload)
        worker_snapshot = _worker_availability_snapshot()
        queue_fallback_timeout_seconds = _worker_queue_fallback_timeout_seconds(worker_snapshot)
        job_id = worker_manager.enqueue_synthesis_job(
            worker_req,
            queue_fallback_timeout_seconds=queue_fallback_timeout_seconds,
        )
        if WORKER_FALLBACK_TO_LOCAL:
            _schedule_worker_fallback_watch(
                job_id=job_id,
                owner_key=owner_key or "",
                owner_label=owner_label or "",
                fallback_timeout_seconds=queue_fallback_timeout_seconds,
            )
        return {
            "job_id": job_id,
            "status": "queued",
            "stage": "queued_remote",
            "progress": 0.0,
            "project_id": _display_project_id(scoped_project_id),
            "output_name": output_name,
            "worker_mode": True,
            "fallback_enabled": WORKER_FALLBACK_TO_LOCAL,
            "fallback_timeout_seconds": queue_fallback_timeout_seconds,
            **worker_snapshot,
        }

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    thread = threading.Thread(target=lambda: run_local_job(job_id=job_id), name=f"radtts-{job_id}", daemon=True)
    thread.start()

    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0.0,
        "project_id": _display_project_id(scoped_project_id),
        "output_name": output_name,
        "worker_mode": False,
        "fallback_enabled": False,
        "fallback_timeout_seconds": 0,
    }


@app.post("/synthesize/worker")
def synthesize_worker(request: Request, req: WorkerSynthesisEnqueueRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _resolve_project_id_for_request(request, req.project_id)})
    _cancel_existing_project_worker_jobs(scoped_req.project_id)
    worker_snapshot = _worker_availability_snapshot()
    queue_fallback_timeout_seconds = _worker_queue_fallback_timeout_seconds(worker_snapshot)
    job_id = worker_manager.enqueue_synthesis_job(
        scoped_req,
        queue_fallback_timeout_seconds=queue_fallback_timeout_seconds,
    )
    owner_key, owner_label = _current_user_key_and_label(request)
    if WORKER_FALLBACK_TO_LOCAL:
        _schedule_worker_fallback_watch(
            job_id=job_id,
            owner_key=owner_key or "",
            owner_label=owner_label or "",
            fallback_timeout_seconds=queue_fallback_timeout_seconds,
        )
    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued_remote",
        "worker_mode": True,
        "fallback_enabled": WORKER_FALLBACK_TO_LOCAL,
        "fallback_timeout_seconds": queue_fallback_timeout_seconds,
        **worker_snapshot,
    }


@app.post("/captions")
def captions(request: Request, req: CaptionRequest):
    _require_auth(request)
    scoped_req = req.model_copy(update={"project_id": _scope_project_id(request, req.project_id)})
    return pipeline.captions(scoped_req)


@app.get("/projects/{project_id}/outputs")
def list_project_outputs(request: Request, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    try:
        rows = pipeline.list_outputs(scoped_project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc

    outputs: list[dict[str, object]] = []
    total_outputs = len(rows)
    for reverse_index, item in enumerate(reversed(rows)):
        audio_path = str(item.get("output_file") or "")
        captions_raw = item.get("captions") if isinstance(item.get("captions"), dict) else {}
        captions = {key: str(value) for key, value in (captions_raw or {}).items()}
        stage_durations_raw = item.get("stage_durations_seconds") if isinstance(item.get("stage_durations_seconds"), dict) else {}
        stage_durations = {
            str(key): float(value)
            for key, value in stage_durations_raw.items()
            if isinstance(key, str) and isinstance(value, int | float)
        }
        folder_path = str(Path(audio_path).parent) if audio_path else ""

        audio_encoded_path = quote(audio_path, safe="") if audio_path else ""
        audio_download_url = (
            f"/projects/{project_id}/artifact?path={audio_encoded_path}&download=true" if audio_path else None
        )
        audio_play_url = (
            f"/projects/{project_id}/artifact?path={audio_encoded_path}&download=false" if audio_path else None
        )
        srt_path = captions.get("srt")
        srt_download_url = (
            f"/projects/{project_id}/artifact?path={quote(srt_path, safe='')}&download=true" if srt_path else None
        )

        outputs.append(
            {
                "job_id": item.get("job_id"),
                "version_number": total_outputs - reverse_index,
                "created_at": item.get("created_at"),
                "output_name": Path(audio_path).stem if audio_path else None,
                "duration_seconds": item.get("duration_seconds"),
                "audio_tuning_label": item.get("audio_tuning_label"),
                "stage_durations_seconds": stage_durations,
                "audio_path": audio_path,
                "folder_path": folder_path,
                "audio_download_url": audio_download_url,
                "audio_play_url": audio_play_url,
                "captions": captions,
                "srt_download_url": srt_download_url,
            }
        )

    return {"project_id": _display_project_id(scoped_project_id), "outputs": outputs}


@app.get("/projects/{project_id}/artifact")
def get_project_artifact(request: Request, project_id: str, path: str, download: bool = True):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    project_paths = pipeline.project_manager.ensure_project(scoped_project_id)

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

    return FileResponse(path=candidate, filename=candidate.name if download else None)


@app.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    job = pipeline.get_job(scoped_project_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    if isinstance(job, dict) and _maybe_trigger_worker_fallback(
        request,
        scoped_project_id=scoped_project_id,
        job_payload=job,
    ):
        # Give the manifest a short moment to reflect the fallback claim stage.
        time.sleep(0.05)
        refreshed = pipeline.get_job(scoped_project_id, job_id)
        if isinstance(refreshed, dict):
            job = refreshed

    if isinstance(job, dict) and isinstance(job.get("project_id"), str):
        job["project_id"] = _display_project_id(job["project_id"])
    return job


@app.post("/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str, project_id: str):
    _require_auth(request)
    scoped_project_id = _resolve_project_id_for_request(request, project_id)
    if worker_manager.cancel_queued_job(
        job_id,
        reason="Cancellation requested before worker pickup.",
    ):
        return {
            "job_id": job_id,
            "project_id": _display_project_id(scoped_project_id),
            "status": "cancelled",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

    payload = pipeline.cancel_job(scoped_project_id, job_id)
    if isinstance(payload, dict) and isinstance(payload.get("project_id"), str):
        payload["project_id"] = _display_project_id(payload["project_id"])
    return payload


@app.get("/workers")
def list_workers(request: Request):
    _require_auth(request)
    workers = worker_manager.list_workers()
    return {"workers": [worker.model_dump(mode="json") for worker in workers]}


@app.get("/workers/status")
def workers_status(request: Request):
    _require_auth(request)
    return _worker_availability_snapshot()


@app.get("/voices/builtin")
def list_builtin_voices(request: Request, quality: str = "normal"):
    _require_auth(request)
    model_id = BUILTIN_MODEL_MODE_ALIASES["quality"] if quality == "high" else BUILTIN_MODEL_MODE_ALIASES["fast"]
    return {
        "quality": quality,
        "model_id": model_id,
        "voices": [
            {
                **voice,
                "preview_url": _builtin_voice_preview_url(str(voice["id"])),
            }
            for voice in QWEN_CUSTOM_VOICE_SPEAKERS
        ],
        "preview_text": BUILTIN_VOICE_PREVIEW_TEXT,
    }


@app.post("/voices/builtin/preview")
def preview_builtin_voice(request: Request, req: BuiltInVoicePreviewRequest):
    _require_auth(request)
    model_id = BUILTIN_MODEL_MODE_ALIASES["quality"] if req.quality == "high" else BUILTIN_MODEL_MODE_ALIASES["fast"]
    preview_text = (req.text or "").strip() or BUILTIN_VOICE_PREVIEW_TEXT
    cache_path = _builtin_voice_preview_cache_path(
        model_id=model_id,
        speaker=req.speaker,
        preview_text=preview_text,
    )
    if cache_path.exists():
        return {
            "speaker": req.speaker,
            "model_id": model_id,
            "preview_text": preview_text,
            "audio_b64": base64.b64encode(cache_path.read_bytes()).decode("utf-8"),
            "content_type": "audio/wav",
            "cached": True,
        }

    with tempfile.TemporaryDirectory(prefix="radtts_voice_preview_") as tmp:
        synth_req = SynthesisRequest(
            project_id="voice-preview",
            text=preview_text,
            voice_source=VoiceSource.BUILTIN,
            reference_audio_path=None,
            reference_text=None,
            model_id=model_id,
            built_in_speaker=req.speaker,
            built_in_instruct=None,
            max_new_tokens=180 if req.quality == "normal" else 260,
            chunk_mode="single",
            pause_config=PauseConfig(min_seconds=0.2, max_seconds=0.35, seed=1),
            output_format="wav",
            output_name="voice_preview",
            generate_transcript=False,
            voice_clone_authorized=True,
        )
        output_path, _, _ = pipeline.orchestrator.tts_service.synthesize(
            synth_req,
            output_dir=Path(tmp),
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(output_path.read_bytes())

        return {
            "speaker": req.speaker,
            "model_id": model_id,
            "preview_text": preview_text,
            "audio_b64": base64.b64encode(output_path.read_bytes()).decode("utf-8"),
            "content_type": "audio/wav",
            "cached": False,
        }


@app.post("/workers/invite", response_model=WorkerInviteResponse)
def worker_invite(request: Request, req: WorkerInviteRequest):
    _require_auth(request)
    token = worker_manager.issue_invite_token(req.capabilities)
    base_url = str(request.base_url).rstrip("/")
    helper_profile = _worker_helper_profile()
    macos_python_selector = (
        'if command -v python3.12 >/dev/null 2>&1; then RADTTS_PYTHON="$(command -v python3.12)"; '
        'elif command -v python3.11 >/dev/null 2>&1; then RADTTS_PYTHON="$(command -v python3.11)"; '
        'else RADTTS_PYTHON="$(command -v python3)"; fi'
    )
    install_command = (
        f"radtts-worker-install --server-url {base_url} --invite-token {token} "
        f"--helper-profile {helper_profile}"
    )
    install_command_windows = (
        "py -m pip install --upgrade pip; "
        "py -m pip install --index-url https://download.pytorch.org/whl/cpu "
        '--extra-index-url https://pypi.org/simple "radtts[asr,tts] @ git+https://github.com/radicalmove/RADTTS.git"; '
        f"py -m radtts.worker_setup --server-url {base_url} --invite-token {token} --helper-profile {helper_profile} --platform windows"
    )
    install_command_macos = (
        f"{macos_python_selector} && "
        'RADTTS_VENV="$HOME/.radtts/venv" && '
        'mkdir -p "$HOME/.radtts" && '
        '"$RADTTS_PYTHON" -m venv "$RADTTS_VENV" && '
        '"$RADTTS_VENV/bin/python" -m pip install --upgrade pip && '
        '"$RADTTS_VENV/bin/python" -m pip install "radtts[asr,tts] @ git+https://github.com/radicalmove/RADTTS.git" && '
        f'"$RADTTS_VENV/bin/python" -m radtts.worker_setup --server-url {base_url} --invite-token {token} --helper-profile {helper_profile} --platform macos --python-exe "$RADTTS_VENV/bin/python"'
    )
    install_command_linux = (
        "python3 -m pip install --upgrade pip && "
        "python3 -m pip install --index-url https://download.pytorch.org/whl/cpu "
        '--extra-index-url https://pypi.org/simple "radtts[asr,tts] @ git+https://github.com/radicalmove/RADTTS.git" && '
        f"python3 -m radtts.worker_setup --server-url {base_url} --invite-token {token} --helper-profile {helper_profile} --platform linux"
    )
    windows_installer_url = f"{base_url}/workers/bootstrap/windows.cmd?invite_token={quote(token)}"
    macos_installer_url = f"{base_url}/workers/bootstrap/macos.command?invite_token={quote(token)}"
    return WorkerInviteResponse(
        invite_token=token,
        expires_in_seconds=WORKER_INVITE_MAX_AGE_SECONDS,
        helper_profile=helper_profile,
        install_command=install_command,
        install_command_windows=install_command_windows,
        install_command_macos=install_command_macos,
        install_command_linux=install_command_linux,
        windows_installer_url=windows_installer_url,
        macos_installer_url=macos_installer_url,
    )


@app.post("/workers/register")
def worker_register(req: WorkerRegisterRequest):
    return worker_manager.register_worker(req).model_dump(mode="json")


@app.post("/workers/pull", response_model=WorkerPullResponse)
def worker_pull(req: WorkerPullRequest):
    try:
        job = worker_manager.pull_job(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return WorkerPullResponse(job=job)


@app.post("/workers/jobs/{job_id}/complete")
def worker_complete(job_id: str, req: WorkerJobCompleteRequest):
    try:
        status = worker_manager.complete_job(job_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"job_id": job_id, "status": status}


@app.post("/workers/jobs/{job_id}/progress")
def worker_progress(job_id: str, req: WorkerJobProgressRequest):
    try:
        status = worker_manager.progress_job(job_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"job_id": job_id, "status": status, "progress": req.progress}


@app.post("/workers/jobs/{job_id}/fail")
def worker_fail(job_id: str, req: WorkerJobFailRequest):
    try:
        status = worker_manager.fail_job(job_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"job_id": job_id, "status": status}


@app.get("/workers/bootstrap/windows.cmd")
def worker_bootstrap_windows_cmd(
    request: Request,
    invite_token: str = Query(min_length=10),
):
    base_url = str(request.base_url).rstrip("/")
    safe_token = invite_token.replace('"', "")
    helper_profile = _worker_helper_profile()
    script = (
        "@echo off\r\n"
        "setlocal\r\n"
        "echo Installing RADTTS worker on this Windows device...\r\n"
        "py -m pip install --upgrade pip\r\n"
        "if errorlevel 1 goto :fail\r\n"
        'py -m pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple "radtts[asr,tts] @ git+https://github.com/radicalmove/RADTTS.git"\r\n'
        "if errorlevel 1 goto :fail\r\n"
        f"py -m radtts.worker_setup --server-url {base_url} --invite-token {safe_token} --helper-profile {helper_profile} --platform windows\r\n"
        "if errorlevel 1 goto :fail\r\n"
        "echo.\r\n"
        "echo Worker is installed and will start automatically in the background at login.\r\n"
        "echo You can close this window.\r\n"
        "pause\r\n"
        "exit /b 0\r\n"
        "\r\n"
        ":fail\r\n"
        "echo.\r\n"
        "echo Setup failed. Please send this screenshot to support.\r\n"
        "pause\r\n"
        "exit /b 1\r\n"
    )
    response = PlainTextResponse(script, media_type="text/plain")
    response.headers["Content-Disposition"] = 'attachment; filename="radtts-worker-setup.cmd"'
    return response


@app.get("/workers/bootstrap/macos.command")
def worker_bootstrap_macos_command(
    request: Request,
    invite_token: str = Query(min_length=10),
):
    base_url = str(request.base_url).rstrip("/")
    safe_token = invite_token.replace('"', "")
    helper_profile = _worker_helper_profile()
    script = (
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "echo \"Installing RADTTS worker on this Mac...\"\n"
        "if command -v python3.12 >/dev/null 2>&1; then RADTTS_PYTHON=\"$(command -v python3.12)\";\n"
        "elif command -v python3.11 >/dev/null 2>&1; then RADTTS_PYTHON=\"$(command -v python3.11)\";\n"
        "else RADTTS_PYTHON=\"$(command -v python3)\"; fi\n"
        "RADTTS_VENV=\"$HOME/.radtts/venv\"\n"
        "mkdir -p \"$HOME/.radtts\"\n"
        "\"$RADTTS_PYTHON\" -m venv \"$RADTTS_VENV\"\n"
        "\"$RADTTS_VENV/bin/python\" -m pip install --upgrade pip\n"
        "\"$RADTTS_VENV/bin/python\" -m pip install \"radtts[asr,tts] @ git+https://github.com/radicalmove/RADTTS.git\"\n"
        f"\"$RADTTS_VENV/bin/python\" -m radtts.worker_setup --server-url {base_url} --invite-token {safe_token} --helper-profile {helper_profile} --platform macos --python-exe \"$RADTTS_VENV/bin/python\"\n"
        "echo \"\"\n"
        "echo \"Worker is installed and will start automatically in the background at login.\"\n"
        "echo \"You can close this window.\"\n"
        "read -p \"Press Enter to close...\" _\n"
    )
    response = PlainTextResponse(script, media_type="text/plain")
    response.headers["Content-Disposition"] = 'attachment; filename="radtts-worker-setup.command"'
    return response


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
