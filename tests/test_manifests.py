from __future__ import annotations

from pathlib import Path

from radtts.constants import SUPPORTED_BASE_MODELS
from radtts.manifests import ManifestStore
from radtts.models import ChunkMode, JobRecord, JobStatus, OutputFormat, OutputMetadata


def test_manifest_store_writes_jobs_and_outputs(tmp_path: Path):
    store = ManifestStore(tmp_path)

    job = JobRecord(id="job_1", project_id="proj", status=JobStatus.RUNNING, stage="generation", progress=0.4)
    store.upsert_job(job)

    metadata = OutputMetadata(
        output_file=tmp_path / "out.mp3",
        duration_seconds=6.2,
        model=SUPPORTED_BASE_MODELS[0],
        audio_tuning_label="Version 4",
        reference_audio=tmp_path / "ref.mp3",
        reference_text="ref",
        input_text="text",
        chunk_mode=ChunkMode.SINGLE,
        pause_seconds=[],
        max_new_tokens=400,
        output_format=OutputFormat.MP3,
        project_id="proj",
        job_id="job_1",
    )
    store.append_output(metadata)

    jobs = store.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["id"] == "job_1"

    outputs = store._read(store.outputs_file)  # noqa: SLF001
    assert len(outputs) == 1
    assert outputs[0]["job_id"] == "job_1"
    assert outputs[0]["audio_tuning_label"] == "Version 4"
