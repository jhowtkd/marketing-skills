from __future__ import annotations

from onboard import SUPPORTED_IDES, _detect_shell_profile


def build_defaults(shell_file: str) -> dict:
    return {
        "supported_ides": list(SUPPORTED_IDES),
        "shell_file": str(_detect_shell_profile(shell_file)),
    }
