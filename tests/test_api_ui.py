from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from radtts.api import app


def test_ui_homepage_renders():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "RADTTS Studio" in response.text
    assert "Create Project" in response.text


def test_project_outputs_endpoint_returns_empty_list_for_new_project():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        outputs = client.get(f"/projects/{project_id}/outputs")
        assert outputs.status_code == 200
        payload = outputs.json()
        assert payload["project_id"] == project_id
        assert payload["outputs"] == []
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_simple_synthesize_requires_voice_clone_authorization():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        response = client.post(
            "/synthesize/simple",
            json={
                "project_id": project_id,
                "text": "Hello world.",
                "reference_audio_b64": "QUJDREVGR0g=" * 4,
                "reference_audio_filename": "reference.wav",
                "quality": "normal",
                "add_fillers": False,
                "average_gap_seconds": 0.8,
                "output_format": "mp3",
                "voice_clone_authorized": False,
            },
        )
        assert response.status_code == 422
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)
