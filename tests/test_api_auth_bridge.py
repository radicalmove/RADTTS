from __future__ import annotations

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
    assert "Bridge User" in home.text
