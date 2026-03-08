from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer

from radtts.api import app


def _bridge_user(client: TestClient, *, sub: int, email: str, display_name: str) -> None:
    serializer = URLSafeTimedSerializer("radtts-dev-session-secret", salt="app-bridge-radtts-v1")
    token = serializer.dumps(
        {
            "sub": sub,
            "email": email,
            "display_name": display_name,
            "is_admin": False,
            "issuer": "psychek",
        }
    )
    response = client.get(f"/auth/bridge?token={token}", follow_redirects=False)
    assert response.status_code == 302


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


def test_worker_invite_includes_cross_platform_setup_commands():
    client = TestClient(app)
    response = client.post("/workers/invite", json={"capabilities": ["synthesize"]})
    assert response.status_code == 200
    payload = response.json()
    token = payload["invite_token"]

    assert "install_command" in payload
    assert "radtts-worker-install" in payload["install_command"]
    assert token in payload["install_command"]

    assert "install_command_windows" in payload
    assert "py -m radtts.worker_setup" in payload["install_command_windows"]
    assert token in payload["install_command_windows"]

    assert "install_command_macos" in payload
    assert "python3 -m radtts.worker_setup" in payload["install_command_macos"]
    assert token in payload["install_command_macos"]

    assert "install_command_linux" in payload
    assert "python3 -m radtts.worker_setup" in payload["install_command_linux"]
    assert token in payload["install_command_linux"]
    assert payload["windows_installer_url"].startswith("http://testserver/workers/bootstrap/windows.cmd?")
    assert payload["macos_installer_url"].startswith("http://testserver/workers/bootstrap/macos.command?")


def test_workers_status_endpoint_returns_counts():
    client = TestClient(app)
    response = client.get("/workers/status")
    assert response.status_code == 200
    payload = response.json()
    assert "worker_total_count" in payload
    assert "worker_online_count" in payload
    assert "worker_live_count" in payload
    assert "worker_registered_count" in payload
    assert "worker_stale_count" in payload
    assert "worker_last_live_seen_at" in payload
    assert "worker_online_window_seconds" in payload


def test_windows_worker_bootstrap_cmd_download():
    client = TestClient(app)
    invite = client.post("/workers/invite", json={"capabilities": ["synthesize"]})
    assert invite.status_code == 200
    token = invite.json()["invite_token"]

    download = client.get(f"/workers/bootstrap/windows.cmd?invite_token={token}")
    assert download.status_code == 200
    assert "radtts.worker_setup" in download.text
    assert token in download.text
    disposition = download.headers.get("content-disposition", "")
    assert "radtts-worker-setup.cmd" in disposition


def test_macos_worker_bootstrap_command_download():
    client = TestClient(app)
    invite = client.post("/workers/invite", json={"capabilities": ["synthesize"]})
    assert invite.status_code == 200
    token = invite.json()["invite_token"]

    download = client.get(f"/workers/bootstrap/macos.command?invite_token={token}")
    assert download.status_code == 200
    assert "radtts.worker_setup" in download.text
    assert token in download.text
    disposition = download.headers.get("content-disposition", "")
    assert "radtts-worker-setup.command" in disposition


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


def test_simple_synthesize_queues_worker_by_default_and_cancel_works():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        queued = client.post(
            "/synthesize/simple",
            json={
                "project_id": project_id,
                "text": "Hello worker default.",
                "reference_audio_b64": "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
                "reference_audio_filename": "reference.wav",
                "quality": "normal",
                "add_fillers": False,
                "average_gap_seconds": 0.8,
                "output_format": "mp3",
                "voice_clone_authorized": True,
            },
        )
        assert queued.status_code == 200
        payload = queued.json()
        assert payload["worker_mode"] is True
        assert payload["stage"] == "queued_remote"

        job_id = payload["job_id"]
        cancelled = client.post(f"/jobs/{job_id}/cancel?project_id={project_id}")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        job = client.get(f"/jobs/{job_id}?project_id={project_id}")
        assert job.status_code == 200
        assert job.json()["status"] == "cancelled"
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_project_reference_audio_upload_persists_file():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        response = client.post(
            f"/projects/{project_id}/reference-audio",
            json={
                "filename": "voice-sample.wav",
                "audio_b64": "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_id"] == project_id
        assert len(payload["audio_hash"]) == 64
        assert payload["filename"].startswith("reference-")
        assert payload["saved_path"].endswith(".wav")
        assert Path(payload["saved_path"]).exists()
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_project_reference_audio_upload_reuses_same_file_for_same_audio():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id
    sample_b64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw"

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        first = client.post(
            f"/projects/{project_id}/reference-audio",
            json={"filename": "voice-a.wav", "audio_b64": sample_b64},
        )
        second = client.post(
            f"/projects/{project_id}/reference-audio",
            json={"filename": "voice-b.wav", "audio_b64": sample_b64},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        first_payload = first.json()
        second_payload = second.json()
        assert first_payload["audio_hash"] == second_payload["audio_hash"]
        assert first_payload["saved_path"] == second_payload["saved_path"]
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_project_reference_audio_list_returns_saved_samples():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id
    sample_b64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw"

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        uploaded = client.post(
            f"/projects/{project_id}/reference-audio",
            json={"filename": "voice-a.wav", "audio_b64": sample_b64},
        )
        assert uploaded.status_code == 200
        uploaded_payload = uploaded.json()

        listed = client.get(f"/projects/{project_id}/reference-audio")
        assert listed.status_code == 200
        payload = listed.json()
        assert payload["project_id"] == project_id
        assert len(payload["samples"]) == 1
        sample = payload["samples"][0]
        assert sample["audio_hash"] == uploaded_payload["audio_hash"]
        assert sample["source_filename"] == "voice-a.wav"
        assert sample["saved_path"] == uploaded_payload["saved_path"]
        assert sample["artifact_url"].startswith(f"/projects/{project_id}/artifact?path=")
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_reference_audio_list_includes_current_user_samples_from_other_projects():
    client = TestClient(app)
    _bridge_user(client, sub=301, email="voice-owner@example.com", display_name="Voice Owner")

    project_a = f"ui-a-{uuid.uuid4().hex[:6]}"
    project_b = f"ui-b-{uuid.uuid4().hex[:6]}"
    created_roots: list[Path] = []
    sample_b64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw"

    try:
        created_a = client.post("/projects", json={"project_id": project_a})
        created_b = client.post("/projects", json={"project_id": project_b})
        assert created_a.status_code == 200
        assert created_b.status_code == 200
        created_roots.append(Path(created_a.json()["project_root"]))
        created_roots.append(Path(created_b.json()["project_root"]))

        uploaded = client.post(
            f"/projects/{project_a}/reference-audio",
            json={"filename": "voice-a.wav", "audio_b64": sample_b64},
        )
        assert uploaded.status_code == 200
        audio_hash = uploaded.json()["audio_hash"]

        listed = client.get(f"/projects/{project_b}/reference-audio")
        assert listed.status_code == 200
        samples = listed.json()["samples"]
        target = next((row for row in samples if row["audio_hash"] == audio_hash), None)
        assert target is not None
        assert target["scope"] == "library"
        assert target["project_id"] == project_a
    finally:
        for root in created_roots:
            if root.exists():
                shutil.rmtree(root)


def test_reference_audio_library_does_not_leak_other_users_samples():
    owner_client = TestClient(app)
    other_client = TestClient(app)
    _bridge_user(owner_client, sub=401, email="owner@example.com", display_name="Owner")
    _bridge_user(other_client, sub=402, email="other@example.com", display_name="Other")

    owner_project_a = f"owner-a-{uuid.uuid4().hex[:6]}"
    owner_project_b = f"owner-b-{uuid.uuid4().hex[:6]}"
    other_project = f"other-{uuid.uuid4().hex[:6]}"
    created_roots: list[Path] = []
    owner_b64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVoxMjM0NTY3ODkw"
    other_b64 = "QkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkI="

    try:
        owner_created_a = owner_client.post("/projects", json={"project_id": owner_project_a})
        owner_created_b = owner_client.post("/projects", json={"project_id": owner_project_b})
        other_created = other_client.post("/projects", json={"project_id": other_project})
        assert owner_created_a.status_code == 200
        assert owner_created_b.status_code == 200
        assert other_created.status_code == 200
        created_roots.append(Path(owner_created_a.json()["project_root"]))
        created_roots.append(Path(owner_created_b.json()["project_root"]))
        created_roots.append(Path(other_created.json()["project_root"]))

        owner_uploaded = owner_client.post(
            f"/projects/{owner_project_a}/reference-audio",
            json={"filename": "owner-voice.wav", "audio_b64": owner_b64},
        )
        other_uploaded = other_client.post(
            f"/projects/{other_project}/reference-audio",
            json={"filename": "other-voice.wav", "audio_b64": other_b64},
        )
        assert owner_uploaded.status_code == 200
        assert other_uploaded.status_code == 200

        owner_hash = owner_uploaded.json()["audio_hash"]
        other_hash = other_uploaded.json()["audio_hash"]

        listed = owner_client.get(f"/projects/{owner_project_b}/reference-audio")
        assert listed.status_code == 200
        hashes = {row["audio_hash"] for row in listed.json()["samples"]}
        assert owner_hash in hashes
        assert other_hash not in hashes
    finally:
        for root in created_roots:
            if root.exists():
                shutil.rmtree(root)


def test_simple_synthesize_with_unknown_reference_audio_hash_returns_404():
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
                "reference_audio_hash": "a" * 64,
                "quality": "normal",
                "average_gap_seconds": 0.8,
                "output_format": "mp3",
                "voice_clone_authorized": True,
            },
        )
        assert response.status_code == 404
        assert "saved reference audio" in response.json()["detail"]
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_project_script_save_and_load_roundtrip():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        saved = client.post(
            f"/projects/{project_id}/script",
            json={"text": "First draft script text.", "source": "manual"},
        )
        assert saved.status_code == 200
        saved_payload = saved.json()
        assert saved_payload["saved"] is True
        assert saved_payload["project_id"] == project_id
        assert saved_payload["text"] == "First draft script text."
        assert len(saved_payload["versions"]) == 1
        assert saved_payload["current_version_id"]

        loaded = client.get(f"/projects/{project_id}/script")
        assert loaded.status_code == 200
        loaded_payload = loaded.json()
        assert loaded_payload["project_id"] == project_id
        assert loaded_payload["text"] == "First draft script text."
        assert loaded_payload["current_version_id"] == saved_payload["current_version_id"]
        assert len(loaded_payload["versions"]) == 1
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def test_project_script_restore_and_deduplicates_identical_save():
    client = TestClient(app)
    project_id = f"ui-{uuid.uuid4().hex[:8]}"
    project_root = Path("projects") / project_id

    try:
        created = client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200

        first = client.post(
            f"/projects/{project_id}/script",
            json={"text": "Version one text.", "source": "manual"},
        )
        assert first.status_code == 200
        first_payload = first.json()
        first_version_id = first_payload["current_version_id"]

        duplicate = client.post(
            f"/projects/{project_id}/script",
            json={"text": "Version one text.", "source": "autosave"},
        )
        assert duplicate.status_code == 200
        duplicate_payload = duplicate.json()
        assert duplicate_payload["saved"] is False
        assert len(duplicate_payload["versions"]) == 1

        second = client.post(
            f"/projects/{project_id}/script",
            json={"text": "Version two text.", "source": "manual"},
        )
        assert second.status_code == 200
        second_payload = second.json()
        second_version_id = second_payload["current_version_id"]
        assert second_payload["saved"] is True
        assert second_version_id != first_version_id
        assert len(second_payload["versions"]) == 2

        restored = client.post(
            f"/projects/{project_id}/script/restore",
            json={"version_id": first_version_id},
        )
        assert restored.status_code == 200
        restored_payload = restored.json()
        assert restored_payload["restored"] is True
        assert restored_payload["current_version_id"] == first_version_id
        assert restored_payload["text"] == "Version one text."

        loaded = client.get(f"/projects/{project_id}/script")
        assert loaded.status_code == 200
        loaded_payload = loaded.json()
        assert loaded_payload["current_version_id"] == first_version_id
        assert loaded_payload["text"] == "Version one text."
        version_ids = {row["version_id"] for row in loaded_payload["versions"]}
        assert first_version_id in version_ids
        assert second_version_id in version_ids
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)
