from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pipeline_models import build_initial_state
from providers.free_fallback import run_research_with_fallback
from providers.perplexity_client import run_perplexity_research
from stack_loader import load_stack
from state_store import save_state


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_free_research(query: str) -> dict:
    return {
        "provider": "duckduckgo-bs4",
        "query": query,
        "results": [],
    }


def _next_stage_id(sequence: list[dict], current_stage_id: str) -> str | None:
    stage_ids = [stage["id"] for stage in sequence]
    try:
        current_index = stage_ids.index(current_stage_id)
    except ValueError:
        return None

    next_index = current_index + 1
    if next_index >= len(stage_ids):
        return None
    return stage_ids[next_index]


def run_until_gate(
    runtime_root: Path,
    project_id: str,
    thread_id: str,
    stack_path: str,
    query: str,
) -> dict:
    stack = load_stack(stack_path)
    sequence = stack["sequence"]
    stage_ids = [stage["id"] for stage in sequence]
    auto_stage = stack.get("execution", {}).get("auto_start_stage", stage_ids[0])

    state = build_initial_state(project_id, thread_id, stack["name"], stage_ids)
    state["current_stage"] = auto_stage
    state["provider_used"] = {}
    state["fallback_used"] = {}

    # Stage: research (auto)
    state["stages"][auto_stage]["status"] = "running"
    state["stages"][auto_stage]["attempts"] = 1
    data = run_research_with_fallback(
        premium_runner=lambda: run_perplexity_research(query),
        free_runner=lambda: _default_free_research(query),
    )
    state["stages"][auto_stage]["status"] = "completed"
    state["provider_used"][auto_stage] = data.get("provider", "unknown")
    state["fallback_used"][auto_stage] = bool(data.get("fallback_used", False))
    state["artifacts"].append("research/research-report.md")

    next_stage_id = _next_stage_id(sequence, auto_stage)
    state["current_stage"] = next_stage_id
    if next_stage_id is None:
        state["status"] = "completed"
    else:
        next_stage = next(stage for stage in sequence if stage["id"] == next_stage_id)
        if next_stage.get("approval_required", False):
            state["status"] = "waiting_approval"
        else:
            state["status"] = "running"
    state["updated_at"] = _now_iso()

    save_state(Path(runtime_root), project_id, thread_id, state)
    return state

