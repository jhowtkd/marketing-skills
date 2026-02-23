from __future__ import annotations

from onboard_web import create_app


def test_health_endpoint() -> None:
    app = create_app()
    client = app.test_client()
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
