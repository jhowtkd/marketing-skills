from __future__ import annotations

from pipeline_runner import build_parser


def test_cli_has_run_approve_status_retry_commands() -> None:
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert {"run", "approve", "status", "retry"} <= set(choices.keys())

