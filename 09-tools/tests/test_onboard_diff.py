from __future__ import annotations

from onboard import build_diff_preview


def test_build_diff_preview_contains_unified_markers() -> None:
    diff_text = build_diff_preview(
        before="line-a\n",
        after="line-a\nline-b\n",
        target="config.yaml",
    )

    assert "--- config.yaml" in diff_text
    assert "+++ config.yaml" in diff_text
    assert "+line-b" in diff_text

