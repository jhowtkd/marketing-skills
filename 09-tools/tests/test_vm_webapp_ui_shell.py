from fastapi.testclient import TestClient

from vm_webapp.app import create_app


def test_root_serves_react_ui_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "<title>VM Workspace</title>" in html
    assert 'data-vm-ui="react"' in html
    assert 'id="root"' in html
    assert "/assets/" in html
