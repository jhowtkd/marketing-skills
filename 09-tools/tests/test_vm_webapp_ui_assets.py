import re
from pathlib import Path


def test_vm_index_shell_has_mobile_stack_and_accessibility_landmarks() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'aria-label="Workspace Navigation"' in html
    assert 'aria-label="Workspace Content"' in html
    assert 'aria-label="Workspace Operations"' in html
    assert "lg:grid" in html or "lg:flex" in html
    assert "overflow-y-auto" in html


def test_vm_app_js_has_timeline_style_map_and_error_banner_hooks() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "TIMELINE_EVENT_STYLE" in js
    assert "ui-error-banner" in js
    assert "function setUiError" in js
    assert "function clearUiError" in js
    assert "setUiError(detail)" in js
    assert "clearUiError()" in js
    assert "TIMELINE_EVENT_STYLE[itemRow.event_type]" in js
    assert 'id="ui-error-banner"' in html


def test_vm_index_uses_stitch_shell_and_cdn_dependencies() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "https://cdn.tailwindcss.com?plugins=forms,typography" in html
    assert "fonts.googleapis.com/icon?family=Material+Icons+Outlined" in html
    assert 'id="vm-shell-left"' in html
    assert 'id="vm-shell-main"' in html
    assert 'id="vm-shell-right"' in html


def test_vm_index_places_anchor_ids_in_left_center_right_columns() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert re.search(r'id="vm-shell-left".*id="brands-list".*id="projects-list"', html, re.S)
    assert re.search(r'id="vm-shell-main".*id="threads-list".*id="timeline-list".*id="workflow-run-form".*id="workflow-run-detail-list"', html, re.S)
    assert re.search(r'id="vm-shell-right".*id="tasks-list".*id="approvals-list".*id="workflow-artifacts-list".*id="workflow-artifact-preview"', html, re.S)


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


def test_ui_assets_include_effective_mode_and_stage_status_labels() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "effective_mode" in js
    assert "requested_mode" in js
    assert "fallback_applied" in js
    assert "error_code" in js
    assert "Run Detail" in html

def test_vm_index_contains_studio_and_devmode_anchors() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "id=\"studio-toolbar\"" in html
    assert "id=\"studio-create-plan-button\"" in html
    assert "id=\"studio-devmode-toggle\"" in html
    assert "id=\"studio-artifact-preview\"" in html
    assert "id=\"studio-wizard\"" in html

def test_vm_app_js_has_devmode_toggle_wiring() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "studio-devmode-toggle" in js
    assert "localStorage" in js

def test_vm_app_js_includes_studio_wizard_ids() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "studio-create-plan-button" in js
    assert "studio-wizard" in js
    assert "/api/v2/threads" in js
    assert "/workflow-runs" in js

def test_vm_index_contains_studio_progress_anchors() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "id=\"studio-stage-progress\"" in html
    assert "id=\"studio-status-text\"" in html


def test_vm_index_contains_retro_terminal_head_and_shell_chrome() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "Share+Tech+Mono" in html
    assert "JetBrains+Mono" in html
    assert "fonts.googleapis.com/icon?family=Material+Icons" in html
    assert 'class="scanlines"' in html
    assert "SYS.VER.3.0.0 [MONOCHROME]" in html


def test_vm_index_left_column_uses_retro_panels_with_brand_project_thread_ids() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert re.search(
        r'id="vm-shell-left".*id="brand-create-form".*id="brands-list".*id="project-create-form".*id="projects-list".*id="thread-create-button".*id="threads-list"',
        html,
        re.S,
    )
    assert "Initialize Brand" in html
    assert "Execute Project" in html


def test_vm_index_main_and_right_columns_keep_all_runtime_anchors_in_retro_layout() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert re.search(
        r'id="vm-shell-main".*id="studio-toolbar".*id="studio-create-plan-button".*id="studio-devmode-toggle".*id="studio-artifact-preview".*id="studio-stage-progress".*id="thread-mode-form".*id="thread-modes-list".*id="timeline-list".*id="workflow-run-form".*id="workflow-run-detail-list"',
        html,
        re.S,
    )
    assert re.search(
        r'id="vm-shell-right".*id="tasks-list".*id="approvals-list".*id="workflow-artifacts-list".*id="workflow-artifact-preview"',
        html,
        re.S,
    )
    assert "Task_Board" in html


def test_vm_retro_theme_tokens_and_action_button_hooks_exist() -> None:
    css = Path("09-tools/web/vm/styles.css").read_text(encoding="utf-8")
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "--terminal-bg" in css
    assert ".scanlines" in css
    assert ".vm-terminal-btn" in css
    assert "createActionButton(label, onClick, variant" in js
    assert "vm-terminal-btn" in js
