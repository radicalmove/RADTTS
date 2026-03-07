"""Shared progress milestones for local and worker synthesis jobs."""

from __future__ import annotations

from radtts.models import OutputFormat

GENERATION_PROGRESS_START = 0.35
STITCHING_PROGRESS_START = 0.72
STITCHING_PROGRESS_MID = 0.78
STITCHING_PROGRESS_END = 0.84
CAPTIONING_PROGRESS_START = 0.85
UPLOAD_PROGRESS = 0.97


def generation_progress_for_chunk(completed_chunks: int, total_chunks: int) -> float:
    total = max(1, int(total_chunks))
    completed = min(total, max(0, int(completed_chunks)))
    ratio = completed / total
    progress = GENERATION_PROGRESS_START + ((STITCHING_PROGRESS_START - GENERATION_PROGRESS_START) * ratio)
    return round(progress, 4)


def stitching_progress_for_output(output_format: OutputFormat | str, *, encoding_started: bool) -> float:
    value = output_format.value if isinstance(output_format, OutputFormat) else str(output_format).strip().lower()
    if value == OutputFormat.MP3.value:
        return STITCHING_PROGRESS_END if encoding_started else STITCHING_PROGRESS_MID
    return STITCHING_PROGRESS_END
