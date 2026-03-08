from __future__ import annotations

import base64
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from radtts.api import app, worker_manager


def _b64_blob(byte: int, length: int = 64) -> str:
    return base64.b64encode(bytes([byte]) * length).decode("utf-8")


def test_worker_queue_round_trip_completes_job():
    client = TestClient(app)
    project_id = f"worker-smoke-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        create = client.post(
            "/projects",
            json={"project_id": project_id, "course": "C1", "module": "M1", "lesson": "L1"},
        )
        assert create.status_code == 200

        invite = client.post("/workers/invite", json={"capabilities": ["synthesize"]})
        assert invite.status_code == 200
        invite_token = invite.json()["invite_token"]

        register = client.post(
            "/workers/register",
            json={
                "invite_token": invite_token,
                "worker_name": "test-worker",
                "capabilities": ["synthesize"],
            },
        )
        assert register.status_code == 200
        worker_id = register.json()["worker_id"]
        api_key = register.json()["api_key"]

        enqueue = client.post(
            "/synthesize/worker",
            json={
                "project_id": project_id,
                "text": "Hello from worker queue.",
                "reference_audio_b64": _b64_blob(1),
                "reference_audio_filename": "reference.wav",
                "reference_text": "hello",
                "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                "max_new_tokens": 300,
                "chunk_mode": "single",
                "pause_config": {"min_seconds": 0.2, "max_seconds": 0.4, "seed": 1},
                "output_format": "wav",
                "output_name": "worker_output",
                "voice_clone_authorized": True,
            },
        )
        assert enqueue.status_code == 200
        job_id = enqueue.json()["job_id"]

        pull = client.post("/workers/pull", json={"worker_id": worker_id, "api_key": api_key})
        assert pull.status_code == 200
        pulled_job = pull.json()["job"]
        assert pulled_job is not None
        assert pulled_job["job_id"] == job_id

        progress = client.post(
            f"/workers/jobs/{job_id}/progress",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "progress": 0.58,
                "stage": "generation",
                "detail": "generation chunk 2/4",
            },
        )
        assert progress.status_code == 200
        assert progress.json()["progress"] == 0.58

        job_running = client.get(f"/jobs/{job_id}?project_id={project_id}")
        assert job_running.status_code == 200
        running_payload = job_running.json()
        assert running_payload["status"] == "running"
        assert running_payload["stage"] == "generation"
        assert running_payload["progress"] == 0.58
        assert any("generation chunk 2/4" in line for line in running_payload["logs"])

        stale_progress = client.post(
            f"/workers/jobs/{job_id}/progress",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "progress": 0.41,
                "detail": "stale progress sample",
            },
        )
        assert stale_progress.status_code == 200

        job_after_stale = client.get(f"/jobs/{job_id}?project_id={project_id}")
        assert job_after_stale.status_code == 200
        assert job_after_stale.json()["progress"] == 0.58

        complete = client.post(
            f"/workers/jobs/{job_id}/complete",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "output_audio_b64": _b64_blob(2),
                "output_format": "wav",
                "duration_seconds": 4.2,
                "reference_text": "hello",
                "pause_seconds": [0.3],
                "captions_txt": "hello",
                "captions_srt": "1\n00:00:00,000 --> 00:00:01,000\nhello\n",
                "captions_vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello\n",
            },
        )
        assert complete.status_code == 200

        job = client.get(f"/jobs/{job_id}?project_id={project_id}")
        assert job.status_code == 200
        payload = job.json()
        assert payload["status"] == "completed"
        assert payload["stage"] == "completed"
        assert Path(payload["outputs"]["audio_path"]).exists()
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_stale_worker_updates_are_ignored_after_project_job_cancel():
    client = TestClient(app)
    project_id = f"worker-stale-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        create = client.post(
            "/projects",
            json={"project_id": project_id, "course": "C1", "module": "M1", "lesson": "L1"},
        )
        assert create.status_code == 200

        invite = client.post("/workers/invite", json={"capabilities": ["synthesize"]})
        assert invite.status_code == 200
        invite_token = invite.json()["invite_token"]

        register = client.post(
            "/workers/register",
            json={
                "invite_token": invite_token,
                "worker_name": "test-worker",
                "capabilities": ["synthesize"],
            },
        )
        assert register.status_code == 200
        worker_id = register.json()["worker_id"]
        api_key = register.json()["api_key"]

        enqueue = client.post(
            "/synthesize/worker",
            json={
                "project_id": project_id,
                "text": "Hello from worker queue.",
                "reference_audio_b64": _b64_blob(3),
                "reference_audio_filename": "reference.wav",
                "reference_text": "hello",
                "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                "max_new_tokens": 300,
                "chunk_mode": "single",
                "pause_config": {"min_seconds": 0.2, "max_seconds": 0.4, "seed": 1},
                "output_format": "wav",
                "output_name": "worker_stale_output",
                "voice_clone_authorized": True,
            },
        )
        assert enqueue.status_code == 200
        job_id = enqueue.json()["job_id"]

        pull = client.post("/workers/pull", json={"worker_id": worker_id, "api_key": api_key})
        assert pull.status_code == 200
        assert pull.json()["job"]["job_id"] == job_id

        worker_manager.cancel_project_jobs(project_id, reason="superseded by a newer request")

        progress = client.post(
            f"/workers/jobs/{job_id}/progress",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "progress": 0.41,
                "stage": "generation",
                "detail": "late progress update",
            },
        )
        assert progress.status_code == 200
        assert progress.json()["status"] == "ignored"

        complete = client.post(
            f"/workers/jobs/{job_id}/complete",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "output_audio_b64": _b64_blob(4),
                "output_format": "wav",
                "duration_seconds": 4.2,
                "reference_text": "hello",
                "pause_seconds": [0.3],
            },
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "ignored"

        fail = client.post(
            f"/workers/jobs/{job_id}/fail",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "error": "late failure update",
            },
        )
        assert fail.status_code == 200
        assert fail.json()["status"] == "ignored"

        job = client.get(f"/jobs/{job_id}?project_id={project_id}")
        assert job.status_code == 200
        payload = job.json()
        assert payload["status"] == "cancelled"
        assert payload["error"] == "superseded by a newer request"
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_queue_fallback_does_not_claim_job_after_worker_accepts():
    client = TestClient(app)
    project_id = f"worker-accept-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        create = client.post(
            "/projects",
            json={"project_id": project_id, "course": "C1", "module": "M1", "lesson": "L1"},
        )
        assert create.status_code == 200

        invite = client.post("/workers/invite", json={"capabilities": ["synthesize"]})
        assert invite.status_code == 200
        invite_token = invite.json()["invite_token"]

        register = client.post(
            "/workers/register",
            json={
                "invite_token": invite_token,
                "worker_name": "test-worker",
                "capabilities": ["synthesize"],
            },
        )
        assert register.status_code == 200
        worker_id = register.json()["worker_id"]
        api_key = register.json()["api_key"]

        enqueue = client.post(
            "/synthesize/worker",
            json={
                "project_id": project_id,
                "text": "Hello from worker queue.",
                "reference_audio_b64": _b64_blob(5),
                "reference_audio_filename": "reference.wav",
                "reference_text": "hello",
                "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                "max_new_tokens": 300,
                "chunk_mode": "single",
                "pause_config": {"min_seconds": 0.2, "max_seconds": 0.4, "seed": 1},
                "output_format": "wav",
                "output_name": "worker_accept_output",
                "voice_clone_authorized": True,
            },
        )
        assert enqueue.status_code == 200
        job_id = enqueue.json()["job_id"]

        pull = client.post("/workers/pull", json={"worker_id": worker_id, "api_key": api_key})
        assert pull.status_code == 200
        assert pull.json()["job"]["job_id"] == job_id

        fallback_claim = worker_manager.claim_job_for_local_fallback(
            job_id,
            reason="No worker accepted this job after 40s. Switching to local server fallback.",
            allowed_statuses={"queued"},
        )
        assert fallback_claim is None

        progress = client.post(
            f"/workers/jobs/{job_id}/progress",
            json={
                "worker_id": worker_id,
                "api_key": api_key,
                "progress": 0.3,
                "stage": "model_load",
                "detail": "tts model=Qwen/Qwen3-TTS-12Hz-0.6B-Base runtime device=mps:0 dtype=torch.float32",
            },
        )
        assert progress.status_code == 200
        assert progress.json()["status"] == "running"

        job = client.get(f"/jobs/{job_id}?project_id={project_id}")
        assert job.status_code == 200
        payload = job.json()
        assert payload["status"] == "running"
        assert payload["stage"] == "model_load"
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)
