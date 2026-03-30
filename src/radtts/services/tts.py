"""Qwen3-TTS wrapper for reference cloning and built-in speakers."""

from __future__ import annotations

import contextlib
import inspect
import os
import tempfile
import time
from pathlib import Path
from random import Random
from typing import Any, Callable

import numpy as np

from radtts.constants import (
    DEFAULT_AUDIO_TUNING_LABEL,
    DEFAULT_REFERENCE_AUDIO_FILTER,
    DEFAULT_TTS_OUTPUT_FILTER,
    SUPPORTED_BASE_MODELS,
    SUPPORTED_CUSTOM_MODELS,
    SUPPORTED_TTS_MODELS,
)
from radtts.exceptions import DependencyMissingError, ValidationError
from radtts.models import ChunkMode, PauseConfig, SynthesisRequest, VoiceSource
from radtts.services.asr import ASRService
from radtts.utils.audio import concat_with_silence, convert_audio, probe_duration_seconds, read_audio, write_wav
from radtts.utils.text import split_sentences, word_count


class PausePlanner:
    def build(self, chunks: list[str], config: PauseConfig) -> list[float]:
        rng = Random(config.seed)
        pauses: list[float] = []
        for idx, sentence in enumerate(chunks[:-1]):
            base = rng.uniform(config.min_seconds, config.max_seconds)
            words = max(1, word_count(sentence))
            length_bonus = min(0.25, (words / 35.0) * 0.15)
            punctuation_bonus = 0.0
            if sentence.rstrip().endswith("?"):
                punctuation_bonus += 0.08
            if sentence.rstrip().endswith("!"):
                punctuation_bonus += 0.06
            pause = min(config.max_seconds, max(config.min_seconds, base + length_bonus + punctuation_bonus))
            pauses.append(round(pause, 3))
        return pauses


def current_audio_tuning_label() -> str:
    raw = str(os.environ.get("RADTTS_AUDIO_TUNING_LABEL", DEFAULT_AUDIO_TUNING_LABEL)).strip()
    return raw or DEFAULT_AUDIO_TUNING_LABEL


class TTSService:
    MIN_REFERENCE_DURATION_SECONDS = 2.5
    MIN_REFERENCE_WORDS = 2
    MIN_REFERENCE_TEXT_CHARS = 8
    DEFAULT_MODEL_CACHE_IDLE_SECONDS = 1800

    def __init__(self, *, auto_reference_asr_model: str = "small"):
        self._model_cache: dict[str, Any] = {}
        self._model_cache_last_used: dict[str, float] = {}
        self._pause_planner = PausePlanner()
        self._asr_service = ASRService(model_size=auto_reference_asr_model)
        self.reference_audio_filter = str(
            os.environ.get("RADTTS_REFERENCE_AUDIO_FILTER", DEFAULT_REFERENCE_AUDIO_FILTER)
        ).strip()
        self.output_audio_filter = str(
            os.environ.get("RADTTS_OUTPUT_AUDIO_FILTER", DEFAULT_TTS_OUTPUT_FILTER)
        ).strip()
        self.audio_tuning_label = current_audio_tuning_label()
        self.model_cache_idle_seconds = max(
            0,
            int(os.environ.get("RADTTS_MODEL_CACHE_IDLE_SECONDS", self.DEFAULT_MODEL_CACHE_IDLE_SECONDS)),
        )

    def ensure_supported_model(self, model_id: str) -> None:
        if model_id not in SUPPORTED_TTS_MODELS:
            raise ValueError(f"Unsupported model id: {model_id}")

    def synthesize(
        self,
        req: SynthesisRequest,
        output_dir: Path,
        *,
        on_progress: Callable[[str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> tuple[Path, list[float], str]:
        self.ensure_supported_model(req.model_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        with contextlib.ExitStack() as stack:
            reference_audio_path = None
            reference_text = req.reference_text
            if req.voice_source == VoiceSource.REFERENCE:
                if req.reference_audio_path is None:
                    raise ValidationError("Reference audio is required for reference voice synthesis.")
                if on_progress:
                    on_progress("preparing reference audio")
                reference_audio_path = self._prepare_reference_audio_path(req.reference_audio_path, stack=stack)
                warnings = self.validate_reference_audio(reference_audio_path)
                if on_progress:
                    if warnings:
                        for warning in warnings[:2]:
                            on_progress(f"reference validation warning: {warning}")
                    else:
                        on_progress("reference sample check complete")
                if req.reference_text:
                    reference_text = req.reference_text
                else:
                    if on_progress:
                        on_progress("reference transcription started")
                    reference_text = self._auto_reference_text(reference_audio_path)
                    if on_progress:
                        on_progress("reference transcription complete")

            chunks = self._build_chunks(req.text, req.chunk_mode)
            pauses = self._pause_planner.build(chunks, req.pause_config) if req.chunk_mode == ChunkMode.SENTENCE else []

            model = self._load_model(req.model_id)
            chunk_audio: list[tuple[np.ndarray, int]] = []
            for idx, chunk in enumerate(chunks):
                if cancel_check and cancel_check():
                    raise RuntimeError("job cancelled")
                if req.voice_source == VoiceSource.REFERENCE:
                    assert reference_audio_path is not None
                    audio, sample_rate = self._synthesize_reference_chunk(
                        model=model,
                        text=chunk,
                        reference_audio_path=reference_audio_path,
                        reference_text=reference_text or "",
                        max_new_tokens=req.max_new_tokens,
                    )
                else:
                    audio, sample_rate = self._synthesize_builtin_chunk(
                        model=model,
                        text=chunk,
                        speaker=req.built_in_speaker or "",
                        instruct=req.built_in_instruct,
                        max_new_tokens=req.max_new_tokens,
                    )
                chunk_audio.append((audio, sample_rate))
                if on_progress:
                    on_progress(f"generation chunk {idx + 1}/{len(chunks)}")

            if on_progress:
                on_progress("stitching chunks")
            sample_rate = chunk_audio[0][1]
            stitched = concat_with_silence(chunk_audio, pauses, sample_rate)

            base_name = req.output_name
            raw_output_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="radtts_output_")))
            raw_wav_path = raw_output_dir / f"{base_name}.wav"
            write_wav(raw_wav_path, stitched, sample_rate)

            if req.output_format.value == "wav":
                wav_path = output_dir / f"{base_name}.wav"
                if self.output_audio_filter:
                    convert_audio(raw_wav_path, wav_path, audio_filters=self.output_audio_filter)
                else:
                    wav_path.write_bytes(raw_wav_path.read_bytes())
                return wav_path, pauses, reference_text or ""

            if on_progress:
                on_progress("stitching encoding mp3")
            mp3_path = output_dir / f"{base_name}.mp3"
            convert_audio(raw_wav_path, mp3_path, audio_filters=self.output_audio_filter)
            return mp3_path, pauses, reference_text or ""

    def list_builtin_speakers(self, model_id: str) -> list[str]:
        self.ensure_supported_model(model_id)
        if model_id not in SUPPORTED_CUSTOM_MODELS:
            raise ValueError("Built-in speakers require a CustomVoice model")
        model = self._load_model(model_id)
        getter = getattr(model, "get_supported_speakers", None)
        if callable(getter):
            speakers = getter()
            if speakers:
                return [str(item) for item in speakers]
        return []

    def _auto_reference_text(self, reference_audio_path: Path) -> str:
        try:
            duration_seconds = probe_duration_seconds(reference_audio_path)
        except Exception:
            duration_seconds = None

        if duration_seconds is not None and duration_seconds < self.MIN_REFERENCE_DURATION_SECONDS:
            raise ValidationError(
                "Reference sample is too short. Please use at least 3 seconds of clear speech, ideally a full sentence."
            )

        with tempfile.TemporaryDirectory(prefix="radtts_ref_asr_") as tmp:
            artifacts, _ = self._asr_service.transcribe(
                reference_audio_path,
                Path(tmp),
                name="reference",
                language=None,
                beam_size=3,
            )
            transcript = artifacts.txt_path.read_text(encoding="utf-8").strip()

        if (
            len(transcript) < self.MIN_REFERENCE_TEXT_CHARS
            or word_count(transcript) < self.MIN_REFERENCE_WORDS
        ):
            raise ValidationError(
                "Reference sample is too short or unclear to clone reliably. Please use at least one clear full sentence."
            )

        return transcript

    def _prepare_reference_audio_path(
        self,
        reference_audio_path: Path,
        *,
        stack: contextlib.ExitStack,
    ) -> Path:
        path = Path(reference_audio_path)
        if path.suffix.lower() == ".wav" and not self.reference_audio_filter:
            return path

        temp_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="radtts_ref_audio_")))
        normalized_path = temp_dir / f"{path.stem or 'reference'}.wav"
        convert_audio(path, normalized_path, audio_filters=self.reference_audio_filter)
        return normalized_path

    @staticmethod
    def _build_chunks(text: str, chunk_mode: ChunkMode) -> list[str]:
        if chunk_mode == ChunkMode.SINGLE:
            return [text.strip()]
        chunks = split_sentences(text)
        if not chunks:
            return [text.strip()]
        return chunks

    @staticmethod
    def _env_override(name: str) -> str | None:
        raw = str(os.environ.get(name, "")).strip()
        if not raw or raw.lower() in {"auto", "default"}:
            return None
        return raw

    @classmethod
    def _preferred_device(cls) -> str:
        override = cls._env_override("RADTTS_TTS_DEVICE")
        if override:
            return override

        try:
            import torch
        except Exception:
            return "cpu"

        if torch.cuda.is_available():
            return "cuda:0"

        mps_backend = getattr(getattr(torch, "backends", None), "mps", None)
        if mps_backend is not None and mps_backend.is_available():
            return "mps"

        return "cpu"

    @classmethod
    def _preferred_dtype(cls, device: str) -> Any | None:
        try:
            import torch
        except Exception:
            return None

        override = cls._env_override("RADTTS_TTS_DTYPE")
        if override:
            normalized = override.lower()
            dtype_aliases = {
                "float16": torch.float16,
                "fp16": torch.float16,
                "half": torch.float16,
                "bfloat16": torch.bfloat16,
                "bf16": torch.bfloat16,
                "float32": torch.float32,
                "fp32": torch.float32,
            }
            if normalized not in dtype_aliases:
                raise ValueError(f"Unsupported RADTTS_TTS_DTYPE value: {override}")
            return dtype_aliases[normalized]

        if str(device).startswith("cuda"):
            return torch.float16
        if str(device).startswith("mps"):
            return torch.float32
        return None

    @classmethod
    def model_load_kwargs(cls) -> dict[str, Any]:
        device = cls._preferred_device()
        dtype = cls._preferred_dtype(device)

        kwargs: dict[str, Any] = {}
        if device:
            kwargs["device_map"] = device
        if dtype is not None:
            kwargs["dtype"] = dtype
        return kwargs

    @staticmethod
    def describe_model_runtime(model: Any, *, model_id: str | None = None) -> str:
        device = getattr(model, "device", None)
        dtype = getattr(model, "dtype", None)
        inner = getattr(model, "model", None)

        if inner is not None:
            try:
                first_param = next(inner.parameters())
                device = first_param.device
                dtype = first_param.dtype
            except Exception:
                device = getattr(inner, "device", device)
                dtype = getattr(inner, "dtype", dtype)

        device_label = str(device or "unknown")
        dtype_label = str(dtype or "unknown")
        prefix = f"tts model={model_id} runtime" if model_id else "tts runtime"
        return f"{prefix} device={device_label} dtype={dtype_label}"

    def load_model_with_runtime(self, model_id: str) -> tuple[Any, str]:
        self.ensure_supported_model(model_id)
        cache_state = "warm" if self._is_model_warm(model_id) else "fresh"
        model = self._load_model(model_id)
        return model, f"{self.describe_model_runtime(model, model_id=model_id)} cache={cache_state}"

    def _evict_idle_models(self, *, now: float | None = None) -> None:
        if self.model_cache_idle_seconds <= 0:
            return
        current = float(now if now is not None else time.monotonic())
        stale = [
            model_id
            for model_id, last_used in self._model_cache_last_used.items()
            if current - last_used > self.model_cache_idle_seconds
        ]
        for model_id in stale:
            self._model_cache.pop(model_id, None)
            self._model_cache_last_used.pop(model_id, None)

    def _is_model_warm(self, model_id: str, *, now: float | None = None) -> bool:
        self._evict_idle_models(now=now)
        return model_id in self._model_cache

    def _touch_model(self, model_id: str, *, now: float | None = None) -> None:
        self._model_cache_last_used[model_id] = float(now if now is not None else time.monotonic())

    def _load_model(self, model_id: str) -> Any:
        self._evict_idle_models()
        if model_id in self._model_cache:
            self._touch_model(model_id)
            return self._model_cache[model_id]
        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise DependencyMissingError(
                "qwen-tts is required for synthesis. Install with 'pip install -e .[tts]'."
            ) from exc

        load_kwargs = self.model_load_kwargs()
        if hasattr(Qwen3TTSModel, "from_pretrained"):
            model = Qwen3TTSModel.from_pretrained(model_id, **load_kwargs)
        else:
            model = Qwen3TTSModel(model_id)
        self._model_cache[model_id] = model
        self._touch_model(model_id)
        return model

    def validate_reference_audio(self, reference_audio_path: Path) -> list[str]:
        warnings: list[str] = []
        try:
            duration_seconds = probe_duration_seconds(reference_audio_path)
        except Exception:
            duration_seconds = None

        if duration_seconds is not None and duration_seconds < self.MIN_REFERENCE_DURATION_SECONDS:
            raise ValidationError(
                "Reference sample is too short. Please use at least 3 seconds of clear speech, ideally a full sentence."
            )

        try:
            audio, _sample_rate = read_audio(reference_audio_path)
        except Exception:
            return warnings

        if audio.size == 0:
            raise ValidationError("Reference sample is empty. Please choose a clear spoken sample.")

        level = np.abs(audio.astype(np.float32))
        peak = float(np.max(level))
        rms = float(np.sqrt(np.mean(np.square(level))))
        clipped_ratio = float(np.mean(level >= 0.995))

        if rms < 0.0015:
            raise ValidationError("Reference sample is too quiet. Please choose a clearer, louder spoken sample.")
        if rms < 0.015:
            warnings.append("Reference sample sounds quiet; voice matching may be weaker.")
        if peak >= 0.995 or clipped_ratio > 0.001:
            warnings.append("Reference sample may be clipped; distortion can reduce voice quality.")
        if duration_seconds is not None and duration_seconds > 30:
            warnings.append("Reference sample is long; trimming to 6 to 15 seconds usually gives cleaner cloning.")

        return warnings

    def _synthesize_reference_chunk(
        self,
        *,
        model: Any,
        text: str,
        reference_audio_path: Path,
        reference_text: str,
        max_new_tokens: int,
    ) -> tuple[np.ndarray, int]:
        fn = getattr(model, "generate_voice_clone", None)
        if fn is None:
            raise RuntimeError("Loaded model does not expose generate_voice_clone")

        kwargs = self._build_clone_kwargs(
            fn=fn,
            text=text,
            reference_audio_path=reference_audio_path,
            reference_text=reference_text,
            max_new_tokens=max_new_tokens,
        )

        try:
            result = fn(**kwargs)
        except TypeError:
            result = fn(text, str(reference_audio_path), reference_text)

        return self._parse_generation_result(result, model)

    def _synthesize_builtin_chunk(
        self,
        *,
        model: Any,
        text: str,
        speaker: str,
        instruct: str | None,
        max_new_tokens: int,
    ) -> tuple[np.ndarray, int]:
        fn = getattr(model, "generate_custom_voice", None)
        if fn is None:
            raise RuntimeError("Loaded model does not expose generate_custom_voice")

        kwargs = self._build_builtin_kwargs(
            fn=fn,
            text=text,
            speaker=speaker,
            instruct=instruct,
            max_new_tokens=max_new_tokens,
            language=self._infer_builtin_language(text),
        )
        try:
            result = fn(**kwargs)
        except TypeError:
            result = fn(text=text, speaker=speaker)
        return self._parse_generation_result(result, model)

    @staticmethod
    def _build_clone_kwargs(
        *,
        fn: Callable[..., Any],
        text: str,
        reference_audio_path: Path,
        reference_text: str,
        max_new_tokens: int,
    ) -> dict[str, Any]:
        sig = inspect.signature(fn)
        params = sig.parameters
        names = set(params.keys())

        kwargs: dict[str, Any] = {}

        text_keys = ["text", "target_text", "input_text", "content"]
        audio_keys = [
            "ref_audio",
            "reference_audio_path",
            "prompt_wav_path",
            "prompt_audio_path",
            "reference_wav_path",
            "ref_wav_path",
            "audio_prompt_path",
            "prompt_speech_path",
            "prompt_audio",
        ]
        ref_text_keys = ["reference_text", "prompt_text", "ref_text", "audio_prompt_text"]
        token_keys = ["max_new_tokens", "max_tokens"]

        for key in text_keys:
            if key in names:
                kwargs[key] = text
                break
        for key in audio_keys:
            if key in names:
                kwargs[key] = str(reference_audio_path)
                break
        for key in ref_text_keys:
            if key in names:
                kwargs[key] = reference_text
                break
        for key in token_keys:
            if key in names:
                kwargs[key] = int(max_new_tokens)
                break

        if not kwargs and any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            kwargs = {
                "text": text,
                "reference_audio_path": str(reference_audio_path),
                "reference_text": reference_text,
                "max_new_tokens": int(max_new_tokens),
            }

        return kwargs

    @staticmethod
    def _build_builtin_kwargs(
        *,
        fn: Callable[..., Any],
        text: str,
        speaker: str,
        instruct: str | None,
        max_new_tokens: int,
        language: str | None,
    ) -> dict[str, Any]:
        sig = inspect.signature(fn)
        params = sig.parameters
        names = set(params.keys())

        kwargs: dict[str, Any] = {}
        if "text" in names:
            kwargs["text"] = text
        if "speaker" in names:
            kwargs["speaker"] = speaker
        if language and "language" in names:
            kwargs["language"] = language
        if instruct and "instruct" in names:
            kwargs["instruct"] = instruct
        if "max_new_tokens" in names:
            kwargs["max_new_tokens"] = int(max_new_tokens)
        elif "max_tokens" in names:
            kwargs["max_tokens"] = int(max_new_tokens)
        return kwargs

    @staticmethod
    def _infer_builtin_language(text: str) -> str:
        sample = str(text or "").strip()
        if not sample:
            return "English"
        if any("\u4e00" <= ch <= "\u9fff" for ch in sample):
            return "Chinese"
        if any("\u3040" <= ch <= "\u30ff" for ch in sample):
            return "Japanese"
        if any("\uac00" <= ch <= "\ud7af" for ch in sample):
            return "Korean"
        return "English"

    @staticmethod
    def _parse_generation_result(result: Any, model: Any) -> tuple[np.ndarray, int]:
        sample_rate = int(
            getattr(model, "sampling_rate", None)
            or getattr(model, "sample_rate", None)
            or 24000
        )

        audio: Any
        if isinstance(result, tuple) and len(result) >= 2:
            audio, sample_rate = result[0], int(result[1])
        elif isinstance(result, dict):
            audio = (
                result.get("audio")
                or result.get("wav")
                or result.get("waveform")
                or result.get("output")
            )
            sample_rate = int(
                result.get("sample_rate")
                or result.get("sampling_rate")
                or sample_rate
            )
        else:
            audio = result

        try:
            import torch

            if isinstance(audio, torch.Tensor):
                audio = audio.detach().cpu().numpy()
        except Exception:
            pass

        if isinstance(audio, list):
            if not audio:
                raise RuntimeError("Unable to parse generated audio from qwen-tts output: empty list")
            if len(audio) == 1:
                audio = audio[0]
            else:
                # Multi-utterance output: flatten into one continuous waveform.
                audio = np.concatenate([np.asarray(item, dtype=np.float32).reshape(-1) for item in audio])
        if not isinstance(audio, np.ndarray):
            audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim == 0:
            raise RuntimeError("Unable to parse generated audio from qwen-tts output")
        if audio.ndim > 1:
            if audio.shape[0] == 1:
                audio = audio[0]
            elif audio.shape[-1] in (1, 2):
                audio = np.mean(audio, axis=-1)
            elif audio.shape[0] in (1, 2):
                audio = np.mean(audio, axis=0)
            else:
                audio = audio.reshape(-1)
        return audio.astype(np.float32), sample_rate
