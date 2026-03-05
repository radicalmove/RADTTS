"""RADTTS command line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from radtts.constants import MODEL_MODE_ALIASES
from radtts.models import (
    CaptionRequest,
    ChunkMode,
    ClipRequest,
    PauseConfig,
    ProjectCreateRequest,
    SynthesisRequest,
    TranscribeRequest,
)
from radtts.pipeline import RADTTSPipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RADTTS: local-first voice synthesis pipeline")
    parser.add_argument("--projects-root", default="projects", help="Projects root directory")

    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create-project", help="Create a project scaffold")
    p_create.add_argument("--project-id", required=True)
    p_create.add_argument("--course")
    p_create.add_argument("--module")
    p_create.add_argument("--lesson")

    p_transcribe = sub.add_parser("transcribe", help="Transcribe audio into txt/srt/segments")
    p_transcribe.add_argument("--project-id", required=True)
    p_transcribe.add_argument("--audio-path", required=True)
    p_transcribe.add_argument("--name")
    p_transcribe.add_argument("--model", default="small")
    p_transcribe.add_argument("--language")
    p_transcribe.add_argument("--beam-size", type=int, default=5)

    p_clip = sub.add_parser("clip", help="Extract transcript-verified clip")
    p_clip.add_argument("--project-id", required=True)
    p_clip.add_argument("--audio-path", required=True)
    p_clip.add_argument("--segments-json", required=True)
    p_clip.add_argument("--output-name", required=True)
    p_clip.add_argument("--start-time", type=float)
    p_clip.add_argument("--end-time", type=float)
    p_clip.add_argument("--start-phrase")
    p_clip.add_argument("--end-phrase")
    p_clip.add_argument("--verification-mode", choices=["strict", "lenient"], default="strict")
    p_clip.add_argument("--output-format", choices=["wav", "mp3"], default="mp3")

    p_synth = sub.add_parser("synthesize", help="Run voice clone synthesis")
    p_synth.add_argument("--project-id", required=True)
    group = p_synth.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--text-file")
    p_synth.add_argument("--reference-audio", required=True)
    p_synth.add_argument("--reference-text")
    p_synth.add_argument("--reference-text-file")
    p_synth.add_argument("--mode", choices=["fast", "quality"], default="quality")
    p_synth.add_argument("--model-id")
    p_synth.add_argument("--max-new-tokens", type=int, default=1200)
    p_synth.add_argument("--chunk-mode", choices=["single", "sentence"], default="sentence")
    p_synth.add_argument("--pause-min", type=float, default=0.45)
    p_synth.add_argument("--pause-max", type=float, default=1.10)
    p_synth.add_argument("--pause-seed", type=int)
    p_synth.add_argument("--output-format", choices=["wav", "mp3"], default="mp3")
    p_synth.add_argument("--output-name", required=True)
    p_synth.add_argument(
        "--ack-voice-clone",
        action="store_true",
        help="Required authorization acknowledgment for voice cloning",
    )

    p_caps = sub.add_parser("captions", help="Generate txt/srt/vtt captions")
    p_caps.add_argument("--project-id", required=True)
    p_caps.add_argument("--audio-path", required=True)
    p_caps.add_argument("--name")
    p_caps.add_argument("--model", default="small")
    p_caps.add_argument("--language")

    p_job = sub.add_parser("job", help="Inspect or cancel a job")
    p_job.add_argument("--project-id", required=True)
    p_job.add_argument("--job-id", required=True)
    p_job.add_argument("--cancel", action="store_true")

    return parser


def _load_text(text: str | None, text_file: str | None) -> str:
    if text is not None:
        return text
    if text_file is None:
        return ""
    return Path(text_file).read_text(encoding="utf-8")


def _resolve_reference_text(reference_text: str | None, reference_text_file: str | None) -> str | None:
    if reference_text:
        return reference_text
    if reference_text_file:
        return Path(reference_text_file).read_text(encoding="utf-8")
    return None


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    pipeline = RADTTSPipeline(projects_root=Path(args.projects_root))

    try:
        if args.command == "create-project":
            result = pipeline.create_project(
                ProjectCreateRequest(
                    project_id=args.project_id,
                    course=args.course,
                    module=args.module,
                    lesson=args.lesson,
                )
            )
        elif args.command == "transcribe":
            result = pipeline.transcribe(
                TranscribeRequest(
                    project_id=args.project_id,
                    audio_path=Path(args.audio_path),
                    name=args.name,
                    model=args.model,
                    language=args.language,
                    beam_size=args.beam_size,
                )
            )
        elif args.command == "clip":
            result = pipeline.clip(
                ClipRequest(
                    project_id=args.project_id,
                    audio_path=Path(args.audio_path),
                    segments_json_path=Path(args.segments_json),
                    output_name=args.output_name,
                    start_time=args.start_time,
                    end_time=args.end_time,
                    start_phrase=args.start_phrase,
                    end_phrase=args.end_phrase,
                    verification_mode=args.verification_mode,
                    output_format=args.output_format,
                )
            )
        elif args.command == "synthesize":
            text = _load_text(args.text, args.text_file)
            reference_text = _resolve_reference_text(args.reference_text, args.reference_text_file)
            model_id = args.model_id or MODEL_MODE_ALIASES[args.mode]
            result = pipeline.synthesize(
                SynthesisRequest(
                    project_id=args.project_id,
                    text=text,
                    reference_audio_path=Path(args.reference_audio),
                    reference_text=reference_text,
                    model_id=model_id,
                    max_new_tokens=args.max_new_tokens,
                    chunk_mode=ChunkMode(args.chunk_mode),
                    pause_config=PauseConfig(
                        min_seconds=args.pause_min,
                        max_seconds=args.pause_max,
                        seed=args.pause_seed,
                    ),
                    output_format=args.output_format,
                    output_name=args.output_name,
                    voice_clone_authorized=args.ack_voice_clone,
                )
            )
        elif args.command == "captions":
            result = pipeline.captions(
                CaptionRequest(
                    project_id=args.project_id,
                    audio_path=Path(args.audio_path),
                    name=args.name,
                    model=args.model,
                    language=args.language,
                )
            )
        elif args.command == "job":
            if args.cancel:
                result = pipeline.cancel_job(args.project_id, args.job_id)
            else:
                result = pipeline.get_job(args.project_id, args.job_id)
                if result is None:
                    raise SystemExit(f"Job not found: {args.job_id}")
        else:
            raise SystemExit(f"Unknown command: {args.command}")

        print(json.dumps(result, indent=2, default=str))

    except PydanticValidationError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
