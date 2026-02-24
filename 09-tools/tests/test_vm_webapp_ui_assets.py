from pathlib import Path


def test_vm_index_contains_chat_and_run_controls() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="chat-form"' in html
    assert 'id="chat-input"' in html
    assert 'id="start-foundation-run"' in html
    assert 'id="runs-timeline"' in html


def test_vm_app_js_calls_expected_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v1/brands" in js
    assert "/api/v1/products" in js
    assert "/api/v1/chat" in js
    assert "/api/v1/runs/foundation" in js


def test_vm_app_js_supports_run_slash_command() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/run foundation" in js
