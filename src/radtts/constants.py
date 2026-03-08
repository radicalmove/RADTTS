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
    {"id": "Aiden", "label": "Aiden"},
    {"id": "Dylan", "label": "Dylan"},
    {"id": "Eric", "label": "Eric"},
    {"id": "Ono_Anna", "label": "Ono Anna"},
    {"id": "Ryan", "label": "Ryan"},
    {"id": "Serena", "label": "Serena"},
    {"id": "Sohee", "label": "Sohee"},
    {"id": "Uncle_Fu", "label": "Uncle Fu"},
    {"id": "Vivian", "label": "Vivian"},
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
