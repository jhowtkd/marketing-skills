from __future__ import annotations

from pathlib import Path


def test_index_html_contains_required_sections() -> None:
    html = Path("09-tools/web/onboard/index.html").read_text(encoding="utf-8")
    assert 'id="ide-form"' in html
    assert 'id="preview-btn"' in html
    assert 'id="apply-btn"' in html
    assert 'id="diff-panel"' in html
