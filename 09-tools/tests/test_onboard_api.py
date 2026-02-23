from __future__ import annotations

from onboard_api import build_defaults, run_preview, run_apply


def test_build_defaults_exposes_supported_ides_and_shell() -> None:
    defaults = build_defaults(shell_file="")
    assert defaults["supported_ides"] == ["codex", "cursor", "kimi", "antigravity"]
    assert defaults["shell_file"]


def test_run_preview_calls_onboarding_in_dry_run(monkeypatch) -> None:
    captured = {}

    def fake_run_onboarding(**kwargs):
        captured.update(kwargs)
        return {"ides": {}, "keys": {}, "dry_run": kwargs["dry_run"]}

    monkeypatch.setattr("onboard_api.run_onboarding", fake_run_onboarding)

    report = run_preview(
        ides=["codex", "cursor"],
        shell_file="",
        apply_keys=False,
        keys={},
    )

    assert report["dry_run"] is True
    assert captured["ide_csv"] == "codex,cursor"
    assert captured["dry_run"] is True


def test_run_apply_passes_decisions_and_apply_keys(monkeypatch) -> None:
    captured = {}

    def fake_run_onboarding(**kwargs):
        captured.update(kwargs)
        return {"ides": {"codex": {"status": "applied"}}, "keys": {}}

    monkeypatch.setattr("onboard_api.run_onboarding", fake_run_onboarding)

    run_apply(
        ides=["codex", "cursor"],
        decisions={"codex": "apply", "cursor": "skip"},
        shell_file="~/.zshrc",
        apply_keys=True,
        keys={"PERPLEXITY_API_KEY": "k1"},
    )

    assert captured["dry_run"] is False
    assert captured["decisions"]["cursor"] == "skip"
    assert captured["apply_keys"] is True
