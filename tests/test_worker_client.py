from __future__ import annotations

from pathlib import Path
import time

import pytest

from radtts.constants import SUPPORTED_BASE_MODELS
from radtts.models import CaptionArtifacts, OutputFormat, PauseConfig, QualityReport, WorkerSynthesisEnqueueRequest
from radtts.worker_client import WorkerClient


def test_worker_client_emits_progress_updates(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"

    progress_calls: list[tuple[str, float, str | None, str | None]] = []

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        if path.endswith("/progress"):
            progress_calls.append((path, float(payload["progress"]), payload.get("stage"), payload.get("detail")))
        return {}

    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 4.2)
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.3, "max": 0.4, "mean": 0.35, "stddev": 0.05},
            warnings=[],
        ),
    )
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float16"),
    )

    def fake_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req.output_name}.mp3"
        output_path.write_bytes(b"ID3")
        assert on_progress is not None
        for message in [
            "generation chunk 1/2",
            "generation chunk 2/2",
            "stitching chunks",
            "stitching encoding mp3",
        ]:
            on_progress(message)
        return output_path, [0.3], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", fake_synthesize)

    def fake_caption_generate(audio_path, output_dir, name, language=None):
        txt_path = output_dir / f"{name}.txt"
        srt_path = output_dir / f"{name}.srt"
        vtt_path = output_dir / f"{name}.vtt"
        txt_path.write_text("hello", encoding="utf-8")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
        vtt_path.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello\n", encoding="utf-8")
        return CaptionArtifacts(txt_path=txt_path, srt_path=srt_path, vtt_path=vtt_path)

    monkeypatch.setattr(client.caption_service, "generate", fake_caption_generate)

    payload = WorkerSynthesisEnqueueRequest(
        project_id="proj-worker",
        text="One. Two.",
        reference_audio_b64="QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
        reference_audio_filename="reference.wav",
        reference_text="hello",
        model_id=SUPPORTED_BASE_MODELS[0],
        max_new_tokens=400,
        chunk_mode="sentence",
        pause_config=PauseConfig(seed=1),
        output_format=OutputFormat.MP3,
        output_name="worker-progress",
        generate_transcript=True,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    result = client._process_synthesis_job("job-worker", payload)

    assert [stage for _, _, stage, _ in progress_calls] == [
        "model_load",
        "generation",
        "generation",
        "stitching",
        "stitching",
        "captioning",
        "captioning",
        "captioning",
    ]
    assert [detail for _, _, _, detail in progress_calls] == [
        f"tts model={SUPPORTED_BASE_MODELS[0]} runtime device=mps:0 dtype=torch.float16",
        "generation chunk 1/2",
        "generation chunk 2/2",
        "stitching chunks",
        "stitching encoding mp3",
        "captioning started",
        "captioning complete",
        "uploading completed audio",
    ]
    assert [progress for _, progress, _, _ in progress_calls] == pytest.approx(
        [0.30, 0.535, 0.72, 0.78, 0.84, 0.85, 0.95, 0.97],
        rel=0,
        abs=1e-4,
    )
    assert result["stage_durations_seconds"]["model_load"] >= 0
    assert result["stage_durations_seconds"]["generation"] >= 0
    assert result["stage_durations_seconds"]["stitching"] >= 0
    assert result["stage_durations_seconds"]["captioning"] >= 0


def test_worker_client_times_out_generation_and_reports_failure(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"
    client.generation_timeout_seconds = 0.05

    calls: list[tuple[str, dict[str, object]]] = []

    payload = WorkerSynthesisEnqueueRequest(
        project_id="proj-worker",
        text="One sentence.",
        reference_audio_b64="QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
        reference_audio_filename="reference.wav",
        reference_text="hello",
        model_id=SUPPORTED_BASE_MODELS[0],
        max_new_tokens=400,
        chunk_mode="single",
        pause_config=PauseConfig(seed=1),
        output_format=OutputFormat.WAV,
        output_name="worker-timeout",
        generate_transcript=False,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        calls.append((path, payload))
        if path == "/workers/pull":
            return {
                "job": {
                    "job_id": "job-timeout",
                    "project_id": "proj-worker",
                    "payload": payload_data,
                }
            }
        return {}

    payload_data = payload
    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32"),
    )

    def slow_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        time.sleep(0.2)
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        return output_path, [], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", slow_synthesize)

    client.run(once=True)

    fail_calls = [payload for path, payload in calls if path.endswith("/fail")]
    assert len(fail_calls) == 1
    assert "timed out" in str(fail_calls[0]["error"])
