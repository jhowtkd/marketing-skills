from __future__ import annotations

from pipeline_models import build_initial_state


def test_build_initial_state_sets_research_as_current() -> None:
    state = build_initial_state(
        project_id="acme",
        thread_id="th-001",
        stack_name="foundation-stack",
        stage_ids=["research", "brand-voice", "positioning", "keywords"],
    )

    assert state["current_stage"] == "research"
    assert state["stages"]["research"]["status"] == "pending"
    assert state["stages"]["brand-voice"]["status"] == "pending"

