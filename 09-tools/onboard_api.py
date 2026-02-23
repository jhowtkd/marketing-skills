from __future__ import annotations

from onboard import SUPPORTED_IDES, _detect_shell_profile, run_onboarding


def build_defaults(shell_file: str) -> dict:
    return {
        "supported_ides": list(SUPPORTED_IDES),
        "shell_file": str(_detect_shell_profile(shell_file)),
    }


def run_preview(ides: list[str], shell_file: str, apply_keys: bool, keys: dict[str, str]) -> dict:
    return run_onboarding(
        ide_csv=",".join(ides),
        dry_run=True,
        auto_apply=False,
        decisions={},
        shell_file=shell_file,
        key_values=keys,
        apply_keys=apply_keys,
    )
