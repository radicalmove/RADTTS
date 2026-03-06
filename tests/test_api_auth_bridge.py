from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer

from radtts.api import app


def test_auth_bridge_sets_session_and_redirects_home():
    serializer = URLSafeTimedSerializer("radtts-dev-session-secret", salt="app-bridge-radtts-v1")
    token = serializer.dumps(
        {
            "sub": 7,
            "email": "bridge@example.com",
            "display_name": "Bridge User",
            "is_admin": True,
            "issuer": "psychek",
        }
    )

    client = TestClient(app)
    response = client.get(f"/auth/bridge?token={token}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"

    home = client.get("/")
    assert home.status_code == 200
    assert ">Admin<" in home.text
    assert ">Log out<" in home.text


def test_authenticated_user_project_namespace_is_scoped():
    serializer = URLSafeTimedSerializer("radtts-dev-session-secret", salt="app-bridge-radtts-v1")
    token = serializer.dumps(
        {
            "sub": 11,
            "email": "scope@example.com",
            "display_name": "Scoped User",
            "is_admin": False,
            "issuer": "psychek",
        }
    )

    client = TestClient(app)
    bridge = client.get(f"/auth/bridge?token={token}", follow_redirects=False)
    assert bridge.status_code == 302

    project_id = f"scope-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/projects",
        json={"project_id": project_id, "course": "C1", "module": "M1", "lesson": "L1"},
    )
    assert created.status_code == 200
    project_root = created.json()["project_root"]
    try:
        assert re.search(r"/u[0-9a-f]{12}__", project_root), project_root
        assert project_root.endswith(project_id)
    finally:
        root = Path(project_root)
        if root.exists():
            shutil.rmtree(root)


def test_list_projects_is_scoped_and_descoped_for_authenticated_user():
    serializer = URLSafeTimedSerializer("radtts-dev-session-secret", salt="app-bridge-radtts-v1")
    user1_token = serializer.dumps(
        {
            "sub": 101,
            "email": "scope1@example.com",
            "display_name": "Scope User 1",
            "is_admin": False,
            "issuer": "psychek",
        }
    )
    user2_token = serializer.dumps(
        {
            "sub": 202,
            "email": "scope2@example.com",
            "display_name": "Scope User 2",
            "is_admin": False,
            "issuer": "psychek",
        }
    )

    client1 = TestClient(app)
    client2 = TestClient(app)
    created_roots: list[Path] = []

    try:
        bridge1 = client1.get(f"/auth/bridge?token={user1_token}", follow_redirects=False)
        assert bridge1.status_code == 302
        user1_project = f"user1-{uuid.uuid4().hex[:8]}"
        created1 = client1.post("/projects", json={"project_id": user1_project})
        assert created1.status_code == 200
        created_roots.append(Path(created1.json()["project_root"]))

        listed1 = client1.get("/projects")
        assert listed1.status_code == 200
        ids1 = {item["project_id"] for item in listed1.json()["projects"]}
        assert user1_project in ids1

        bridge2 = client2.get(f"/auth/bridge?token={user2_token}", follow_redirects=False)
        assert bridge2.status_code == 302
        user2_project = f"user2-{uuid.uuid4().hex[:8]}"
        created2 = client2.post("/projects", json={"project_id": user2_project})
        assert created2.status_code == 200
        created_roots.append(Path(created2.json()["project_root"]))

        listed2 = client2.get("/projects")
        assert listed2.status_code == 200
        ids2 = {item["project_id"] for item in listed2.json()["projects"]}
        assert user2_project in ids2
        assert user1_project not in ids2
    finally:
        for root in created_roots:
            if root.exists():
                shutil.rmtree(root)


def test_project_owner_can_share_with_other_user():
    serializer = URLSafeTimedSerializer("radtts-dev-session-secret", salt="app-bridge-radtts-v1")
    owner_token = serializer.dumps(
        {
            "sub": 701,
            "email": "owner-share@example.com",
            "display_name": "Owner Share",
            "is_admin": False,
            "issuer": "psychek",
        }
    )
    collaborator_token = serializer.dumps(
        {
            "sub": 702,
            "email": "collab-share@example.com",
            "display_name": "Collab Share",
            "is_admin": False,
            "issuer": "psychek",
        }
    )

    owner_client = TestClient(app)
    collaborator_client = TestClient(app)
    created_roots: list[Path] = []

    try:
        assert owner_client.get(f"/auth/bridge?token={owner_token}", follow_redirects=False).status_code == 302
        assert collaborator_client.get(f"/auth/bridge?token={collaborator_token}", follow_redirects=False).status_code == 302

        project_id = f"share-{uuid.uuid4().hex[:8]}"
        created = owner_client.post("/projects", json={"project_id": project_id})
        assert created.status_code == 200
        created_roots.append(Path(created.json()["project_root"]))

        before_share = collaborator_client.get("/projects")
        assert before_share.status_code == 200
        ids_before = {item["project_id"] for item in before_share.json()["projects"]}
        assert project_id not in ids_before

        granted = owner_client.post(
            f"/projects/{project_id}/access/grant",
            json={"email": "collab-share@example.com"},
        )
        assert granted.status_code == 200

        after_share = collaborator_client.get("/projects")
        assert after_share.status_code == 200
        projects = after_share.json()["projects"]
        shared_item = next((item for item in projects if item["project_id"] == project_id), None)
        assert shared_item is not None
        assert bool(shared_item.get("shared")) is True

        project_ref = shared_item["project_ref"]
        outputs = collaborator_client.get(f"/projects/{project_ref}/outputs")
        assert outputs.status_code == 200
        assert outputs.json()["project_id"] == project_id
    finally:
        for root in created_roots:
            if root.exists():
                shutil.rmtree(root)
