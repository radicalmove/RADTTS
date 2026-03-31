"""Worker daemon for distributed RADTTS synthesis jobs."""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import logging
import os
import re
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import requests

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from radtts.models import SynthesisRequest, WorkerSynthesisEnqueueRequest
from radtts.progress import (
    CAPTIONING_PROGRESS_START,
    UPLOAD_PROGRESS,
    generation_progress_for_chunk,
    stitching_progress_for_output,
)
from radtts.services.captions import CaptionService
from radtts.services.quality import QualityService
from radtts.services.tts import TTSService
from radtts.utils.audio import probe_duration_seconds
from radtts.utils.runtime import run_with_retry_timeout
from radtts.utils.text import estimated_chunk_count, recommended_generation_timeout_seconds

_GENERATION_CHUNK_RE = re.compile(r"^generation chunk (\d+)/(\d+)$", re.IGNORECASE)
DEFAULT_WORKER_GENERATION_TIMEOUT_SECONDS = 600
DEFAULT_HEAVY_REFERENCE_GENERATION_TIMEOUT_SECONDS = 1800
LOG = logging.getLogger("radtts.worker")


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _pid_looks_like_radtts_worker(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return False
    command = str(result.stdout or "").strip().lower()
    return "radtts.worker_client" in command or "radtts.worker" in command


def _terminate_pid(pid: int, *, timeout_seconds: float = 5.0) -> bool:
    try:
        os.kill(pid, 15)
    except OSError:
        return True
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_is_running(pid):
            return True
        time.sleep(0.1)
    try:
        os.kill(pid, 9)
    except OSError:
        return not _pid_is_running(pid)
    time.sleep(0.1)
    return not _pid_is_running(pid)


@contextlib.contextmanager
def _worker_single_instance(config_path: Path):
    if fcntl is None:
        yield
        return

    lock_path = config_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+", encoding="utf-8")

    def _write_current_pid() -> None:
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()

    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_file.seek(0)
            raw_pid = lock_file.read().strip()
            prior_pid = int(raw_pid) if raw_pid.isdigit() else None
            if prior_pid and prior_pid != os.getpid() and _pid_is_running(prior_pid) and _pid_looks_like_radtts_worker(prior_pid):
                LOG.warning("terminating prior RADTTS worker pid=%s before starting a new one", prior_pid)
                _terminate_pid(prior_pid)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        _write_current_pid()
        yield
    finally:
        try:
            lock_file.seek(0)
            lock_file.truncate()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_file.close()


class WorkerClient:
    HEARTBEAT_INTERVAL_SECONDS = 10.0

    def __init__(
        self,
        *,
        server_url: str,
        config_path: Path,
        worker_name: str,
        invite_token: str | None,
        poll_seconds: int,
    ):
        self.server_url = server_url.rstrip("/")
        self.config_path = config_path
        self.worker_name = worker_name
        self.invite_token = invite_token
        self.poll_seconds = poll_seconds

        self.worker_id: str | None = None
        self.api_key: str | None = None

        self.session = requests.Session()
        self.tts_service = TTSService()
        self.caption_service = CaptionService()
        self.quality_service = QualityService()
        self.generation_timeout_seconds = max(
            30,
            int(os.environ.get("RADTTS_WORKER_GENERATION_TIMEOUT_SECONDS", DEFAULT_WORKER_GENERATION_TIMEOUT_SECONDS)),
        )

    def _generation_timeout_for_request(
        self,
        req: WorkerSynthesisEnqueueRequest,
        *,
        reference_duration_seconds: float | None = None,
    ) -> float:
        voice_source = str(getattr(req.voice_source, "value", req.voice_source) or "").strip().lower()
        minimum_seconds = self.generation_timeout_seconds
        if (
            voice_source == "reference"
            and "1.7b" in str(req.model_id).lower()
            and int(req.max_new_tokens) >= 1200
        ):
            minimum_seconds = max(
                minimum_seconds,
                int(os.environ.get("RADTTS_HEAVY_REFERENCE_GENERATION_TIMEOUT_SECONDS", DEFAULT_HEAVY_REFERENCE_GENERATION_TIMEOUT_SECONDS)),
            )

        if minimum_seconds < 1:
            return minimum_seconds
        return max(
            minimum_seconds,
            recommended_generation_timeout_seconds(
                req.text,
                chunk_mode=req.chunk_mode,
                max_new_tokens=req.max_new_tokens,
                minimum_seconds=minimum_seconds,
                voice_source=req.voice_source,
                reference_duration_seconds=reference_duration_seconds,
            ),
        )

    def _post_json(self, path: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
        url = f"{self.server_url}{path}"
        response = self.session.post(url, json=payload, timeout=timeout)
        if response.status_code >= 400:
            raise RuntimeError(f"{response.status_code} {url} -> {response.text[:400]}")
        if not response.content:
            return {}
        return response.json()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            return
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.worker_id = payload.get("worker_id")
        self.api_key = payload.get("api_key")

    def _save_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "server_url": self.server_url,
            "worker_id": self.worker_id,
            "api_key": self.api_key,
            "worker_name": self.worker_name,
        }
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def ensure_registered(self) -> None:
        self._load_config()
        if self.worker_id and self.api_key and not self.invite_token:
            LOG.info("reusing worker credentials worker_id=%s", self.worker_id)
            return

        if not self.invite_token:
            raise RuntimeError(
                "Worker is not registered. Provide --invite-token or reuse an existing config file."
            )

        response = self._post_json(
            "/workers/register",
            {
                "invite_token": self.invite_token,
                "worker_name": self.worker_name,
                "capabilities": ["synthesize"],
            },
        )
        self.worker_id = response["worker_id"]
        self.api_key = response["api_key"]
        self._save_config()
        LOG.info("registered worker worker_id=%s name=%s", self.worker_id, self.worker_name)

    def run(self, *, once: bool = False) -> None:
        self.ensure_registered()
        assert self.worker_id and self.api_key
        LOG.info(
            "worker loop starting worker_id=%s server=%s poll_seconds=%s generation_timeout_seconds=%s",
            self.worker_id,
            self.server_url,
            self.poll_seconds,
            self.generation_timeout_seconds,
        )
        idle_polls = 0

        while True:
            pull_response = self._post_json(
                "/workers/pull",
                {"worker_id": self.worker_id, "api_key": self.api_key},
                timeout=180,
            )
            job = pull_response.get("job")
            if not job:
                idle_polls += 1
                if idle_polls == 1 or idle_polls % 12 == 0:
                    LOG.info("no job available; continuing to poll")
                if once:
                    return
                time.sleep(self.poll_seconds)
                continue

            idle_polls = 0
            job_id = job["job_id"]
            payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
            LOG.info(
                "claimed job job_id=%s project_id=%s voice_source=%s model=%s speaker=%s max_new_tokens=%s chunk_mode=%s output_format=%s transcript=%s text_chars=%s has_reference_text=%s",
                job_id,
                job.get("project_id"),
                payload.get("voice_source"),
                payload.get("model_id"),
                payload.get("built_in_speaker"),
                payload.get("max_new_tokens"),
                payload.get("chunk_mode"),
                payload.get("output_format"),
                payload.get("generate_transcript"),
                len(str(payload.get("text") or "")),
                bool(str(payload.get("reference_text") or "").strip()),
            )
            try:
                complete_payload = self._process_synthesis_job(job_id, payload)
                complete_payload.update({"worker_id": self.worker_id, "api_key": self.api_key})
                self._post_json(
                    f"/workers/jobs/{job_id}/complete",
                    complete_payload,
                    timeout=1800,
                )
                LOG.info(
                    "completed job job_id=%s duration_seconds=%s stage_durations=%s",
                    job_id,
                    complete_payload.get("duration_seconds"),
                    complete_payload.get("stage_durations_seconds"),
                )
            except Exception as exc:  # noqa: BLE001
                error_text = str(exc).strip() or f"{exc.__class__.__name__}: {exc!r}"
                LOG.exception("job failed job_id=%s error=%s", job_id, error_text)
                self._post_json(
                    f"/workers/jobs/{job_id}/fail",
                    {
                        "worker_id": self.worker_id,
                        "api_key": self.api_key,
                        "error": error_text[:1800],
                    },
                )
            if once:
                return

    def _post_progress_update(
        self,
        job_id: str,
        *,
        progress: float,
        stage: str | None = None,
        detail: str | None = None,
    ) -> None:
        assert self.worker_id and self.api_key
        payload = {
            "worker_id": self.worker_id,
            "api_key": self.api_key,
            "progress": max(0.0, min(1.0, float(progress))),
        }
        if stage:
            payload["stage"] = stage
        if detail:
            payload["detail"] = detail
        try:
            self._post_json(f"/workers/jobs/{job_id}/progress", payload, timeout=60)
        except Exception:
            # Progress updates are best-effort; synthesis should continue even if they fail.
            return

    def _process_synthesis_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized_payload = dict(payload)
        if str(normalized_payload.get("voice_source") or "").lower() == "builtin":
            if normalized_payload.get("reference_audio_b64") is None:
                normalized_payload.pop("reference_audio_b64", None)
            if normalized_payload.get("reference_audio_filename") is None:
                normalized_payload.pop("reference_audio_filename", None)
        req = WorkerSynthesisEnqueueRequest(**normalized_payload)
        with tempfile.TemporaryDirectory(prefix="radtts_worker_") as tmp:
            tmp_path = Path(tmp)
            reference_path = None
            reference_duration_seconds = None
            if req.voice_source == "reference":
                reference_path = tmp_path / req.reference_audio_filename
                reference_path.write_bytes(base64.b64decode(req.reference_audio_b64.encode("utf-8")))
                try:
                    reference_duration_seconds = round(probe_duration_seconds(reference_path), 3)
                except Exception:
                    reference_duration_seconds = None
            generation_timeout_seconds = self._generation_timeout_for_request(
                req,
                reference_duration_seconds=reference_duration_seconds,
            )
            estimated_chunks = estimated_chunk_count(req.text, req.chunk_mode, voice_source=req.voice_source)
            LOG.info(
                "starting synthesis job_id=%s reference_audio=%s reference_seconds=%s reference_text_chars=%s built_in_speaker=%s estimated_chunks=%s generation_timeout_seconds=%s",
                job_id,
                req.reference_audio_filename,
                reference_duration_seconds,
                len(str(req.reference_text or "")),
                req.built_in_speaker,
                estimated_chunks,
                generation_timeout_seconds,
            )
            stage_durations_seconds: dict[str, float] = {}
            progress_state = {
                "progress": 0.18,
                "stage": "worker_running",
                "detail": None,
            }
            progress_lock = threading.Lock()
            stop_heartbeat = threading.Event()

            def emit_progress(progress: float, *, stage: str | None = None, detail: str | None = None) -> None:
                with progress_lock:
                    progress_state["progress"] = max(0.0, min(1.0, float(progress)))
                    progress_state["stage"] = stage or progress_state["stage"]
                    progress_state["detail"] = detail
                self._post_progress_update(job_id, progress=progress, stage=stage, detail=detail)

            def heartbeat_worker() -> None:
                while not stop_heartbeat.wait(self.HEARTBEAT_INTERVAL_SECONDS):
                    with progress_lock:
                        progress = float(progress_state["progress"])
                        stage = str(progress_state["stage"] or "worker_running")
                    self._post_progress_update(
                        job_id,
                        progress=progress,
                        stage=stage,
                        detail=f"heartbeat: stage={stage}",
                    )

            heartbeat_thread = threading.Thread(target=heartbeat_worker, name="radtts-worker-heartbeat", daemon=True)
            heartbeat_thread.start()
            try:
                emit_progress(0.28, stage="model_load", detail="Loading voice model...")
                model_load_started_at = time.monotonic()
                _, runtime_summary = self.tts_service.load_model_with_runtime(req.model_id)
                stage_durations_seconds["model_load"] = round(time.monotonic() - model_load_started_at, 3)
                LOG.info("model loaded job_id=%s %s", job_id, runtime_summary)
                emit_progress(0.30, stage="model_load", detail=runtime_summary)
                synth_started_at = time.monotonic()
                stitching_started_at: float | None = None

                def on_tts_progress(message: str) -> None:
                    nonlocal stitching_started_at
                    cleaned = str(message or "").strip()
                    lower = cleaned.lower()
                    chunk_match = _GENERATION_CHUNK_RE.match(cleaned)

                    if lower == "reference transcription started":
                        emit_progress(0.33, stage="generation", detail=cleaned)
                        return

                    if lower == "reference transcription complete":
                        emit_progress(0.36, stage="generation", detail=cleaned)
                        return

                    if lower == "preparing reference audio":
                        emit_progress(0.31, stage="generation", detail=cleaned)
                        return

                    if lower == "reference sample check complete" or lower.startswith("reference validation warning:"):
                        emit_progress(0.32, stage="generation", detail=cleaned)
                        return

                    if chunk_match:
                        progress = generation_progress_for_chunk(
                            completed_chunks=int(chunk_match.group(1)),
                            total_chunks=int(chunk_match.group(2)),
                        )
                        emit_progress(progress, stage="generation", detail=cleaned)
                        return

                    if lower.startswith("stitching"):
                        if stitching_started_at is None:
                            stitching_started_at = time.monotonic()
                            stage_durations_seconds["generation"] = round(stitching_started_at - synth_started_at, 3)
                        progress = stitching_progress_for_output(
                            req.output_format,
                            encoding_started=(lower == "stitching encoding mp3"),
                        )
                        emit_progress(progress, stage="stitching", detail=cleaned)

                synth_req = SynthesisRequest(
                    project_id=req.project_id,
                    text=req.text,
                    voice_source=req.voice_source,
                    reference_audio_path=reference_path,
                    reference_text=req.reference_text,
                    model_id=req.model_id,
                    built_in_speaker=req.built_in_speaker,
                    built_in_instruct=req.built_in_instruct,
                    max_new_tokens=req.max_new_tokens,
                    chunk_mode=req.chunk_mode,
                    pause_config=req.pause_config,
                    output_format=req.output_format,
                    output_name=req.output_name,
                    voice_clone_authorized=True,
                )
                output_path, pause_seconds, reference_text = run_with_retry_timeout(
                    stage_name="worker_generation",
                    fn=lambda: self.tts_service.synthesize(
                        synth_req,
                        output_dir=tmp_path,
                        on_progress=on_tts_progress,
                    ),
                    timeout_seconds=generation_timeout_seconds,
                    retries=0,
                    on_log=lambda message: LOG.info("job_id=%s %s", job_id, message),
                )
                synth_finished_at = time.monotonic()

                if stitching_started_at is None:
                    stage_durations_seconds["generation"] = round(synth_finished_at - synth_started_at, 3)
                else:
                    stage_durations_seconds["stitching"] = round(synth_finished_at - stitching_started_at, 3)

                duration = probe_duration_seconds(output_path)

                captions_txt = None
                captions_srt = None
                captions_vtt = None
                if req.generate_transcript:
                    caption_started_at = time.monotonic()
                    emit_progress(CAPTIONING_PROGRESS_START, stage="captioning", detail="captioning started")
                    try:
                        caption_artifacts = self.caption_service.generate(
                            audio_path=output_path,
                            output_dir=tmp_path,
                            name=f"{req.output_name}_worker",
                            language=None,
                        )
                        captions_txt = caption_artifacts.txt_path.read_text(encoding="utf-8")
                        captions_srt = caption_artifacts.srt_path.read_text(encoding="utf-8")
                        captions_vtt = caption_artifacts.vtt_path.read_text(encoding="utf-8")
                        stage_durations_seconds["captioning"] = round(time.monotonic() - caption_started_at, 3)
                        emit_progress(0.95, stage="captioning", detail="captioning complete")
                    except Exception:  # noqa: BLE001
                        pass

                quality = self.quality_service.evaluate(
                    text=req.text,
                    duration_seconds=duration,
                    pause_seconds=pause_seconds,
                )
                final_stage = "captioning" if req.generate_transcript else "stitching"
                emit_progress(UPLOAD_PROGRESS, stage=final_stage, detail="uploading completed audio")

                return {
                    "output_audio_b64": base64.b64encode(output_path.read_bytes()).decode("utf-8"),
                    "output_format": req.output_format.value,
                    "duration_seconds": duration,
                    "reference_text": reference_text,
                    "pause_seconds": pause_seconds,
                    "captions_txt": captions_txt,
                    "captions_srt": captions_srt,
                    "captions_vtt": captions_vtt,
                    "quality": quality.model_dump(mode="json"),
                    "stage_durations_seconds": stage_durations_seconds,
                }
            finally:
                stop_heartbeat.set()
                heartbeat_thread.join(timeout=1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RADTTS distributed worker")
    parser.add_argument("--server-url", required=True, help="RADTTS server base URL")
    parser.add_argument("--invite-token", help="Invite token from /workers/invite")
    parser.add_argument("--worker-name", default=socket.gethostname())
    parser.add_argument(
        "--config-path",
        default=str(Path.home() / ".radtts" / "worker.json"),
        help="Path for worker credentials cache",
    )
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--once", action="store_true", help="Process at most one pull cycle")
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    args = build_parser().parse_args()
    config_path = Path(args.config_path)
    with _worker_single_instance(config_path):
        client = WorkerClient(
            server_url=args.server_url,
            config_path=config_path,
            worker_name=args.worker_name,
            invite_token=args.invite_token,
            poll_seconds=max(1, args.poll_seconds),
        )
        client.run(once=args.once)


if __name__ == "__main__":
    main()
