from __future__ import annotations

from executor import run_until_gate


def test_run_executes_research_then_waits_brand_voice(tmp_path) -> None:
    state = run_until_gate(
        runtime_root=tmp_path,
        project_id="acme",
        thread_id="th-001",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        query="crm para clínicas",
    )

    assert state["stages"]["research"]["status"] == "completed"
    assert state["current_stage"] == "brand-voice"
    assert state["status"] == "waiting_approval"

