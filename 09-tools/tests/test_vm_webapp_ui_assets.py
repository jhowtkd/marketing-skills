from pathlib import Path


def test_vm_index_contains_chat_and_run_controls() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="chat-form"' in html
    assert 'id="chat-input"' in html
    assert 'id="start-foundation-run"' in html
    assert 'id="runs-timeline"' in html
