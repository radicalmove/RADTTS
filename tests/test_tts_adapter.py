from __future__ import annotations

from pathlib import Path

import numpy as np

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


def test_parse_generation_result_handles_single_item_audio_list():
    result = ([np.array([0.1, -0.2, 0.3], dtype=np.float32)], 24000)
    model = type("DummyModel", (), {"sample_rate": 16000})()

    audio, sample_rate = TTSService._parse_generation_result(result, model)

    assert sample_rate == 24000
    assert audio.shape == (3,)
    assert np.allclose(audio, np.array([0.1, -0.2, 0.3], dtype=np.float32))
