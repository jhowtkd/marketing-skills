from __future__ import annotations

from artifact_store import write_log_event


def test_write_log_event_appends_jsonl(tmp_path) -> None:
    log_path = write_log_event(
        output_root=tmp_path,
        project_id="acme",
        thread_id="th-001",
        event={"stage": "research", "status": "completed"},
    )

    content = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    assert '"stage": "research"' in content[0]

