"""Pipeline orchestrator with progress, retries, and metadata persistence."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from radtts.constants import DEFAULT_STAGE_RETRIES, DEFAULT_STAGE_TIMEOUTS
from radtts.exceptions import JobCancelledError
from radtts.manifests import ManifestStore
from radtts.models import JobRecord, JobStatus, OutputMetadata, SynthesisRequest
from radtts.project import ProjectManager
from radtts.services.captions import CaptionService
from radtts.services.quality import QualityService
from radtts.services.tts import TTSService
from radtts.utils.audio import probe_duration_seconds
from radtts.utils.runtime import Heartbeat, run_with_retry_timeout


class PipelineOrchestrator:
    def __init__(
        self,
        *,
        projects_root: Path | str = Path("projects"),
        heartbeat_seconds: int = 10,
        stage_timeouts: dict[str, int] | None = None,
        stage_retries: dict[str, int] | None = None,
    ):
        self.project_manager = ProjectManager(projects_root)
        self.tts_service = TTSService()
        self.caption_service = CaptionService()
        self.quality_service = QualityService()
        self.heartbeat_seconds = heartbeat_seconds
        self.stage_timeouts = {**DEFAULT_STAGE_TIMEOUTS, **(stage_timeouts or {})}
        self.stage_retries = {**DEFAULT_STAGE_RETRIES, **(stage_retries or {})}
        self._cancelled: set[str] = set()

    def run_synthesis_job(self, req: SynthesisRequest) -> JobRecord:
        paths = self.project_manager.ensure_project(req.project_id)
        store = ManifestStore(paths.manifests)

        job = JobRecord(
            id=f"job_{uuid.uuid4().hex[:12]}",
            project_id=req.project_id,
            status=JobStatus.QUEUED,
            stage="queued",
            progress=0.0,
        )
        store.upsert_job(job)

        self._update_job(store, job, status=JobStatus.RUNNING, stage="model_load", progress=0.05)

        stage_durations: dict[str, float] = {}

        def ensure_not_cancelled() -> bool:
            return job.id in self._cancelled

        def run_stage(stage_name: str, progress: float, fn: Callable[[], object]) -> object:
            self._update_job(store, job, stage=stage_name, progress=progress)

            heartbeat = Heartbeat(
                interval_seconds=self.heartbeat_seconds,
                label=stage_name,
                on_beat=lambda msg: self._log_job(store, job, msg),
            )
            heartbeat.start()
            started = time.monotonic()
            try:
                result = run_with_retry_timeout(
                    stage_name=stage_name,
                    fn=fn,
                    timeout_seconds=self.stage_timeouts[stage_name],
                    retries=self.stage_retries[stage_name],
                    on_log=lambda msg: self._log_job(store, job, msg),
                )
                stage_durations[stage_name] = round(time.monotonic() - started, 3)
                return result
            finally:
                heartbeat.stop()

        def model_load() -> None:
            if ensure_not_cancelled():
                raise JobCancelledError("cancelled before model load")
            self.tts_service.ensure_supported_model(req.model_id)
            self.tts_service._load_model(req.model_id)  # noqa: SLF001

        try:
            run_stage("model_load", 0.10, model_load)

            stage_state = {"name": "generation"}

            def on_tts_progress(message: str) -> None:
                if message.lower().startswith("stitching"):
                    stage_state["name"] = "stitching"
                    self._update_job(store, job, stage="stitching", progress=0.72)
                else:
                    self._update_job(store, job, stage=stage_state["name"], progress=0.45)
                self._log_job(store, job, message)

            def generation() -> tuple[Path, list[float], str]:
                if ensure_not_cancelled():
                    raise JobCancelledError("cancelled before generation")
                return self.tts_service.synthesize(
                    req,
                    output_dir=paths.assets_generated_audio,
                    on_progress=on_tts_progress,
                    cancel_check=ensure_not_cancelled,
                )

            output_path, pause_seconds, reference_text = run_stage("generation", 0.35, generation)

            if stage_state["name"] == "stitching":
                stage_durations["stitching"] = stage_durations.get("generation", 0.0)

            if ensure_not_cancelled():
                self._update_job(store, job, status=JobStatus.CANCELLED, stage="cancelled", progress=0.0)
                return job

            def captioning():
                if ensure_not_cancelled():
                    raise JobCancelledError("cancelled before captioning")
                return self.caption_service.generate(
                    audio_path=output_path,
                    output_dir=paths.captions,
                    name=req.output_name,
                    language=None,
                )

            captions = run_stage("captioning", 0.85, captioning)
            output_duration = probe_duration_seconds(output_path)

            quality = self.quality_service.evaluate(
                text=req.text,
                duration_seconds=output_duration,
                pause_seconds=pause_seconds,
            )

            metadata = OutputMetadata(
                output_file=output_path,
                duration_seconds=output_duration,
                model=req.model_id,
                reference_audio=req.reference_audio_path,
                reference_text=reference_text,
                input_text=req.text,
                chunk_mode=req.chunk_mode,
                pause_seconds=pause_seconds,
                max_new_tokens=req.max_new_tokens,
                output_format=req.output_format,
                seed=req.pause_config.seed,
                project_id=req.project_id,
                job_id=job.id,
                captions={
                    "txt": captions.txt_path,
                    "srt": captions.srt_path,
                    "vtt": captions.vtt_path,
                },
                quality=quality,
                stage_durations_seconds=stage_durations,
            )

            metadata_path = paths.manifests / f"{req.output_name}.metadata.json"
            store.write_output_file(metadata_path, metadata)
            store.append_output(metadata)

            job.outputs = {
                "audio_path": str(output_path),
                "captions": {
                    "txt": str(captions.txt_path),
                    "srt": str(captions.srt_path),
                    "vtt": str(captions.vtt_path),
                },
                "metadata_path": str(metadata_path),
            }
            self._update_job(
                store,
                job,
                status=JobStatus.COMPLETED,
                stage="completed",
                progress=1.0,
            )
            return job
        except JobCancelledError as exc:
            job.error = str(exc)
            self._update_job(store, job, status=JobStatus.CANCELLED, stage="cancelled", progress=0.0)
            return job
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc)
            self._update_job(store, job, status=JobStatus.FAILED, stage="failed", progress=1.0)
            raise

    def cancel_job(self, project_id: str, job_id: str) -> None:
        self.project_manager.ensure_project(project_id)
        self._cancelled.add(job_id)

    def get_job(self, project_id: str, job_id: str) -> dict[str, object] | None:
        paths = self.project_manager.ensure_project(project_id)
        store = ManifestStore(paths.manifests)
        return store.get_job(job_id)

    def _update_job(
        self,
        store: ManifestStore,
        job: JobRecord,
        *,
        status: JobStatus | None = None,
        stage: str | None = None,
        progress: float | None = None,
    ) -> None:
        if status is not None:
            job.status = status
        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = progress
        job.updated_at = datetime.now(timezone.utc)
        store.upsert_job(job)

    def _log_job(self, store: ManifestStore, job: JobRecord, message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        job.logs.append(f"{ts} {message}")
        job.updated_at = datetime.now(timezone.utc)
        store.upsert_job(job)
