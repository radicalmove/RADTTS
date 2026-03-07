"""Worker daemon for distributed RADTTS synthesis jobs."""

from __future__ import annotations

import argparse
import base64
import json
import re
import socket
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

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

_GENERATION_CHUNK_RE = re.compile(r"^generation chunk (\d+)/(\d+)$", re.IGNORECASE)


class WorkerClient:
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

    def run(self, *, once: bool = False) -> None:
        self.ensure_registered()
        assert self.worker_id and self.api_key

        while True:
            pull_response = self._post_json(
                "/workers/pull",
                {"worker_id": self.worker_id, "api_key": self.api_key},
                timeout=180,
            )
            job = pull_response.get("job")
            if not job:
                if once:
                    return
                time.sleep(self.poll_seconds)
                continue

            job_id = job["job_id"]
            try:
                complete_payload = self._process_synthesis_job(job_id, job["payload"])
                complete_payload.update({"worker_id": self.worker_id, "api_key": self.api_key})
                self._post_json(
                    f"/workers/jobs/{job_id}/complete",
                    complete_payload,
                    timeout=1800,
                )
            except Exception as exc:  # noqa: BLE001
                self._post_json(
                    f"/workers/jobs/{job_id}/fail",
                    {
                        "worker_id": self.worker_id,
                        "api_key": self.api_key,
                        "error": str(exc)[:1800],
                    },
                )
            if once:
                return

    def _post_progress_update(
        self,
        job_id: str,
        *,
        progress: float,
        detail: str | None = None,
    ) -> None:
        assert self.worker_id and self.api_key
        payload = {
            "worker_id": self.worker_id,
            "api_key": self.api_key,
            "progress": max(0.0, min(1.0, float(progress))),
        }
        if detail:
            payload["detail"] = detail
        try:
            self._post_json(f"/workers/jobs/{job_id}/progress", payload, timeout=60)
        except Exception:
            # Progress updates are best-effort; synthesis should continue even if they fail.
            return

    def _process_synthesis_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = WorkerSynthesisEnqueueRequest(**payload)

        with tempfile.TemporaryDirectory(prefix="radtts_worker_") as tmp:
            tmp_path = Path(tmp)
            reference_path = tmp_path / req.reference_audio_filename
            reference_path.write_bytes(base64.b64decode(req.reference_audio_b64.encode("utf-8")))
            stage_durations_seconds: dict[str, float] = {}
            model_load_started_at = time.monotonic()
            _, runtime_summary = self.tts_service.load_model_with_runtime(req.model_id)
            stage_durations_seconds["model_load"] = round(time.monotonic() - model_load_started_at, 3)
            self._post_progress_update(job_id, progress=0.30, detail=runtime_summary)
            synth_started_at = time.monotonic()
            stitching_started_at: float | None = None

            def on_tts_progress(message: str) -> None:
                nonlocal stitching_started_at
                cleaned = str(message or "").strip()
                lower = cleaned.lower()
                chunk_match = _GENERATION_CHUNK_RE.match(cleaned)

                if chunk_match:
                    progress = generation_progress_for_chunk(
                        completed_chunks=int(chunk_match.group(1)),
                        total_chunks=int(chunk_match.group(2)),
                    )
                    self._post_progress_update(job_id, progress=progress, detail=cleaned)
                    return

                if lower.startswith("stitching"):
                    if stitching_started_at is None:
                        stitching_started_at = time.monotonic()
                        stage_durations_seconds["generation"] = round(stitching_started_at - synth_started_at, 3)
                    progress = stitching_progress_for_output(
                        req.output_format,
                        encoding_started=(lower == "stitching encoding mp3"),
                    )
                    self._post_progress_update(job_id, progress=progress, detail=cleaned)

            synth_req = SynthesisRequest(
                project_id=req.project_id,
                text=req.text,
                reference_audio_path=reference_path,
                reference_text=req.reference_text,
                model_id=req.model_id,
                max_new_tokens=req.max_new_tokens,
                chunk_mode=req.chunk_mode,
                pause_config=req.pause_config,
                output_format=req.output_format,
                output_name=req.output_name,
                voice_clone_authorized=True,
            )
            output_path, pause_seconds, reference_text = self.tts_service.synthesize(
                synth_req,
                output_dir=tmp_path,
                on_progress=on_tts_progress,
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
                self._post_progress_update(job_id, progress=CAPTIONING_PROGRESS_START, detail="captioning started")
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
                    self._post_progress_update(job_id, progress=0.95, detail="captioning complete")
                except Exception:  # noqa: BLE001
                    pass

            quality = self.quality_service.evaluate(
                text=req.text,
                duration_seconds=duration,
                pause_seconds=pause_seconds,
            )
            self._post_progress_update(job_id, progress=UPLOAD_PROGRESS, detail="uploading completed audio")

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
    args = build_parser().parse_args()
    client = WorkerClient(
        server_url=args.server_url,
        config_path=Path(args.config_path),
        worker_name=args.worker_name,
        invite_token=args.invite_token,
        poll_seconds=max(1, args.poll_seconds),
    )
    client.run(once=args.once)


if __name__ == "__main__":
    main()
