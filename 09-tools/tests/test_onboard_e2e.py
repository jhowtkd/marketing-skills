from __future__ import annotations

from onboard import run_onboarding


def test_onboard_e2e_dry_run_returns_all_ide_reports(tmp_path) -> None:
    report = run_onboarding(
        ide_csv="codex,cursor,kimi,antigravity",
        dry_run=True,
        auto_apply=False,
        decisions={},
        shell_file=str(tmp_path / ".zshrc"),
        key_values={},
        apply_keys=False,
        target_root=tmp_path / "ide-configs",
    )

    assert set(report["ides"].keys()) == {"codex", "cursor", "kimi", "antigravity"}
