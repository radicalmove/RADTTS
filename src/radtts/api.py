"""FastAPI service exposing RADTTS pipeline endpoints."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlencode

from radtts.models import (
    CaptionRequest,
    ClipRequest,
    ProjectCreateRequest,
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
    from fastapi.responses import HTMLResponse, RedirectResponse
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
        },
    )


@app.post("/projects")
def create_project(request: Request, req: ProjectCreateRequest):
    _require_auth(request)
    return pipeline.create_project(req)


@app.post("/transcribe")
def transcribe(request: Request, req: TranscribeRequest):
    _require_auth(request)
    return pipeline.transcribe(req)


@app.post("/clip")
def clip(request: Request, req: ClipRequest):
    _require_auth(request)
    return pipeline.clip(req)


@app.post("/synthesize")
def synthesize(request: Request, req: SynthesisRequest):
    _require_auth(request)
    return pipeline.synthesize(req)


@app.post("/synthesize/worker")
def synthesize_worker(request: Request, req: WorkerSynthesisEnqueueRequest):
    _require_auth(request)
    job_id = worker_manager.enqueue_synthesis_job(req)
    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued_remote",
        "worker_mode": True,
    }


@app.post("/captions")
def captions(request: Request, req: CaptionRequest):
    _require_auth(request)
    return pipeline.captions(req)


@app.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str, project_id: str):
    _require_auth(request)
    job = pipeline.get_job(project_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.post("/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str, project_id: str):
    _require_auth(request)
    return pipeline.cancel_job(project_id, job_id)


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
