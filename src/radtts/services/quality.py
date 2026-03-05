"""Quality heuristics for synthesized audio and clip boundaries."""

from __future__ import annotations

import statistics

from radtts.models import QualityReport
from radtts.utils.text import word_count


class QualityService:
    def evaluate(
        self,
        *,
        text: str,
        duration_seconds: float,
        pause_seconds: list[float],
        boundary_warnings: list[str] | None = None,
    ) -> QualityReport:
        warnings = list(boundary_warnings or [])
        words = max(1, word_count(text))
        minutes = max(duration_seconds / 60.0, 1e-6)
        speech_rate_wpm = words / minutes

        if speech_rate_wpm > 190:
            warnings.append("speech rate is high")
        if speech_rate_wpm < 85:
            warnings.append("speech rate is very slow")

        if pause_seconds:
            pause_min = min(pause_seconds)
            pause_max = max(pause_seconds)
            pause_mean = statistics.mean(pause_seconds)
            pause_std = statistics.pstdev(pause_seconds) if len(pause_seconds) > 1 else 0.0
        else:
            pause_min = 0.0
            pause_max = 0.0
            pause_mean = 0.0
            pause_std = 0.0

        if pause_min and pause_min < 0.15:
            warnings.append("very short pauses detected")
        if pause_max > 2.5:
            warnings.append("very long pauses detected")
        if pause_std < 0.05 and len(pause_seconds) >= 3:
            warnings.append("pause rhythm may be too uniform")
        if duration_seconds < 0.5:
            warnings.append("duration below minimum threshold")

        pause_stats = {
            "min": round(pause_min, 3),
            "max": round(pause_max, 3),
            "mean": round(pause_mean, 3),
            "stddev": round(pause_std, 3),
        }

        return QualityReport(
            speech_rate_wpm=round(speech_rate_wpm, 2),
            pause_stats=pause_stats,
            warnings=warnings,
        )
