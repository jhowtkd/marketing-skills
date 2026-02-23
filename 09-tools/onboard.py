#!/usr/bin/env python3
"""Vibe Marketing onboarding orchestrator (MCP + IDE setup)."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from difflib import unified_diff
from importlib import import_module
from pathlib import Path


SUPPORTED_IDES = ("codex", "cursor", "kimi", "antigravity")


def _adapter_module_name(ide: str) -> str:
    return f"onboard_adapters.{ide}"


def load_adapter(ide: str):
    if ide not in SUPPORTED_IDES:
        raise ValueError(f"Unsupported IDE: {ide}")
    return import_module(_adapter_module_name(ide))


def discover_targets(ide_csv: str) -> list[dict]:
    if ide_csv.strip():
        requested = [item.strip().lower() for item in ide_csv.split(",") if item.strip()]
    else:
        requested = list(SUPPORTED_IDES)

    unique = OrderedDict((ide, None) for ide in requested)
    targets: list[dict] = []
    home = Path.home()

    for ide in unique.keys():
        adapter = load_adapter(ide)
        targets.append(
            {
                "ide": ide,
                "status": "detected",
                "target_paths": [str(p) for p in adapter.default_target_paths(home)],
            }
        )
    return targets


def build_diff_preview(before: str, after: str, target: str) -> str:
    diff_lines = unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=target,
        tofile=target,
    )
    return "".join(diff_lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("vm-onboard")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--yes", action="store_true")
    run_parser.add_argument("--ide", default="")
    run_parser.add_argument("--shell-file", default="")

    return parser


def main() -> int:
    parser = build_parser()
    parser.parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
