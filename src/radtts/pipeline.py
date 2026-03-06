"""High-level pipeline facade for CLI and API consumption."""

from __future__ import annotations

import json
from pathlib import Path

from radtts.manifests import ManifestStore
from radtts.models import (
    BoundaryReport,
    CaptionArtifacts,
    CaptionRequest,
    ClipRequest,
    ProjectCreateRequest,
    SynthesisRequest,
    TranscribeRequest,
    now_utc_iso,
)
from radtts.orchestrator import PipelineOrchestrator
from radtts.project import ProjectManager
from radtts.services.asr import ASRService
from radtts.services.clip import ClipService


class RADTTSPipeline:
    def __init__(self, projects_root: Path | str = Path("projects")):
        self.project_manager = ProjectManager(projects_root)
        self.orchestrator = PipelineOrchestrator(projects_root=projects_root)
        self.asr_service = ASRService()
        self.clip_service = ClipService()

    def create_project(self, req: ProjectCreateRequest) -> dict[str, str]:
        paths = self.project_manager.create_project(
            req.project_id,
            course=req.course,
            module=req.module,
            lesson=req.lesson,
        )
        return {"project_root": str(paths.root)}

    def list_projects(self) -> list[str]:
        return self.project_manager.list_projects()

    def list_outputs(self, project_id: str) -> list[dict[str, object]]:
        paths = self.project_manager.ensure_project(project_id)
        store = ManifestStore(paths.manifests)
        return store.list_outputs()

    def transcribe(self, req: TranscribeRequest) -> dict[str, str]:
        paths = self.project_manager.ensure_project(req.project_id)
        name = req.name or req.audio_path.stem
        self.asr_service.model_size = req.model
        artifacts, _ = self.asr_service.transcribe(
            req.audio_path,
            paths.transcripts,
            name=name,
            language=req.language,
            beam_size=req.beam_size,
        )
        return {
            "segments_json_path": str(artifacts.segments_json_path),
            "txt_path": str(artifacts.txt_path),
            "srt_path": str(artifacts.srt_path),
        }

    def clip(self, req: ClipRequest) -> dict[str, object]:
        paths = self.project_manager.ensure_project(req.project_id)
        segments = self.asr_service.load_segments(req.segments_json_path)
        output_path, report = self.clip_service.extract_verified_clip(
            req=req,
            segments=segments,
            output_dir=paths.assets_source_audio,
        )
        report_path = paths.manifests / f"{req.output_name}.clip.boundary.json"
        self._write_boundary_report(report_path, report)
        return {
            "clip_path": str(output_path),
            "report_path": str(report_path),
            "warnings": report.warnings,
        }

    def synthesize(self, req: SynthesisRequest) -> dict[str, object]:
        job = self.orchestrator.run_synthesis_job(req)
        return {
            "job_id": job.id,
            "status": job.status.value,
            "stage": job.stage,
            "outputs": job.outputs,
        }

    def captions(self, req: CaptionRequest) -> dict[str, str]:
        paths = self.project_manager.ensure_project(req.project_id)
        artifacts = self.orchestrator.caption_service.generate(
            audio_path=req.audio_path,
            output_dir=paths.captions,
            name=req.name or req.audio_path.stem,
            language=req.language,
        )
        return {
            "txt_path": str(artifacts.txt_path),
            "srt_path": str(artifacts.srt_path),
            "vtt_path": str(artifacts.vtt_path),
        }

    def get_job(self, project_id: str, job_id: str) -> dict[str, object] | None:
        return self.orchestrator.get_job(project_id, job_id)

    def cancel_job(self, project_id: str, job_id: str) -> dict[str, str]:
        self.orchestrator.cancel_job(project_id, job_id)
        return {
            "job_id": job_id,
            "project_id": project_id,
            "status": "cancel_requested",
            "requested_at": now_utc_iso(),
        }

    @staticmethod
    def _write_boundary_report(path: Path, report: BoundaryReport) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
