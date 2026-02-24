from pathlib import Path


def test_vm_index_contains_event_driven_workspace_panels() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="brand-create-form"' in html
    assert 'id="project-create-form"' in html
    assert 'id="thread-create-button"' in html
    assert 'id="mode-help"' in html
    assert 'id="thread-modes-list"' in html
    assert 'id="timeline-list"' in html
    assert 'id="tasks-list"' in html
    assert 'id="approvals-list"' in html
    assert 'id="brand-id-input"' not in html
    assert 'id="project-id-input"' not in html


def test_vm_app_js_targets_v2_event_driven_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v2/brands" in js
    assert "/api/v2/projects" in js
    assert "/api/v2/threads" in js
    assert "/api/v2/threads/" in js and "/timeline" in js
    assert "/modes/" in js and "/remove" in js
    assert "PATCH" in js
    assert "buildEntityId" in js
    assert "Idempotency-Key" in js


def test_vm_index_contains_workflow_io_panel() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="workflow-run-form"' in html
    assert 'id="workflow-request-input"' in html
    assert 'id="workflow-overrides-input"' in html
    assert 'id="workflow-profile-preview-list"' in html
    assert 'id="workflow-runs-list"' in html
    assert 'id="workflow-artifacts-list"' in html
    assert 'id="workflow-artifact-preview"' in html


def test_vm_app_js_calls_workflow_run_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v2/threads/" in js and "/workflow-runs" in js
    assert "/api/v2/workflow-runs/" in js and "/artifacts" in js
    assert "/api/v2/workflow-runs/" in js and "/resume" in js
    assert "/api/v2/workflow-profiles" in js


def test_readme_mentions_kimi_env_vars_for_vm_webapp() -> None:
    content = Path("README.md").read_text(encoding="utf-8")
    assert "KIMI_API_KEY" in content
    assert "KIMI_MODEL" in content
    assert "KIMI_BASE_URL" in content


def test_ui_assets_include_effective_mode_and_stage_status_labels() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "effective_mode" in js
    assert "requested_mode" in js
    assert "fallback_applied" in js
    assert "error_code" in js
    assert "Run Detail" in html
