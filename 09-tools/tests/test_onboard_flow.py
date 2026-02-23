from __future__ import annotations

from onboard import run_onboarding


def test_run_onboarding_respects_apply_skip_decisions(tmp_path) -> None:
    result = run_onboarding(
        ide_csv="codex,cursor",
        dry_run=False,
        auto_apply=False,
        decisions={"codex": "apply", "cursor": "skip"},
        shell_file=str(tmp_path / ".zshrc"),
        key_values={"PERPLEXITY_API_KEY": "k1", "FIRECRAWL_API_KEY": "k2"},
        apply_keys=False,
        target_root=tmp_path / "ide-configs",
    )

    assert result["ides"]["codex"]["status"] == "applied"
    assert result["ides"]["cursor"]["status"] == "skipped"

