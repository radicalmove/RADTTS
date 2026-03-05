"""faster-whisper wrapper for transcript artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from radtts.exceptions import DependencyMissingError
from radtts.models import TranscriptArtifacts, TranscriptSegment, TranscriptWord
from radtts.utils.subtitles import write_srt, write_txt


class ASRService:
    def __init__(self, model_size: str = "small", device: str = "auto", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        *,
        name: str,
        language: str | None = None,
        beam_size: int = 5,
    ) -> tuple[TranscriptArtifacts, list[TranscriptSegment]]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise DependencyMissingError(
                "faster-whisper is required for transcription. Install with 'pip install -e .[asr]'."
            ) from exc

        output_dir.mkdir(parents=True, exist_ok=True)
        model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        seg_iter, _ = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            word_timestamps=True,
            vad_filter=True,
        )

        segments: list[TranscriptSegment] = []
        for idx, seg in enumerate(seg_iter):
            words: list[TranscriptWord] = []
            for word in seg.words or []:
                words.append(
                    TranscriptWord(
                        word=word.word.strip(),
                        start=float(word.start),
                        end=float(word.end),
                        probability=float(word.probability) if word.probability is not None else None,
                    )
                )
            confidence = None
            if seg.avg_logprob is not None:
                confidence = max(0.0, min(1.0, float(1.0 + (seg.avg_logprob / 5.0))))
            segments.append(
                TranscriptSegment(
                    id=idx,
                    start=float(seg.start),
                    end=float(seg.end),
                    text=seg.text.strip(),
                    avg_logprob=float(seg.avg_logprob) if seg.avg_logprob is not None else None,
                    no_speech_prob=float(seg.no_speech_prob) if seg.no_speech_prob is not None else None,
                    confidence=confidence,
                    words=words,
                )
            )

        segments_json_path = output_dir / f"{name}.segments.json"
        txt_path = output_dir / f"{name}.txt"
        srt_path = output_dir / f"{name}.srt"

        segments_json_path.write_text(
            json.dumps([seg.model_dump(mode="json") for seg in segments], indent=2),
            encoding="utf-8",
        )
        write_txt(txt_path, segments)
        write_srt(srt_path, segments)

        return (
            TranscriptArtifacts(
                segments_json_path=segments_json_path,
                txt_path=txt_path,
                srt_path=srt_path,
            ),
            segments,
        )

    @staticmethod
    def load_segments(segments_json_path: Path) -> list[TranscriptSegment]:
        payload = json.loads(segments_json_path.read_text(encoding="utf-8"))
        return [TranscriptSegment(**item) for item in payload]
