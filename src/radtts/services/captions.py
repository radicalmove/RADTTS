"""Caption generation for synthesized outputs."""

from __future__ import annotations

from pathlib import Path

from radtts.models import CaptionArtifacts
from radtts.services.asr import ASRService
from radtts.utils.subtitles import write_vtt


class CaptionService:
    def __init__(self, model_size: str = "small"):
        self._asr = ASRService(model_size=model_size)

    def generate(
        self,
        *,
        audio_path: Path,
        output_dir: Path,
        name: str,
        language: str | None = None,
    ) -> CaptionArtifacts:
        artifacts, segments = self._asr.transcribe(
            audio_path,
            output_dir,
            name=name,
            language=language,
            beam_size=5,
        )
        vtt_path = output_dir / f"{name}.vtt"
        write_vtt(vtt_path, segments)
        return CaptionArtifacts(
            txt_path=artifacts.txt_path,
            srt_path=artifacts.srt_path,
            vtt_path=vtt_path,
        )
