from __future__ import annotations

from onboard import discover_targets


def test_discover_targets_returns_supported_ide_keys() -> None:
    targets = discover_targets("codex,cursor,kimi,antigravity")
    names = [item["ide"] for item in targets]
    assert names == ["codex", "cursor", "kimi", "antigravity"]

