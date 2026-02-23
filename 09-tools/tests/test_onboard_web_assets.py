from __future__ import annotations

from pathlib import Path


def test_index_html_contains_required_sections() -> None:
    html = Path("09-tools/web/onboard/index.html").read_text(encoding="utf-8")
    assert 'id="ide-form"' in html
    assert 'id="preview-btn"' in html
    assert 'id="apply-btn"' in html
    assert 'id="diff-panel"' in html


def test_app_js_targets_api_endpoints() -> None:
    js = Path("09-tools/web/onboard/app.js").read_text(encoding="utf-8")
    assert "/api/v1/onboard/preview" in js
    assert "/api/v1/onboard/apply" in js
    assert "fetch(" in js
