from __future__ import annotations

from pathlib import Path

import pytest

from radtts.constants import SUPPORTED_BASE_MODELS
from radtts.manifests import ManifestStore
from radtts.models import OutputFormat, PauseConfig, QualityReport, SynthesisRequest
from radtts.orchestrator import PipelineOrchestrator


def test_orchestrator_tracks_chunk_and_stitching_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    orchestrator = PipelineOrchestrator(projects_root=tmp_path, heartbeat_seconds=3600)
    project_id = "proj-progress"
    job_id = "job_progress"
    reference_audio = tmp_path / "reference.wav"
    reference_audio.write_bytes(b"RIFF")

    req = SynthesisRequest(
        project_id=project_id,
        text="One. Two. Three.",
        reference_audio_path=reference_audio,
        model_id=SUPPORTED_BASE_MODELS[0],
        pause_config=PauseConfig(seed=7),
        output_format=OutputFormat.MP3,
        output_name="progress-check",
        generate_transcript=False,
        voice_clone_authorized=True,
    )

    paths = orchestrator.project_manager.create_project(project_id)
    store = ManifestStore(paths.manifests)
    snapshots: list[tuple[str, str, float]] = []

    monkeypatch.setattr(orchestrator.tts_service, "ensure_supported_model", lambda model_id: None)
    monkeypatch.setattr(orchestrator.tts_service, "_load_model", lambda model_id: object())
    monkeypatch.setattr(
        orchestrator.quality_service,
        "evaluate",
        lambda **_: QualityReport(
            speech_rate_wpm=120.0,
            pause_stats={"min": 0.4, "max": 0.5, "mean": 0.45, "stddev": 0.05},
            warnings=[],
        ),
    )
    monkeypatch.setattr("radtts.orchestrator.probe_duration_seconds", lambda path: 6.0)

    def fake_synthesize(req_obj, output_dir, *, on_progress=None, cancel_check=None):
        output_path = output_dir / f"{req_obj.output_name}.mp3"
        output_path.write_bytes(b"ID3")
        for message in [
            "generation chunk 1/3",
            "generation chunk 2/3",
            "generation chunk 3/3",
            "stitching chunks",
            "stitching encoding mp3",
        ]:
            assert on_progress is not None
            on_progress(message)
            snapshot = store.get_job(job_id)
            assert snapshot is not None
            snapshots.append((message, snapshot["stage"], snapshot["progress"]))
        return output_path, [0.4, 0.5], "Reference text"

    monkeypatch.setattr(orchestrator.tts_service, "synthesize", fake_synthesize)

    job = orchestrator.run_synthesis_job(req, job_id=job_id)

    assert snapshots == [
        ("generation chunk 1/3", "generation", pytest.approx(0.4733, rel=0, abs=1e-4)),
        ("generation chunk 2/3", "generation", pytest.approx(0.5967, rel=0, abs=1e-4)),
        ("generation chunk 3/3", "generation", pytest.approx(0.72, rel=0, abs=1e-4)),
        ("stitching chunks", "stitching", pytest.approx(0.78, rel=0, abs=1e-4)),
        ("stitching encoding mp3", "stitching", pytest.approx(0.84, rel=0, abs=1e-4)),
    ]
    assert job.status.value == "completed"
    assert job.progress == 1.0
