from __future__ import annotations

from pathlib import Path
import time

import numpy as np
import pytest

from radtts.constants import SUPPORTED_BASE_MODELS, SUPPORTED_CUSTOM_MODELS
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
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float16 cache=fresh"),
    )

    def fake_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req.output_name}.mp3"
        output_path.write_bytes(b"ID3")
        assert on_progress is not None
        for message in [
            "preparing reference audio",
            "reference sample check complete",
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
        "model_load",
        "generation",
        "generation",
        "generation",
        "generation",
        "stitching",
        "stitching",
        "captioning",
        "captioning",
        "captioning",
    ]
    assert [detail for _, _, _, detail in progress_calls] == [
        "Loading voice model...",
        f"tts model={SUPPORTED_BASE_MODELS[0]} runtime device=mps:0 dtype=torch.float16 cache=fresh",
        "preparing reference audio",
        "reference sample check complete",
        "generation chunk 1/2",
        "generation chunk 2/2",
        "stitching chunks",
        "stitching encoding mp3",
        "captioning started",
        "captioning complete",
        "uploading completed audio",
    ]
    assert [progress for _, progress, _, _ in progress_calls] == pytest.approx(
        [0.28, 0.30, 0.31, 0.32, 0.535, 0.72, 0.78, 0.84, 0.85, 0.95, 0.97],
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
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 80.64)

    def slow_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        time.sleep(0.2)
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        return output_path, [], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", slow_synthesize)

    client.run(once=True)

    fail_calls = [payload for path, payload in calls if path.endswith("/fail")]
    assert len(fail_calls) == 1
    error_text = str(fail_calls[0]["error"])
    assert "Reference-voice generation timed out on the local helper" in error_text
    assert "about 81s long" in error_text
    assert "6 to 15 second sample" in error_text
    assert "Normal quality first" in error_text


def test_worker_client_reloads_updated_credentials_after_invalid_worker_error(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "worker.json"
    config_path.write_text(
        '{"server_url": "http://example.test", "worker_id": "worker-old", "api_key": "api-old", "worker_name": "test-worker"}',
        encoding="utf-8",
    )
    client = WorkerClient(
        server_url="http://example.test",
        config_path=config_path,
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )

    pull_attempts: list[tuple[str | None, str | None]] = []

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        if path == "/workers/pull":
            pull_attempts.append((str(payload.get("worker_id")), str(payload.get("api_key"))))
            if len(pull_attempts) == 1:
                config_path.write_text(
                    '{"server_url": "http://example.test", "worker_id": "worker-new", "api_key": "api-new", "worker_name": "test-worker"}',
                    encoding="utf-8",
                )
                raise RuntimeError("403 http://example.test/workers/pull -> {\"detail\":\"invalid worker credentials\"}")
            return {}
        return {}

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    client.run(once=True)

    assert pull_attempts == [("worker-old", "api-old"), ("worker-new", "api-new")]
    assert client.worker_id == "worker-new"
    assert client.api_key == "api-new"


def test_worker_client_handles_stale_credentials_without_crashing_once(tmp_path: Path, monkeypatch, caplog):
    config_path = tmp_path / "worker.json"
    config_path.write_text(
        '{"server_url": "http://example.test", "worker_id": "worker-stale", "api_key": "api-stale", "worker_name": "test-worker"}',
        encoding="utf-8",
    )
    client = WorkerClient(
        server_url="http://example.test",
        config_path=config_path,
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )

    monkeypatch.setattr(
        client,
        "_post_json",
        lambda path, payload, timeout=120: (_ for _ in ()).throw(
            RuntimeError("403 http://example.test/workers/pull -> {\"detail\":\"invalid worker credentials\"}")
        )
        if path == "/workers/pull"
        else {},
    )

    client.run(once=True)

    assert "run helper setup from this environment" in caplog.text.lower()


def test_worker_client_extends_generation_timeout_for_long_scripts(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"
    client.generation_timeout_seconds = 600

    captured_timeout: dict[str, float] = {}

    monkeypatch.setattr(client, "_post_json", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32"),
    )
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 8.4)
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.2, "max": 0.6, "mean": 0.4, "stddev": 0.1},
            warnings=[],
        ),
    )

    def fake_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        return output_path, [], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", fake_synthesize)

    def fake_run_with_retry_timeout(*, stage_name, fn, timeout_seconds, retries, on_log):
        captured_timeout["value"] = float(timeout_seconds)
        return fn()

    monkeypatch.setattr("radtts.worker_client.run_with_retry_timeout", fake_run_with_retry_timeout)

    payload = WorkerSynthesisEnqueueRequest(
        project_id="proj-worker",
        text=" ".join([f"Sentence {idx}." for idx in range(1, 41)]),
        voice_source="builtin",
        model_id=SUPPORTED_CUSTOM_MODELS[0],
        built_in_speaker="Vivian",
        max_new_tokens=1400,
        chunk_mode="sentence",
        pause_config=PauseConfig(seed=1),
        output_format=OutputFormat.WAV,
        output_name="worker-long-timeout",
        generate_transcript=False,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    client._process_synthesis_job("job-worker-long", payload)

    assert captured_timeout["value"] > 600


def test_worker_client_uses_larger_timeout_floor_for_heavy_reference_model(tmp_path: Path):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.generation_timeout_seconds = 600

    payload = WorkerSynthesisEnqueueRequest(
        project_id="proj-worker",
        text=" ".join([f"Sentence {idx} has several words for a longer reference synthesis run." for idx in range(1, 15)]),
        reference_audio_b64="QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
        reference_audio_filename="reference.wav",
        reference_text="hello",
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        max_new_tokens=1400,
        chunk_mode="sentence",
        pause_config=PauseConfig(seed=1),
        output_format=OutputFormat.WAV,
        output_name="worker-heavy-reference-timeout",
        generate_transcript=False,
        voice_clone_authorized=True,
    )

    timeout = client._generation_timeout_for_request(payload, reference_duration_seconds=6.8)

    assert timeout >= 1800


def test_worker_client_switches_heavy_reference_jobs_into_helper_batches(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"

    progress_calls: list[tuple[float, str | None, str | None]] = []
    timeout_stage_names: list[str] = []

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        if path.endswith("/progress"):
            progress_calls.append((float(payload["progress"]), payload.get("stage"), payload.get("detail")))
        return {}

    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 10.0)
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32 cache=warm"),
    )
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.3, "max": 0.4, "mean": 0.35, "stddev": 0.05},
            warnings=[],
        ),
    )

    def fake_run_with_retry_timeout(*, stage_name, fn, timeout_seconds, retries, on_log):
        timeout_stage_names.append(stage_name)
        return fn()

    monkeypatch.setattr("radtts.worker_client.run_with_retry_timeout", fake_run_with_retry_timeout)

    def fake_synthesize(
        req,
        output_dir,
        *,
        on_progress=None,
        cancel_check=None,
        chunk_texts=None,
        progress_label="chunk",
        chunk_runner=None,
    ):
        assert progress_label == "batch"
        assert chunk_texts is not None
        assert len(chunk_texts) > 1
        assert chunk_runner is not None
        assert on_progress is not None
        total = len(chunk_texts)
        for idx, chunk in enumerate(chunk_texts, start=1):
            chunk_runner(lambda: (np.ones(32, dtype=np.float32), 24000), chunk, idx, total)
            on_progress(f"generation batch {idx}/{total}")
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        return output_path, [], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", fake_synthesize)

    payload = WorkerSynthesisEnqueueRequest(
        project_id="proj-worker",
        text=" ".join(
            f"Sentence {idx} has several words to keep the helper batching path active."
            for idx in range(1, 15)
        ),
        reference_audio_b64="QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
        reference_audio_filename="reference.wav",
        reference_text="hello",
        model_id=SUPPORTED_BASE_MODELS[0],
        max_new_tokens=1200,
        chunk_mode="sentence",
        pause_config=PauseConfig(seed=1),
        output_format=OutputFormat.WAV,
        output_name="worker-batched-reference",
        generate_transcript=False,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    client._process_synthesis_job("job-worker-batched-reference", payload)

    assert any(
        stage == "generation" and detail and detail.startswith("Planning long-run helper batches")
        for _, stage, detail in progress_calls
    )
    assert any(
        stage == "generation" and detail and detail.startswith("generation batch ")
        for _, stage, detail in progress_calls
    )
    assert timeout_stage_names
    assert all(name.startswith("worker_generation_batch_") for name in timeout_stage_names)


def test_worker_client_emits_reference_validation_warning_progress(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"

    progress_calls: list[tuple[float, str | None, str | None]] = []

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        if path.endswith("/progress"):
            progress_calls.append((float(payload["progress"]), payload.get("stage"), payload.get("detail")))
        return {}

    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 9.0)
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32 cache=warm"),
    )
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.3, "max": 0.4, "mean": 0.35, "stddev": 0.05},
            warnings=[],
        ),
    )

    def fake_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        assert on_progress is not None
        on_progress("preparing reference audio")
        on_progress("reference validation warning: Reference sample sounds quiet; voice matching may be weaker.")
        on_progress("generation chunk 1/1")
        return output_path, [0.3], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", fake_synthesize)

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
        output_name="worker-reference-warning",
        generate_transcript=False,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    client._process_synthesis_job("job-worker-reference-warning", payload)

    assert (0.31, "generation", "preparing reference audio") in progress_calls
    assert any(
        stage == "generation" and detail and detail.startswith("reference validation warning:")
        for _, stage, detail in progress_calls
    )


def test_worker_client_accepts_builtin_payload_with_null_reference_fields(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"

    monkeypatch.setattr(client, "_post_json", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32"),
    )
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 1.2)
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.0, "max": 0.0, "mean": 0.0, "stddev": 0.0},
            warnings=[],
        ),
    )

    def fake_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        assert req.voice_source.value == "builtin"
        assert req.built_in_speaker == "Vivian"
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        return output_path, [], ""

    monkeypatch.setattr(client.tts_service, "synthesize", fake_synthesize)

    payload = {
        "project_id": "proj-worker",
        "text": "Hello built in voice.",
        "voice_source": "builtin",
        "reference_audio_b64": None,
        "reference_audio_filename": None,
        "model_id": SUPPORTED_CUSTOM_MODELS[0],
        "built_in_speaker": "Vivian",
        "max_new_tokens": 400,
        "chunk_mode": "single",
        "pause_config": PauseConfig(seed=1).model_dump(mode="json"),
        "output_format": "wav",
        "output_name": "worker-builtin",
        "generate_transcript": False,
        "voice_clone_authorized": True,
    }

    result = client._process_synthesis_job("job-builtin", payload)

    assert result["output_format"] == "wav"
    assert result["reference_text"] == ""


def test_worker_client_emits_reference_transcription_progress(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"

    progress_calls: list[tuple[float, str | None, str | None]] = []

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        if path.endswith("/progress"):
            progress_calls.append((float(payload["progress"]), payload.get("stage"), payload.get("detail")))
        return {}

    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 4.2)
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32"),
    )
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.3, "max": 0.4, "mean": 0.35, "stddev": 0.05},
            warnings=[],
        ),
    )

    def fake_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        assert on_progress is not None
        on_progress("reference transcription started")
        on_progress("reference transcription complete")
        on_progress("generation chunk 1/1")
        return output_path, [0.3], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", fake_synthesize)

    payload = WorkerSynthesisEnqueueRequest(
        project_id="proj-worker",
        text="One sentence.",
        reference_audio_b64="QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
        reference_audio_filename="reference.wav",
        reference_text="",
        model_id=SUPPORTED_BASE_MODELS[0],
        max_new_tokens=400,
        chunk_mode="single",
        pause_config=PauseConfig(seed=1),
        output_format=OutputFormat.WAV,
        output_name="worker-transcription-progress",
        generate_transcript=False,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    client._process_synthesis_job("job-worker-transcription", payload)

    assert (0.33, "generation", "reference transcription started") in progress_calls
    assert (0.36, "generation", "reference transcription complete") in progress_calls


def test_worker_client_emits_explicit_heartbeat_during_long_generation(tmp_path: Path, monkeypatch):
    client = WorkerClient(
        server_url="http://example.test",
        config_path=tmp_path / "worker.json",
        worker_name="test-worker",
        invite_token=None,
        poll_seconds=5,
    )
    client.worker_id = "worker-1"
    client.api_key = "api-key"
    monkeypatch.setattr(client, "HEARTBEAT_INTERVAL_SECONDS", 0.01, raising=False)

    progress_calls: list[tuple[float, str | None, str | None]] = []

    def fake_post_json(path: str, payload: dict[str, object], timeout: int = 120):
        if path.endswith("/progress"):
            progress_calls.append((float(payload["progress"]), payload.get("stage"), payload.get("detail")))
        return {}

    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr("radtts.worker_client.probe_duration_seconds", lambda path: 4.2)
    monkeypatch.setattr(
        client.tts_service,
        "load_model_with_runtime",
        lambda model_id: (object(), f"tts model={model_id} runtime device=mps:0 dtype=torch.float32"),
    )
    monkeypatch.setattr(
        client.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.3, "max": 0.4, "mean": 0.35, "stddev": 0.05},
            warnings=[],
        ),
    )

    def slow_synthesize(req, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req.output_name}.wav"
        output_path.write_bytes(b"RIFF")
        assert on_progress is not None
        on_progress("preparing reference audio")
        time.sleep(0.04)
        on_progress("generation chunk 1/1")
        return output_path, [], "reference text"

    monkeypatch.setattr(client.tts_service, "synthesize", slow_synthesize)

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
        output_name="worker-heartbeat",
        generate_transcript=False,
        voice_clone_authorized=True,
    ).model_dump(mode="json")

    client._process_synthesis_job("job-worker-heartbeat", payload)

    assert any(
        stage == "generation" and detail == "heartbeat: stage=generation"
        for _, stage, detail in progress_calls
    )
