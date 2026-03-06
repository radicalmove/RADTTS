"""Distributed worker queue manager for offloaded synthesis jobs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from radtts.manifests import ManifestStore
from radtts.models import (
    JobRecord,
    JobStatus,
    OutputMetadata,
    QualityReport,
    WorkerCapability,
    WorkerJobCompleteRequest,
    WorkerJobFailRequest,
    WorkerPullRequest,
    WorkerQueuedJob,
    WorkerRegisterRequest,
    WorkerRegisterResponse,
    WorkerSummary,
    WorkerSynthesisEnqueueRequest,
)
from radtts.project import ProjectManager


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _slugify_filename(name: str) -> str:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_", "."}).strip(".")
    return safe or "reference_audio.wav"


class WorkerManager:
    def __init__(
        self,
        *,
        projects_root: Path,
        worker_secret: str,
        invite_max_age_seconds: int = 86400,
    ):
        self.projects_root = Path(projects_root)
        self.project_manager = ProjectManager(self.projects_root)
        self.worker_secret = worker_secret
        self.invite_max_age_seconds = invite_max_age_seconds

        self.worker_dir = self.projects_root / "_worker"
        self.workers_path = self.worker_dir / "workers.json"
        self.jobs_path = self.worker_dir / "jobs.json"
        self.worker_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._ensure_files()

    def _ensure_files(self) -> None:
        for path in (self.workers_path, self.jobs_path):
            if not path.exists():
                path.write_text("[]", encoding="utf-8")

    def _read_list(self, path: Path) -> list[dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return []

    def _write_list(self, path: Path, payload: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _invite_serializer(self) -> URLSafeTimedSerializer:
        return URLSafeTimedSerializer(self.worker_secret, salt="radtts-worker-invite-v1")

    def issue_invite_token(self, capabilities: list[WorkerCapability] | None = None) -> str:
        payload = {
            "capabilities": [cap.value for cap in (capabilities or [WorkerCapability.SYNTHESIZE])],
            "issued_at": _now_iso(),
        }
        return self._invite_serializer().dumps(payload)

    def register_worker(self, req: WorkerRegisterRequest) -> WorkerRegisterResponse:
        try:
            invite_payload = self._invite_serializer().loads(
                req.invite_token,
                max_age=self.invite_max_age_seconds,
            )
        except SignatureExpired as exc:
            raise ValueError("invite token expired") from exc
        except BadSignature as exc:
            raise ValueError("invalid invite token") from exc

        allowed = set(invite_payload.get("capabilities") or [WorkerCapability.SYNTHESIZE.value])
        requested = [cap.value for cap in req.capabilities]
        capabilities = [cap for cap in requested if cap in allowed]
        if not capabilities:
            raise ValueError("worker capabilities do not match invite token")

        worker_id = f"wrk_{uuid.uuid4().hex[:10]}"
        api_key = secrets.token_urlsafe(32)
        now = _now_iso()

        record = {
            "worker_id": worker_id,
            "worker_name": req.worker_name,
            "capabilities": capabilities,
            "status": "active",
            "created_at": now,
            "last_seen_at": now,
            "api_key_hash": _hash_key(api_key),
        }

        with self._lock:
            workers = self._read_list(self.workers_path)
            workers.append(record)
            self._write_list(self.workers_path, workers)

        return WorkerRegisterResponse(worker_id=worker_id, api_key=api_key, poll_interval_seconds=5)

    def _authenticate_worker(self, req: WorkerPullRequest) -> dict[str, Any]:
        workers = self._read_list(self.workers_path)
        for worker in workers:
            if worker.get("worker_id") != req.worker_id:
                continue
            expected_hash = worker.get("api_key_hash", "")
            provided_hash = _hash_key(req.api_key)
            if not hmac.compare_digest(expected_hash, provided_hash):
                break
            worker["last_seen_at"] = _now_iso()
            self._write_list(self.workers_path, workers)
            return worker
        raise PermissionError("invalid worker credentials")

    def list_workers(self) -> list[WorkerSummary]:
        workers = self._read_list(self.workers_path)
        result: list[WorkerSummary] = []
        for worker in workers:
            caps = [WorkerCapability(cap) for cap in worker.get("capabilities", [])]
            result.append(
                WorkerSummary(
                    worker_id=worker["worker_id"],
                    worker_name=worker.get("worker_name", worker["worker_id"]),
                    capabilities=caps,
                    status=worker.get("status", "active"),
                    last_seen_at=worker.get("last_seen_at"),
                    created_at=worker.get("created_at", _now_iso()),
                )
            )
        return result

    def enqueue_synthesis_job(self, req: WorkerSynthesisEnqueueRequest) -> str:
        paths = self.project_manager.ensure_project(req.project_id)
        store = ManifestStore(paths.manifests)

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = _now_iso()

        job_record = JobRecord(
            id=job_id,
            project_id=req.project_id,
            status=JobStatus.QUEUED,
            stage="queued_remote",
            progress=0.0,
            logs=[f"{now} queued for worker execution"],
        )
        store.upsert_job(job_record)

        queue_entry = {
            "job_id": job_id,
            "project_id": req.project_id,
            "status": "queued",
            "type": "synthesize",
            "required_capabilities": [WorkerCapability.SYNTHESIZE.value],
            "assigned_worker_id": None,
            "created_at": now,
            "updated_at": now,
            "payload": req.model_dump(mode="json"),
            "error": None,
        }

        with self._lock:
            jobs = self._read_list(self.jobs_path)
            jobs.append(queue_entry)
            self._write_list(self.jobs_path, jobs)

        return job_id

    def claim_job_for_local_fallback(self, job_id: str, *, reason: str) -> WorkerSynthesisEnqueueRequest | None:
        with self._lock:
            jobs = self._read_list(self.jobs_path)
            entry = next((item for item in jobs if item.get("job_id") == job_id), None)
            if not entry:
                return None
            if entry.get("status") != "queued":
                return None

            entry["status"] = "fallback_local"
            entry["assigned_worker_id"] = "local-fallback"
            entry["updated_at"] = _now_iso()
            self._write_list(self.jobs_path, jobs)

        self._update_job_manifest(
            project_id=entry["project_id"],
            job_id=job_id,
            status=JobStatus.RUNNING,
            stage="fallback_local",
            progress=0.08,
            log=reason,
        )
        return WorkerSynthesisEnqueueRequest(**entry["payload"])

    def cancel_queued_job(self, job_id: str, *, reason: str) -> bool:
        with self._lock:
            jobs = self._read_list(self.jobs_path)
            entry = next((item for item in jobs if item.get("job_id") == job_id), None)
            if not entry:
                return False
            if entry.get("status") != "queued":
                return False

            entry["status"] = "cancelled"
            entry["error"] = reason
            entry["updated_at"] = _now_iso()
            self._write_list(self.jobs_path, jobs)

        self._update_job_manifest(
            project_id=entry["project_id"],
            job_id=job_id,
            status=JobStatus.CANCELLED,
            stage="cancelled",
            progress=0.0,
            error=reason,
            log=reason,
        )
        return True

    def pull_job(self, req: WorkerPullRequest) -> WorkerQueuedJob | None:
        with self._lock:
            worker = self._authenticate_worker(req)
            jobs = self._read_list(self.jobs_path)

            for entry in jobs:
                if entry.get("status") != "queued":
                    continue

                required = set(entry.get("required_capabilities") or [])
                caps = set(worker.get("capabilities") or [])
                if not required.issubset(caps):
                    continue

                entry["status"] = "running"
                entry["assigned_worker_id"] = req.worker_id
                entry["updated_at"] = _now_iso()
                self._write_list(self.jobs_path, jobs)

                self._update_job_manifest(
                    project_id=entry["project_id"],
                    job_id=entry["job_id"],
                    status=JobStatus.RUNNING,
                    stage="worker_running",
                    progress=0.25,
                    log=f"worker {req.worker_id} started processing",
                )

                return WorkerQueuedJob(
                    job_id=entry["job_id"],
                    project_id=entry["project_id"],
                    type="synthesize",
                    payload=entry["payload"],
                )

        return None

    def complete_job(self, job_id: str, req: WorkerJobCompleteRequest) -> None:
        pull_req = WorkerPullRequest(worker_id=req.worker_id, api_key=req.api_key)
        with self._lock:
            self._authenticate_worker(pull_req)
            jobs = self._read_list(self.jobs_path)
            entry = next((item for item in jobs if item.get("job_id") == job_id), None)
            if not entry:
                raise FileNotFoundError(f"worker job not found: {job_id}")
            if entry.get("assigned_worker_id") != req.worker_id:
                raise PermissionError("job is assigned to a different worker")

            entry["status"] = "completed"
            entry["updated_at"] = _now_iso()
            self._write_list(self.jobs_path, jobs)

        payload = WorkerSynthesisEnqueueRequest(**entry["payload"])
        paths = self.project_manager.ensure_project(payload.project_id)
        store = ManifestStore(paths.manifests)

        output_suffix = req.output_format.value
        output_path = paths.assets_generated_audio / f"{payload.output_name}.{output_suffix}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(req.output_audio_b64.encode("utf-8")))

        reference_filename = _slugify_filename(payload.reference_audio_filename)
        reference_path = paths.assets_reference_audio / f"{payload.output_name}_{reference_filename}"
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_bytes(base64.b64decode(payload.reference_audio_b64.encode("utf-8")))

        captions: dict[str, Path] = {}
        if req.captions_txt is not None:
            txt_path = paths.captions / f"{payload.output_name}.txt"
            txt_path.write_text(req.captions_txt, encoding="utf-8")
            captions["txt"] = txt_path
        if req.captions_srt is not None:
            srt_path = paths.captions / f"{payload.output_name}.srt"
            srt_path.write_text(req.captions_srt, encoding="utf-8")
            captions["srt"] = srt_path
        if req.captions_vtt is not None:
            vtt_path = paths.captions / f"{payload.output_name}.vtt"
            vtt_path.write_text(req.captions_vtt, encoding="utf-8")
            captions["vtt"] = vtt_path

        quality_obj = None
        if req.quality:
            quality_obj = QualityReport(**req.quality)

        metadata = OutputMetadata(
            output_file=output_path,
            duration_seconds=req.duration_seconds,
            model=payload.model_id,
            reference_audio=reference_path,
            reference_text=req.reference_text,
            input_text=payload.text,
            chunk_mode=payload.chunk_mode,
            pause_seconds=req.pause_seconds,
            max_new_tokens=payload.max_new_tokens,
            output_format=req.output_format,
            seed=payload.pause_config.seed,
            project_id=payload.project_id,
            job_id=job_id,
            captions={key: value for key, value in captions.items()} or None,
            quality=quality_obj,
            stage_durations_seconds=req.stage_durations_seconds,
        )
        metadata_path = paths.manifests / f"{payload.output_name}.metadata.json"
        store.write_output_file(metadata_path, metadata)
        store.append_output(metadata)

        outputs = {
            "audio_path": str(output_path),
            "captions": {key: str(path) for key, path in captions.items()},
            "metadata_path": str(metadata_path),
        }
        self._update_job_manifest(
            project_id=payload.project_id,
            job_id=job_id,
            status=JobStatus.COMPLETED,
            stage="completed",
            progress=1.0,
            outputs=outputs,
            log=f"worker {req.worker_id} completed job",
        )

    def fail_job(self, job_id: str, req: WorkerJobFailRequest) -> None:
        pull_req = WorkerPullRequest(worker_id=req.worker_id, api_key=req.api_key)
        with self._lock:
            self._authenticate_worker(pull_req)
            jobs = self._read_list(self.jobs_path)
            entry = next((item for item in jobs if item.get("job_id") == job_id), None)
            if not entry:
                raise FileNotFoundError(f"worker job not found: {job_id}")
            if entry.get("assigned_worker_id") != req.worker_id:
                raise PermissionError("job is assigned to a different worker")

            entry["status"] = "failed"
            entry["error"] = req.error
            entry["updated_at"] = _now_iso()
            self._write_list(self.jobs_path, jobs)

        self._update_job_manifest(
            project_id=entry["project_id"],
            job_id=job_id,
            status=JobStatus.FAILED,
            stage="failed",
            progress=1.0,
            error=req.error,
            log=f"worker {req.worker_id} failed job: {req.error}",
        )

    def _update_job_manifest(
        self,
        *,
        project_id: str,
        job_id: str,
        status: JobStatus,
        stage: str,
        progress: float,
        error: str | None = None,
        outputs: dict[str, Any] | None = None,
        log: str | None = None,
    ) -> None:
        paths = self.project_manager.ensure_project(project_id)
        store = ManifestStore(paths.manifests)
        payload = store.get_job(job_id)
        if payload:
            job = JobRecord(**payload)
        else:
            job = JobRecord(
                id=job_id,
                project_id=project_id,
                status=status,
                stage=stage,
                progress=progress,
            )

        job.status = status
        job.stage = stage
        job.progress = progress
        job.updated_at = datetime.now(timezone.utc)
        if error is not None:
            job.error = error
        if outputs is not None:
            job.outputs = outputs
        if log:
            job.logs.append(f"{_now_iso()} {log}")

        store.upsert_job(job)
