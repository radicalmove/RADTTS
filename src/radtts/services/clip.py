"""Transcript-aligned clip extraction service."""

from __future__ import annotations

from pathlib import Path

from radtts.models import BoundaryReport, ClipRequest, TranscriptSegment
from radtts.utils.audio import extract_clip


class ClipService:
    def __init__(self, *, min_duration_seconds: float = 0.25):
        self.min_duration_seconds = min_duration_seconds

    def extract_verified_clip(
        self,
        *,
        req: ClipRequest,
        segments: list[TranscriptSegment],
        output_dir: Path,
    ) -> tuple[Path, BoundaryReport]:
        start, start_seg = self._resolve_start(req, segments)
        end, end_seg = self._resolve_end(req, segments, start)

        if end <= start:
            raise ValueError(f"Invalid clip boundary: start={start} end={end}")

        warnings: list[str] = []
        duration = end - start
        if duration < self.min_duration_seconds:
            warnings.append("clip duration is very short")

        if start_seg and req.start_time is not None:
            drift = abs(req.start_time - start_seg.start)
            if drift > 1.0:
                warnings.append("start_time is far from transcript boundary")

        if end_seg and req.end_time is not None:
            drift = abs(req.end_time - end_seg.end)
            if drift > 1.0:
                warnings.append("end_time is far from transcript boundary")

        confidence_values = [c for c in [start_seg.confidence if start_seg else None, end_seg.confidence if end_seg else None] if c is not None]
        confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{req.output_name}.{req.output_format.value}"
        extract_clip(req.audio_path, output_path, start, end)

        report = BoundaryReport(
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            start_segment_id=start_seg.id if start_seg else None,
            end_segment_id=end_seg.id if end_seg else None,
            start_segment_text=start_seg.text if start_seg else None,
            end_segment_text=end_seg.text if end_seg else None,
            confidence=confidence,
            warnings=warnings,
        )
        return output_path, report

    def _resolve_start(
        self, req: ClipRequest, segments: list[TranscriptSegment]
    ) -> tuple[float, TranscriptSegment | None]:
        if req.start_phrase:
            seg = self._find_phrase_segment(segments, req.start_phrase)
            if seg is None:
                raise ValueError(f"start_phrase not found in transcript: {req.start_phrase}")
            return max(0.0, seg.start - 0.04), seg
        if req.start_time is None:
            raise ValueError("start boundary missing")
        seg = self._nearest_segment(segments, req.start_time)
        return req.start_time, seg

    def _resolve_end(
        self, req: ClipRequest, segments: list[TranscriptSegment], start_seconds: float
    ) -> tuple[float, TranscriptSegment | None]:
        if req.end_phrase:
            seg = self._find_phrase_segment(segments, req.end_phrase, after=start_seconds)
            if seg is None:
                raise ValueError(f"end_phrase not found in transcript: {req.end_phrase}")
            return seg.end + 0.04, seg
        if req.end_time is None:
            raise ValueError("end boundary missing")
        seg = self._nearest_segment(segments, req.end_time)
        return req.end_time, seg

    @staticmethod
    def _find_phrase_segment(
        segments: list[TranscriptSegment], phrase: str, after: float | None = None
    ) -> TranscriptSegment | None:
        phrase_l = phrase.lower().strip()
        for seg in segments:
            if after is not None and seg.start < after:
                continue
            if phrase_l in seg.text.lower():
                return seg
        return None

    @staticmethod
    def _nearest_segment(segments: list[TranscriptSegment], t: float) -> TranscriptSegment | None:
        if not segments:
            return None
        return min(segments, key=lambda seg: min(abs(seg.start - t), abs(seg.end - t)))
