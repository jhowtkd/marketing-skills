from pathlib import Path


def test_vm_index_contains_chat_and_run_controls() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="chat-form"' in html
    assert 'id="chat-input"' in html
    assert 'id="start-foundation-run"' in html
    assert 'id="runs-timeline"' in html


def test_vm_index_contains_brand_workspace_thread_controls() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="brand-tabs"' in html
    assert 'id="new-thread-button"' in html
    assert 'id="threads-list"' in html
    assert 'id="close-thread-button"' in html


def test_vm_app_js_calls_expected_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v1/brands" in js
    assert "/api/v1/products" in js
    assert "/api/v1/chat" in js
    assert "/api/v1/runs/foundation" in js


def test_vm_app_js_supports_run_slash_command() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/run foundation" in js


def test_vm_app_js_uses_eventsource_and_approve_api() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "new EventSource" in js
    assert "/events" in js
    assert "/approve" in js


def test_vm_app_js_disables_approve_button_while_request_in_flight() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "buttonEl.disabled = true" in js
    assert "buttonEl.disabled = false" in js


def test_vm_app_js_guards_duplicate_approve_requests_per_run_id() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "const approvingRunIds = new Set();" in js
    assert "if (approvingRunIds.has(runId))" in js
    assert "approvingRunIds.add(runId)" in js
    assert "approvingRunIds.delete(runId)" in js


def test_vm_app_js_supports_threads_api_and_workspace_state() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v1/threads" in js
    assert "/messages" in js
    assert "/close" in js
    assert "new-thread-button" in js
    assert "loadThreads(" in js
    assert "selectThread(" in js
