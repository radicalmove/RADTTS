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
