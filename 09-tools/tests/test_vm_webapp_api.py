from fastapi.testclient import TestClient

from vm_webapp.app import create_app


def test_api_health_and_list_brands() -> None:
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True

    res = client.get("/api/v1/brands")
    assert res.status_code == 200
    assert res.json()["brands"] == []
