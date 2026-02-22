from __future__ import annotations

from executor import approve_stage, get_status, run_until_gate


def test_foundation_flow_run_approve_until_completed(tmp_path) -> None:
    state = run_until_gate(
        runtime_root=tmp_path,
        project_id="acme",
        thread_id="th-001",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        query="crm",
    )
    assert state["status"] == "waiting_approval"

    state = approve_stage(tmp_path, "acme", "th-001", "brand-voice")
    assert state["current_stage"] == "positioning"

    state = approve_stage(tmp_path, "acme", "th-001", "positioning")
    assert state["current_stage"] == "keywords"

    state = approve_stage(tmp_path, "acme", "th-001", "keywords")
    assert state["status"] == "completed"

    status = get_status(tmp_path, "acme", "th-001")
    assert status["status"] == "completed"
    assert "final/foundation-brief.md" in status["artifacts"]

