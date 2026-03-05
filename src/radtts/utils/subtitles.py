"""Helpers for writing subtitle/caption artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from radtts.models import TranscriptSegment


def _format_srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3600 * 1000)
    minutes, rem = divmod(rem, 60 * 1000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def _format_vtt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3600 * 1000)
    minutes, rem = divmod(rem, 60 * 1000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{ms:03}"


def write_txt(path: Path, segments: Iterable[TranscriptSegment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(seg.text.strip() for seg in segments if seg.text.strip())
    path.write_text(text + "\n", encoding="utf-8")


def write_srt(path: Path, segments: Iterable[TranscriptSegment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        lines.extend(
            [
                str(idx),
                f"{_format_srt_timestamp(seg.start)} --> {_format_srt_timestamp(seg.end)}",
                seg.text.strip(),
                "",
            ]
        )
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_vtt(path: Path, segments: Iterable[TranscriptSegment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines.extend(
            [
                f"{_format_vtt_timestamp(seg.start)} --> {_format_vtt_timestamp(seg.end)}",
                seg.text.strip(),
                "",
            ]
        )
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
