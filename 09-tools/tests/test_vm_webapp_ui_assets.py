from pathlib import Path


def test_vm_index_contains_event_driven_workspace_panels() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="brand-create-form"' in html
    assert 'id="project-create-form"' in html
    assert 'id="thread-create-button"' in html
    assert 'id="timeline-list"' in html
    assert 'id="tasks-list"' in html
    assert 'id="approvals-list"' in html


def test_vm_app_js_targets_v2_event_driven_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v2/brands" in js
    assert "/api/v2/projects" in js
    assert "/api/v2/threads" in js
    assert "/api/v2/threads/" in js and "/timeline" in js
    assert "Idempotency-Key" in js
