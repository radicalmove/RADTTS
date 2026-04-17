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


def coalesce_sentence_chunks(
    chunks: list[str],
    *,
    target_words: int = 26,
    max_words: int = 38,
    max_chars: int = 220,
) -> list[str]:
    cleaned = [normalize_whitespace(chunk) for chunk in chunks if normalize_whitespace(chunk)]
    if not cleaned:
        return []

    merged: list[str] = []
    current = cleaned[0]
    for next_chunk in cleaned[1:]:
        current_words = word_count(current)
        next_words = word_count(next_chunk)
        combined = f"{current} {next_chunk}".strip()
        combined_words = word_count(combined)

        if (
            current_words < target_words
            and combined_words <= max_words
            and len(combined) <= max_chars
        ):
            current = combined
            continue

        merged.append(current)
        current = next_chunk

    merged.append(current)
    return merged


def coalesce_reference_sentence_chunks(chunks: list[str]) -> list[str]:
    cleaned = [normalize_whitespace(chunk) for chunk in chunks if normalize_whitespace(chunk)]
    if not cleaned:
        return []

    total_words = sum(word_count(chunk) for chunk in cleaned)
    total_sentences = len(cleaned)
    if total_words >= 150 or total_sentences >= 12:
        return coalesce_sentence_chunks(cleaned, target_words=62, max_words=92, max_chars=440)
    if total_words >= 96 or total_sentences >= 8:
        return coalesce_sentence_chunks(cleaned, target_words=50, max_words=76, max_chars=380)
    return coalesce_sentence_chunks(cleaned)


def plan_reference_helper_batches(text: str, chunk_mode: str = "sentence") -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    if str(chunk_mode).strip().lower() == "single":
        return [cleaned]

    sentences = split_sentences(cleaned) or [cleaned]
    total_words = sum(word_count(sentence) for sentence in sentences)
    total_sentences = len(sentences)

    if total_words >= 180 or total_sentences >= 12:
        planned = coalesce_sentence_chunks(sentences, target_words=22, max_words=32, max_chars=180)
    elif total_words >= 120 or total_sentences >= 8:
        planned = coalesce_sentence_chunks(sentences, target_words=24, max_words=36, max_chars=200)
    else:
        planned = coalesce_sentence_chunks(sentences, target_words=26, max_words=38, max_chars=220)

    return planned or sentences


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def estimated_chunk_count(text: str, chunk_mode: str = "sentence", *, voice_source: str | None = None) -> int:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return 0
    if str(chunk_mode).strip().lower() == "single":
        return 1
    chunks = split_sentences(cleaned)
    if str(voice_source or "").strip().lower() == "reference":
        chunks = coalesce_reference_sentence_chunks(chunks) or chunks
    return max(1, len(chunks))


def recommended_generation_timeout_seconds(
    text: str,
    *,
    chunk_mode: str = "sentence",
    max_new_tokens: int = 1200,
    minimum_seconds: int = 600,
    maximum_seconds: int = 5400,
    voice_source: str | None = None,
    reference_duration_seconds: float | None = None,
) -> int:
    minimum = max(1, int(minimum_seconds))
    maximum = max(minimum, int(maximum_seconds))
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return minimum

    if str(chunk_mode).strip().lower() == "single":
        chunk_texts = [cleaned]
    else:
        chunk_texts = split_sentences(cleaned) or [cleaned]
        if str(voice_source or "").strip().lower() == "reference":
            chunk_texts = coalesce_reference_sentence_chunks(chunk_texts) or chunk_texts

    chunks = max(1, len(chunk_texts))
    chunk_words = [max(1, word_count(chunk)) for chunk in chunk_texts]
    words = sum(chunk_words)
    max_chunk_words = max(chunk_words)
    token_budget = max(0, int(max_new_tokens))

    # Larger scripts scale mostly with chunk count, but denser chunk layouts
    # need more headroom because the helper is doing fewer, heavier model calls.
    dense_chunk_words = max(0, words - (chunks * 10))
    longest_chunk_penalty = max(0, max_chunk_words - 24)
    estimate = (
        180
        + (chunks * 22)
        + (words * 1.35)
        + (token_budget * 0.22)
        + (dense_chunk_words * 6.0)
        + (longest_chunk_penalty * 6.0)
    )
    if str(voice_source or "").strip().lower() == "reference":
        reference_seconds = max(0.0, float(reference_duration_seconds or 0.0))
        estimate += 180 + (chunks * 28) + max(0.0, reference_seconds - 6.0) * 18.0
    bounded = max(float(minimum), min(float(maximum), estimate))
    return int(round(bounded))


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
