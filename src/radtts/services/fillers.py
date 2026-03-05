"""Conservative filler-word text processing."""

from __future__ import annotations

import re

_FILLER_RE = re.compile(r"\b(um+|uh+|ah+|erm+|mmm+)\b", re.IGNORECASE)


def remove_fillers_from_text(text: str) -> str:
    cleaned = _FILLER_RE.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    return cleaned.strip()
