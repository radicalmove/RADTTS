from __future__ import annotations

from fastapi.testclient import TestClient

from radtts.api import app


def test_ui_homepage_renders():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "RADTTS Studio" in response.text
    assert "Create Project" in response.text
