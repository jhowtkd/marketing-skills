from __future__ import annotations

from onboard_api import build_defaults


def test_build_defaults_exposes_supported_ides_and_shell() -> None:
    defaults = build_defaults(shell_file="")
    assert defaults["supported_ides"] == ["codex", "cursor", "kimi", "antigravity"]
    assert defaults["shell_file"]
