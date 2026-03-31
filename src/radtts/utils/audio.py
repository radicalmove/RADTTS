"""Audio utility functions built around ffmpeg and soundfile."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


def get_ffmpeg_binary() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found. Install ffmpeg or imageio-ffmpeg.")
        return ffmpeg


def get_ffprobe_binary() -> str:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe

    ffmpeg = get_ffmpeg_binary()
    sibling = Path(ffmpeg).with_name("ffprobe")
    if sibling.exists():
        return str(sibling)
    raise RuntimeError("ffprobe not found. Install ffmpeg/ffprobe or imageio-ffmpeg.")


def probe_duration_seconds(path: Path) -> float:
    try:
        info = sf.info(str(path))
        return float(info.frames) / float(info.samplerate)
    except Exception:
        ffprobe = get_ffprobe_binary()
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        duration_text = str(result.stdout or "").strip()
        if not duration_text:
            raise RuntimeError(f"ffprobe returned no duration for {path}")
        return float(duration_text)


def convert_audio(input_path: Path, output_path: Path, *, audio_filters: str | None = None) -> Path:
    ffmpeg = get_ffmpeg_binary()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-i", str(input_path)]
    if audio_filters and audio_filters.strip():
        cmd.extend(["-af", audio_filters.strip()])
    cmd.append(str(output_path))
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def extract_clip(input_path: Path, output_path: Path, start_seconds: float, end_seconds: float) -> Path:
    ffmpeg = get_ffmpeg_binary()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        f"{start_seconds:.3f}",
        "-to",
        f"{end_seconds:.3f}",
        "-i",
        str(input_path),
        "-vn",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sample_rate)
    return path


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=False)
    if isinstance(data, np.ndarray) and data.ndim > 1:
        data = np.mean(data, axis=1)
    return np.asarray(data, dtype=np.float32), int(sr)


def concat_with_silence(
    chunks: list[tuple[np.ndarray, int]], pause_seconds: list[float], sample_rate: int
) -> np.ndarray:
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    parts: list[np.ndarray] = []
    for idx, (audio, sr) in enumerate(chunks):
        if sr != sample_rate:
            raise ValueError(f"Mismatched sample rate in chunks: {sr} != {sample_rate}")
        parts.append(audio)
        if idx < len(pause_seconds):
            pause_samples = max(0, int(round(pause_seconds[idx] * sample_rate)))
            parts.append(np.zeros(pause_samples, dtype=np.float32))
    return np.concatenate(parts)
