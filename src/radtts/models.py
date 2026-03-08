"""Shared pydantic models for CLI and API operations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .constants import QWEN_CUSTOM_VOICE_SPEAKERS, SUPPORTED_BASE_MODELS, SUPPORTED_CUSTOM_MODELS, SUPPORTED_TTS_MODELS


class ChunkMode(str, Enum):
    SINGLE = "single"
    SENTENCE = "sentence"


class OutputFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"


class VoiceSource(str, Enum):
    REFERENCE = "reference"
    BUILTIN = "builtin"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerCapability(str, Enum):
    SYNTHESIZE = "synthesize"


class PauseConfig(BaseModel):
    strategy: str = "random_uniform_with_length_adjustment"
    min_seconds: float = Field(default=0.45, gt=0)
    max_seconds: float = Field(default=1.10, gt=0)
    seed: int | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "PauseConfig":
        if self.max_seconds < self.min_seconds:
            raise ValueError("pause_config.max_seconds must be >= min_seconds")
        return self


class ProjectCreateRequest(BaseModel):
    project_id: str = Field(min_length=2)
    course: str | None = None
    module: str | None = None
    lesson: str | None = None


class TranscribeRequest(BaseModel):
    project_id: str = Field(min_length=2)
    audio_path: Path
    name: str | None = None
    model: str = "small"
    language: str | None = None
    beam_size: int = Field(default=5, ge=1, le=10)


class ClipRequest(BaseModel):
    project_id: str = Field(min_length=2)
    audio_path: Path
    segments_json_path: Path
    output_name: str = Field(min_length=2)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, gt=0)
    start_phrase: str | None = None
    end_phrase: str | None = None
    verification_mode: Literal["strict", "lenient"] = "strict"
    output_format: OutputFormat = OutputFormat.MP3

    @model_validator(mode="after")
    def validate_boundaries(self) -> "ClipRequest":
        if self.start_time is None and not self.start_phrase:
            raise ValueError("provide start_time or start_phrase")
        if self.end_time is None and not self.end_phrase:
            raise ValueError("provide end_time or end_phrase")
        if self.start_time is not None and self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class SynthesisRequest(BaseModel):
    project_id: str = Field(min_length=2)
    text: str = Field(min_length=1)
    voice_source: VoiceSource = VoiceSource.REFERENCE
    reference_audio_path: Path | None = None
    reference_text: str | None = None
    model_id: str = SUPPORTED_BASE_MODELS[1]
    built_in_speaker: str | None = None
    built_in_instruct: str | None = None
    max_new_tokens: int = Field(default=1200, ge=64, le=8192)
    chunk_mode: ChunkMode = ChunkMode.SENTENCE
    pause_config: PauseConfig = Field(default_factory=PauseConfig)
    output_format: OutputFormat = OutputFormat.MP3
    output_name: str = "synthesized_output"
    generate_transcript: bool = True
    voice_clone_authorized: bool = False

    @model_validator(mode="after")
    def validate_model(self) -> "SynthesisRequest":
        if self.model_id not in SUPPORTED_TTS_MODELS:
            raise ValueError(
                f"Unsupported model_id: {self.model_id}. Supported: {', '.join(SUPPORTED_TTS_MODELS)}"
            )
        if self.voice_source == VoiceSource.REFERENCE:
            if self.reference_audio_path is None:
                raise ValueError("reference_audio_path is required for reference voice synthesis")
            if self.model_id not in SUPPORTED_BASE_MODELS:
                raise ValueError("reference voice synthesis requires a Base model")
            if not self.voice_clone_authorized:
                raise ValueError("voice_clone_authorized must be true before synthesis")
        else:
            if not self.built_in_speaker:
                raise ValueError("built_in_speaker is required for builtin voice synthesis")
            if self.model_id not in SUPPORTED_CUSTOM_MODELS:
                raise ValueError("builtin voice synthesis requires a CustomVoice model")
        return self


class WorkerSynthesisEnqueueRequest(BaseModel):
    project_id: str = Field(min_length=2)
    text: str = Field(min_length=1)
    voice_source: VoiceSource = VoiceSource.REFERENCE
    reference_audio_b64: str | None = None
    reference_audio_filename: str | None = None
    reference_text: str | None = None
    model_id: str = SUPPORTED_BASE_MODELS[1]
    built_in_speaker: str | None = None
    built_in_instruct: str | None = None
    max_new_tokens: int = Field(default=1200, ge=64, le=8192)
    chunk_mode: ChunkMode = ChunkMode.SENTENCE
    pause_config: PauseConfig = Field(default_factory=PauseConfig)
    output_format: OutputFormat = OutputFormat.MP3
    output_name: str = "synthesized_output"
    generate_transcript: bool = True
    voice_clone_authorized: bool = False

    @model_validator(mode="after")
    def validate_model(self) -> "WorkerSynthesisEnqueueRequest":
        if self.model_id not in SUPPORTED_TTS_MODELS:
            raise ValueError(
                f"Unsupported model_id: {self.model_id}. Supported: {', '.join(SUPPORTED_TTS_MODELS)}"
            )
        if self.voice_source == VoiceSource.REFERENCE:
            if not self.reference_audio_b64 or not self.reference_audio_filename:
                raise ValueError("reference_audio_b64 and reference_audio_filename are required for reference voice synthesis")
            if self.model_id not in SUPPORTED_BASE_MODELS:
                raise ValueError("reference voice synthesis requires a Base model")
            if not self.voice_clone_authorized:
                raise ValueError("voice_clone_authorized must be true before synthesis")
        else:
            if not self.built_in_speaker:
                raise ValueError("built_in_speaker is required for builtin voice synthesis")
            if self.model_id not in SUPPORTED_CUSTOM_MODELS:
                raise ValueError("builtin voice synthesis requires a CustomVoice model")
        return self


class SimpleSynthesisRequest(BaseModel):
    project_id: str = Field(min_length=2)
    text: str = Field(min_length=1)
    voice_source: VoiceSource = VoiceSource.REFERENCE
    reference_audio_b64: str | None = None
    reference_audio_filename: str | None = None
    reference_audio_hash: str | None = Field(default=None, min_length=16)
    built_in_speaker: str | None = None
    built_in_instruct: str | None = None
    output_name: str | None = None
    quality: Literal["normal", "high"] = "normal"
    add_ums: bool = False
    add_ahs: bool = False
    add_fillers: bool = False
    average_gap_seconds: float = Field(default=0.8, ge=0.15, le=2.5)
    generate_transcript: bool = False
    output_format: OutputFormat = OutputFormat.MP3
    voice_clone_authorized: bool = False

    @model_validator(mode="after")
    def validate_authorization(self) -> "SimpleSynthesisRequest":
        if self.voice_source == VoiceSource.REFERENCE:
            has_uploaded_reference = bool(self.reference_audio_b64 and self.reference_audio_filename)
            has_library_reference = bool(self.reference_audio_hash)
            if not has_uploaded_reference and not has_library_reference:
                raise ValueError("Provide either reference_audio_b64+reference_audio_filename or reference_audio_hash")
            if self.reference_audio_b64 and not self.reference_audio_filename:
                raise ValueError("reference_audio_filename is required when reference_audio_b64 is provided")
            if not self.voice_clone_authorized:
                raise ValueError("voice_clone_authorized must be true before synthesis")
        else:
            supported_speakers = {row["id"].lower() for row in QWEN_CUSTOM_VOICE_SPEAKERS}
            if not self.built_in_speaker:
                raise ValueError("built_in_speaker is required for builtin voice synthesis")
            if str(self.built_in_speaker).lower() not in supported_speakers:
                raise ValueError("Unsupported built_in_speaker")
        return self


class ProjectReferenceAudioUploadRequest(BaseModel):
    filename: str = Field(min_length=1)
    audio_b64: str = Field(min_length=32)


class ProjectReferenceAudioDeleteRequest(BaseModel):
    audio_hash: str = Field(min_length=16, max_length=128)
    source_project_id: str | None = Field(default=None, min_length=2, max_length=128)


class ProjectScriptSaveRequest(BaseModel):
    text: str = ""
    source: str = Field(default="autosave", min_length=2, max_length=32)


class ProjectScriptRestoreRequest(BaseModel):
    version_id: str = Field(min_length=4, max_length=64)


class ProjectScriptDeleteRequest(BaseModel):
    version_id: str = Field(min_length=4, max_length=64)


class ProjectAccessGrantRequest(BaseModel):
    email: str = Field(min_length=3)


class ProjectAccessRevokeRequest(BaseModel):
    email: str = Field(min_length=3)


class CaptionRequest(BaseModel):
    project_id: str = Field(min_length=2)
    audio_path: Path
    name: str | None = None
    model: str = "small"
    language: str | None = None


class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float
    probability: float | None = None


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    confidence: float | None = None
    words: list[TranscriptWord] = Field(default_factory=list)


class TranscriptArtifacts(BaseModel):
    segments_json_path: Path
    txt_path: Path
    srt_path: Path


class CaptionArtifacts(BaseModel):
    txt_path: Path
    srt_path: Path
    vtt_path: Path


class BoundaryReport(BaseModel):
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    start_segment_id: int | None = None
    end_segment_id: int | None = None
    start_segment_text: str | None = None
    end_segment_text: str | None = None
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)


class QualityReport(BaseModel):
    speech_rate_wpm: float
    pause_stats: dict[str, float]
    warnings: list[str] = Field(default_factory=list)


class OutputMetadata(BaseModel):
    output_file: Path
    duration_seconds: float
    model: str
    reference_audio: Path | None = None
    reference_text: str | None = None
    voice_source: VoiceSource = VoiceSource.REFERENCE
    built_in_speaker: str | None = None
    input_text: str
    chunk_mode: ChunkMode
    pause_seconds: list[float]
    max_new_tokens: int
    output_format: OutputFormat
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    seed: int | None = None
    project_id: str
    job_id: str
    captions: dict[str, Path] | None = None
    quality: QualityReport | None = None
    stage_durations_seconds: dict[str, float] = Field(default_factory=dict)


class JobRecord(BaseModel):
    id: str
    project_id: str
    status: JobStatus
    stage: str
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    logs: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)


class WorkerInviteResponse(BaseModel):
    invite_token: str
    expires_in_seconds: int
    install_command: str
    install_command_windows: str | None = None
    install_command_macos: str | None = None
    install_command_linux: str | None = None
    windows_installer_url: str | None = None
    macos_installer_url: str | None = None


class WorkerInviteRequest(BaseModel):
    capabilities: list[WorkerCapability] = Field(default_factory=lambda: [WorkerCapability.SYNTHESIZE])


class WorkerRegisterRequest(BaseModel):
    invite_token: str = Field(min_length=10)
    worker_name: str = Field(min_length=2)
    capabilities: list[WorkerCapability] = Field(default_factory=lambda: [WorkerCapability.SYNTHESIZE])


class WorkerRegisterResponse(BaseModel):
    worker_id: str
    api_key: str
    poll_interval_seconds: int = 5


class WorkerPullRequest(BaseModel):
    worker_id: str
    api_key: str


class WorkerQueuedJob(BaseModel):
    job_id: str
    project_id: str
    type: Literal["synthesize"]
    payload: dict[str, Any]


class WorkerPullResponse(BaseModel):
    job: WorkerQueuedJob | None = None


class WorkerJobCompleteRequest(BaseModel):
    worker_id: str
    api_key: str
    output_audio_b64: str = Field(min_length=32)
    output_format: OutputFormat
    duration_seconds: float = Field(gt=0)
    reference_text: str
    pause_seconds: list[float] = Field(default_factory=list)
    captions_txt: str | None = None
    captions_srt: str | None = None
    captions_vtt: str | None = None
    quality: dict[str, Any] | None = None
    stage_durations_seconds: dict[str, float] = Field(default_factory=dict)


class WorkerJobProgressRequest(BaseModel):
    worker_id: str
    api_key: str
    progress: float = Field(ge=0.0, le=1.0)
    stage: str | None = None
    detail: str | None = None


class WorkerJobFailRequest(BaseModel):
    worker_id: str
    api_key: str
    error: str = Field(min_length=1)


class WorkerSummary(BaseModel):
    worker_id: str
    worker_name: str
    capabilities: list[WorkerCapability]
    status: str
    last_seen_at: str | None = None
    created_at: str


class BuiltInVoicePreviewRequest(BaseModel):
    speaker: str = Field(min_length=2)
    quality: Literal["normal", "high"] = "normal"
    text: str | None = None


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
