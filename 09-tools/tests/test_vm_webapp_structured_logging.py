from __future__ import annotations

import logging
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_http_request_logs_include_request_id_and_path(
    tmp_path: Path, caplog
) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    with caplog.at_level(logging.INFO, logger="vm_webapp.http"):
        response = client.get(
            "/api/v2/health/live",
            headers={
                "X-Request-Id": "req-123",
                "X-Correlation-Id": "corr-456",
            },
        )

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records if record.name == "vm_webapp.http"]
    assert any("request_id=req-123" in message for message in messages)
    assert any("correlation_id=corr-456" in message for message in messages)
    assert any("path=/api/v2/health/live" in message for message in messages)
