from fastapi.testclient import TestClient

from vm_webapp.app import create_app


def test_root_serves_stitch_shell_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="vm-shell-left"' in html
    assert 'id="vm-shell-main"' in html
    assert 'id="vm-shell-right"' in html
    assert "Share+Tech+Mono" in html
    assert 'class="scanlines"' in html
    assert "VM Web App Event-Driven Workspace" in html
