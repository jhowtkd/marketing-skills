from __future__ import annotations

from pathlib import Path


def test_readme_mentions_vm_onboard_command() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "@vm-onboard" in readme


def test_readme_mentions_vm_onboard_web_console() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "python3 09-tools/onboard_web.py serve" in readme
