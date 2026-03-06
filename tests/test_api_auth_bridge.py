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
