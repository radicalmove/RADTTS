"""FastAPI service exposing RADTTS pipeline endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from radtts.models import (
    CaptionRequest,
    ClipRequest,
    ProjectCreateRequest,
    SynthesisRequest,
    TranscribeRequest,
)
from radtts.pipeline import RADTTSPipeline
from radtts.constants import DEFAULT_PRESETS, MODEL_MODE_ALIASES, SUPPORTED_BASE_MODELS

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is not installed. Install with 'pip install -e .[api]'.") from exc


PROJECTS_ROOT = Path(os.environ.get("RADTTS_PROJECTS_ROOT", "projects"))
MODULE_ROOT = Path(__file__).resolve().parent
pipeline = RADTTSPipeline(projects_root=PROJECTS_ROOT)
app = FastAPI(title="RADTTS API", version="0.1.0")
app.mount("/static", StaticFiles(directory=MODULE_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(MODULE_ROOT / "templates"))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "models": SUPPORTED_BASE_MODELS,
            "model_modes": MODEL_MODE_ALIASES,
            "presets": DEFAULT_PRESETS,
        },
    )


@app.post("/projects")
def create_project(req: ProjectCreateRequest):
    return pipeline.create_project(req)


@app.post("/transcribe")
def transcribe(req: TranscribeRequest):
    return pipeline.transcribe(req)


@app.post("/clip")
def clip(req: ClipRequest):
    return pipeline.clip(req)


@app.post("/synthesize")
def synthesize(req: SynthesisRequest):
    return pipeline.synthesize(req)


@app.post("/captions")
def captions(req: CaptionRequest):
    return pipeline.captions(req)


@app.get("/jobs/{job_id}")
def get_job(job_id: str, project_id: str):
    job = pipeline.get_job(project_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, project_id: str):
    return pipeline.cancel_job(project_id, job_id)


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
