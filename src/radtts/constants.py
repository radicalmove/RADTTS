"""Static constants used across the RADTTS pipeline."""

from __future__ import annotations

SUPPORTED_BASE_MODELS = [
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
]

SUPPORTED_CUSTOM_MODELS = [
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
]

SUPPORTED_TTS_MODELS = SUPPORTED_BASE_MODELS + SUPPORTED_CUSTOM_MODELS

MODEL_MODE_ALIASES = {
    "fast": SUPPORTED_BASE_MODELS[0],
    "quality": SUPPORTED_BASE_MODELS[1],
}

BUILTIN_MODEL_MODE_ALIASES = {
    "fast": SUPPORTED_CUSTOM_MODELS[0],
    "quality": SUPPORTED_CUSTOM_MODELS[1],
}

QWEN_CUSTOM_VOICE_SPEAKERS = [
    {"id": "Aiden", "label": "Aiden", "native_language": "English"},
    {"id": "Dylan", "label": "Dylan", "native_language": "Chinese"},
    {"id": "Eric", "label": "Eric", "native_language": "Chinese"},
    {"id": "Ono_Anna", "label": "Ono Anna", "native_language": "Japanese"},
    {"id": "Ryan", "label": "Ryan", "native_language": "English"},
    {"id": "Serena", "label": "Serena", "native_language": "Chinese"},
    {"id": "Sohee", "label": "Sohee", "native_language": "Korean"},
    {"id": "Uncle_Fu", "label": "Uncle Fu", "native_language": "Chinese"},
    {"id": "Vivian", "label": "Vivian", "native_language": "Chinese"},
]

DEFAULT_PRESETS = {
    "natural_lecture_intro": {
        "chunk_mode": "sentence",
        "pause_config": {"min_seconds": 0.45, "max_seconds": 1.10, "seed": None},
        "max_new_tokens": 1200,
        "model_mode": "quality",
    },
    "bridge_segment": {
        "chunk_mode": "sentence",
        "pause_config": {"min_seconds": 0.30, "max_seconds": 0.85, "seed": None},
        "max_new_tokens": 900,
        "model_mode": "fast",
    },
    "short_concept_explainer": {
        "chunk_mode": "single",
        "pause_config": {"min_seconds": 0.25, "max_seconds": 0.50, "seed": None},
        "max_new_tokens": 700,
        "model_mode": "fast",
    },
}

DEFAULT_STAGE_TIMEOUTS = {
    "model_load": 600,
    "generation": 1800,
    "stitching": 300,
    "captioning": 900,
}

DEFAULT_STAGE_RETRIES = {
    "model_load": 1,
    "generation": 1,
    "stitching": 1,
    "captioning": 1,
}

DEFAULT_REFERENCE_AUDIO_FILTER = (
    "highpass=f=80,"
    "agate=threshold=0.015:ratio=1.15:attack=8:release=180:range=0.6:knee=3,"
    "equalizer=f=6200:t=q:w=1.2:g=-1.0"
)

DEFAULT_TTS_OUTPUT_FILTER = (
    "highpass=f=60,"
    "equalizer=f=6400:t=q:w=1.2:g=-1.2,"
    "deesser=i=0.08:m=0.35:f=0.5:s=o"
)
