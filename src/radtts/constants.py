"""Static constants used across the RADTTS pipeline."""

from __future__ import annotations

SUPPORTED_BASE_MODELS = [
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
]

MODEL_MODE_ALIASES = {
    "fast": SUPPORTED_BASE_MODELS[0],
    "quality": SUPPORTED_BASE_MODELS[1],
}

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
