from __future__ import annotations

from pathlib import Path

from onboard import upsert_export


def test_upsert_export_replaces_existing_value(tmp_path: Path) -> None:
    profile = tmp_path / ".zshrc"
    profile.write_text("export PERPLEXITY_API_KEY='old'\n", encoding="utf-8")

    upsert_export(profile, "PERPLEXITY_API_KEY", "new")

    content = profile.read_text(encoding="utf-8")
    assert "export PERPLEXITY_API_KEY='new'" in content
    assert content.count("PERPLEXITY_API_KEY") == 1

