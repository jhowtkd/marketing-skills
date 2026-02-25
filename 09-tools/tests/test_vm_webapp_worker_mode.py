from __future__ import annotations

from unittest.mock import MagicMock

import vm_webapp.__main__ as cli_main


def test_cli_supports_worker_command_and_does_not_mount_http_app() -> None:
    uvicorn_run = MagicMock()
    worker_calls: list[int] = []

    cli_main.uvicorn.run = uvicorn_run

    def fake_run_worker(*, poll_interval_ms: int) -> int:
        worker_calls.append(poll_interval_ms)
        return 0

    cli_main.run_worker = fake_run_worker

    exit_code = cli_main.main(["worker", "--poll-interval-ms", "250"])

    assert exit_code == 0
    assert worker_calls == [250]
    uvicorn_run.assert_not_called()
