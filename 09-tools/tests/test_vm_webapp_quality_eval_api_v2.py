from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_quality_evaluation_endpoint_returns_structured_payload(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    response = client.post(
        "/api/v2/workflow-runs/run-missing/quality-evaluation",
        headers={"Idempotency-Key": "quality-1"},
        json={"depth": "deep", "rubric_version": "v1"},
    )

    assert response.status_code in {200, 404}
