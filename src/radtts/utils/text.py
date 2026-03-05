"""Text processing utilities for chunking and pacing."""

from __future__ import annotations

import random
import re
from typing import Iterable

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_WORD_RE = re.compile(r"\b[\w']+\b")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    chunks = [chunk.strip() for chunk in _SENTENCE_BOUNDARY.split(cleaned) if chunk.strip()]
    if not chunks:
        return [cleaned]
    return chunks


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def maybe_add_sparse_fillers(text: str, probability: float, seed: int | None = None) -> str:
    """Inject sparse fillers in authoring text when explicitly requested."""
    if probability <= 0:
        return text
    rng = random.Random(seed)
    fillers = ["um", "ah", "you know"]
    parts = split_sentences(text)
    result: list[str] = []
    for sent in parts:
        if rng.random() < probability:
            filler = rng.choice(fillers)
            sent = f"{filler}, {sent[0].lower() + sent[1:] if len(sent) > 1 else sent}"
        result.append(sent)
    return " ".join(result)


def flatten_lines(lines: Iterable[str]) -> str:
    return normalize_whitespace(" ".join(lines))
