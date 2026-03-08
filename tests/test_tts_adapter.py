from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from radtts.exceptions import ValidationError
from radtts.services.tts import TTSService


def test_build_clone_kwargs_supports_ref_audio_key():
    def fake_generate(text: str, ref_audio: str, ref_text: str, max_new_tokens: int):  # noqa: ANN001
        return text, ref_audio, ref_text, max_new_tokens

    kwargs = TTSService._build_clone_kwargs(
        fn=fake_generate,
        text="hello",
        reference_audio_path=Path("/tmp/ref.wav"),
        reference_text="ref text",
        max_new_tokens=321,
    )

    assert kwargs["text"] == "hello"
    assert kwargs["ref_audio"] == "/tmp/ref.wav"
    assert kwargs["ref_text"] == "ref text"
    assert kwargs["max_new_tokens"] == 321


def test_build_builtin_kwargs_supports_speaker_and_instruct():
    def fake_generate(text: str, speaker: str, instruct: str, max_new_tokens: int):  # noqa: ANN001
        return text, speaker, instruct, max_new_tokens

    kwargs = TTSService._build_builtin_kwargs(
        fn=fake_generate,
        text="hello",
        speaker="vivian",
        instruct="Warm and clear",
        max_new_tokens=222,
    )

    assert kwargs["text"] == "hello"
    assert kwargs["speaker"] == "vivian"
    assert kwargs["instruct"] == "Warm and clear"
    assert kwargs["max_new_tokens"] == 222


def test_parse_generation_result_handles_single_item_audio_list():
    result = ([np.array([0.1, -0.2, 0.3], dtype=np.float32)], 24000)
    model = type("DummyModel", (), {"sample_rate": 16000})()

    audio, sample_rate = TTSService._parse_generation_result(result, model)

    assert sample_rate == 24000
    assert audio.shape == (3,)
    assert np.allclose(audio, np.array([0.1, -0.2, 0.3], dtype=np.float32))


def test_model_load_kwargs_prefers_mps_when_available(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RADTTS_TTS_DEVICE", raising=False)
    monkeypatch.delenv("RADTTS_TTS_DTYPE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)

    kwargs = TTSService.model_load_kwargs()

    assert kwargs["device_map"] == "mps"
    assert kwargs["dtype"] == torch.float32


def test_model_load_kwargs_respects_env_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RADTTS_TTS_DEVICE", "cpu")
    monkeypatch.setenv("RADTTS_TTS_DTYPE", "float32")

    kwargs = TTSService.model_load_kwargs()

    assert kwargs["device_map"] == "cpu"
    assert kwargs["dtype"] == torch.float32


def test_prepare_reference_audio_path_converts_non_wav(monkeypatch: pytest.MonkeyPatch):
    service = TTSService()
    converted: list[tuple[Path, Path]] = []

    def fake_convert(input_path: Path, output_path: Path) -> Path:
        converted.append((input_path, output_path))
        output_path.write_bytes(b"RIFF")
        return output_path

    monkeypatch.setattr("radtts.services.tts.convert_audio", fake_convert)

    import contextlib

    with contextlib.ExitStack() as stack:
        normalized = service._prepare_reference_audio_path(Path("/tmp/ref.webm"), stack=stack)

    assert normalized.suffix == ".wav"
    assert converted == [(Path("/tmp/ref.webm"), normalized)]


def test_auto_reference_text_rejects_too_short_audio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    service = TTSService()
    audio_path = tmp_path / "tiny.wav"
    audio_path.write_bytes(b"RIFF")

    monkeypatch.setattr("radtts.services.tts.probe_duration_seconds", lambda path: 1.2)

    with pytest.raises(ValidationError, match="Reference sample is too short"):
        service._auto_reference_text(audio_path)


def test_auto_reference_text_rejects_empty_transcript(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    service = TTSService()
    audio_path = tmp_path / "ref.wav"
    audio_path.write_bytes(b"RIFF")

    class DummyArtifacts:
        def __init__(self, txt_path: Path):
            self.txt_path = txt_path

    def fake_transcribe(audio_path, output_dir, *, name, language=None, beam_size=5):  # noqa: ANN001
        txt_path = output_dir / f"{name}.txt"
        txt_path.write_text("hi", encoding="utf-8")
        return DummyArtifacts(txt_path), []

    monkeypatch.setattr("radtts.services.tts.probe_duration_seconds", lambda path: 4.0)
    monkeypatch.setattr(service._asr_service, "transcribe", fake_transcribe)

    with pytest.raises(ValidationError, match="too short or unclear"):
        service._auto_reference_text(audio_path)
