from __future__ import annotations

import pytest

from pydantic import ValidationError

from radtts.constants import SUPPORTED_BASE_MODELS
from radtts.models import (
    ChunkMode,
    OutputFormat,
    OutputMetadata,
    PauseConfig,
    QualityReport,
    SimpleSynthesisRequest,
    SynthesisRequest,
)
from radtts.services.tts import PausePlanner
from radtts.utils.text import (
    coalesce_sentence_chunks,
    estimated_chunk_count,
    recommended_generation_timeout_seconds,
    split_sentences,
)


def test_sentence_splitter_preserves_sentences():
    text = "In this lesson, we begin. Next, we compare models! Why does pacing matter?"
    chunks = split_sentences(text)
    assert chunks == [
        "In this lesson, we begin.",
        "Next, we compare models!",
        "Why does pacing matter?",
    ]


def test_pause_generation_bounds_and_seed_determinism():
    planner = PausePlanner()
    config = PauseConfig(min_seconds=0.4, max_seconds=0.85, seed=7)
    chunks = ["Short intro.", "This is a longer middle sentence for pacing control.", "Final line."]

    pauses_a = planner.build(chunks, config)
    pauses_b = planner.build(chunks, config)

    assert pauses_a == pauses_b
    assert len(pauses_a) == 2
    assert all(config.min_seconds <= value <= config.max_seconds for value in pauses_a)


def test_estimated_chunk_count_respects_chunk_mode():
    text = "One sentence. Two sentence. Three sentence."
    assert estimated_chunk_count(text, "sentence") == 3
    assert estimated_chunk_count(text, "single") == 1


def test_estimated_chunk_count_coalesces_reference_sentence_runs():
    text = "One short sentence. Two short sentence. Three short sentence. Four short sentence."

    regular = estimated_chunk_count(text, "sentence")
    reference = estimated_chunk_count(text, "sentence", voice_source="reference")

    assert regular == 4
    assert reference < regular


def test_coalesce_sentence_chunks_merges_short_neighbors():
    chunks = ["One short sentence.", "Two short sentence.", "This is a much longer sentence that should stand alone."]

    merged = coalesce_sentence_chunks(chunks, target_words=8, max_words=20, max_chars=80)

    assert merged[0] == "One short sentence. Two short sentence."
    assert merged[1] == "This is a much longer sentence that should stand alone."


def test_recommended_generation_timeout_scales_for_longer_scripts():
    short_timeout = recommended_generation_timeout_seconds(
        "Short example.",
        chunk_mode="sentence",
        max_new_tokens=400,
        minimum_seconds=600,
    )
    long_timeout = recommended_generation_timeout_seconds(
        " ".join([f"Sentence {idx}." for idx in range(1, 41)]),
        chunk_mode="sentence",
        max_new_tokens=1400,
        minimum_seconds=600,
    )
    assert short_timeout == 600
    assert long_timeout > short_timeout


def test_recommended_generation_timeout_penalizes_dense_sentence_chunks():
    spread_out_text = " ".join(
        " ".join([f"Word{idx}_{part}" for part in range(6)]) + "."
        for idx in range(10)
    )
    dense_text = " ".join(
        " ".join([f"Word{idx}_{part}" for part in range(20)]) + "."
        for idx in range(3)
    )

    spread_timeout = recommended_generation_timeout_seconds(
        spread_out_text,
        chunk_mode="sentence",
        max_new_tokens=1000,
        minimum_seconds=600,
    )
    dense_timeout = recommended_generation_timeout_seconds(
        dense_text,
        chunk_mode="sentence",
        max_new_tokens=1000,
        minimum_seconds=600,
    )

    assert dense_timeout > spread_timeout


def test_recommended_generation_timeout_penalizes_reference_voice_jobs():
    text = " ".join([f"Sentence {idx}." for idx in range(1, 16)])

    builtin_timeout = recommended_generation_timeout_seconds(
        text,
        chunk_mode="sentence",
        max_new_tokens=1000,
        minimum_seconds=600,
        voice_source="builtin",
    )
    reference_timeout = recommended_generation_timeout_seconds(
        text,
        chunk_mode="sentence",
        max_new_tokens=1000,
        minimum_seconds=600,
        voice_source="reference",
        reference_duration_seconds=12.0,
    )

    assert reference_timeout > builtin_timeout


def test_model_id_validation_rejects_unsupported():
    with pytest.raises(ValidationError):
        SynthesisRequest(
            project_id="p1",
            text="hello",
            reference_audio_path="/tmp/ref.wav",
            model_id="Qwen/unsupported",
            voice_clone_authorized=True,
        )


def test_model_id_validation_accepts_supported_base_model():
    req = SynthesisRequest(
        project_id="p1",
        text="hello",
        reference_audio_path="/tmp/ref.wav",
        model_id=SUPPORTED_BASE_MODELS[0],
        voice_clone_authorized=True,
    )
    assert req.model_id == SUPPORTED_BASE_MODELS[0]


def test_metadata_completeness_fields_present():
    metadata = OutputMetadata(
        output_file="/tmp/out.mp3",
        duration_seconds=12.4,
        model=SUPPORTED_BASE_MODELS[0],
        audio_tuning_label="Version 4",
        reference_audio="/tmp/ref.mp3",
        reference_text="reference",
        input_text="input",
        chunk_mode=ChunkMode.SENTENCE,
        pause_seconds=[0.5, 0.7],
        max_new_tokens=1200,
        output_format=OutputFormat.MP3,
        seed=3,
        project_id="proj",
        job_id="job1",
        captions={"txt": "/tmp/out.txt", "srt": "/tmp/out.srt", "vtt": "/tmp/out.vtt"},
        quality=QualityReport(speech_rate_wpm=130.0, pause_stats={"min": 0.5, "max": 0.7, "mean": 0.6, "stddev": 0.1}),
        stage_durations_seconds={"model_load": 2.0, "generation": 10.0},
    )

    payload = metadata.model_dump(mode="json")
    required_keys = {
        "output_file",
        "duration_seconds",
        "model",
        "audio_tuning_label",
        "reference_audio",
        "reference_text",
        "input_text",
        "chunk_mode",
        "pause_seconds",
        "max_new_tokens",
        "created_at",
        "project_id",
        "job_id",
    }
    assert required_keys.issubset(payload.keys())


def test_simple_synthesis_request_accepts_reference_audio_hash():
    req = SimpleSynthesisRequest(
        project_id="proj1",
        text="hello",
        reference_audio_hash="a" * 64,
        voice_clone_authorized=True,
    )
    assert req.reference_audio_hash == "a" * 64


def test_simple_synthesis_request_rejects_missing_reference_input():
    with pytest.raises(ValidationError):
        SimpleSynthesisRequest(
            project_id="proj1",
            text="hello",
            voice_clone_authorized=True,
        )
