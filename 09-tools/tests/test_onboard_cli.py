from __future__ import annotations

from onboard import build_parser


def test_onboard_cli_exposes_run_and_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--dry-run"])

    assert args.command == "run"
    assert args.dry_run is True

