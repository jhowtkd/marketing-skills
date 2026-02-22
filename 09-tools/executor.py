from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from artifact_store import write_artifact_file, write_log_event
from pipeline_models import build_initial_state
from providers.free_fallback import run_research_with_fallback
from providers.perplexity_client import run_perplexity_research
from stack_loader import load_stack
from state_store import load_state, save_state


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
    output_root: Path = Path("08-output"),
) -> dict:
    output_root = Path(output_root)
    stack = load_stack(stack_path)
    sequence = stack["sequence"]
    stage_ids = [stage["id"] for stage in sequence]
    auto_stage = stack.get("execution", {}).get("auto_start_stage", stage_ids[0])

    state = build_initial_state(project_id, thread_id, stack["name"], stage_ids)
    state["current_stage"] = auto_stage
    state["stack_path"] = stack_path
    state["query"] = query
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
    write_artifact_file(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        relative_path="research/research-report.md",
        content=(
            "# Research Report\n\n"
            f"- Query: {query}\n"
            f"- Provider: {state['provider_used'][auto_stage]}\n"
            f"- Fallback: {state['fallback_used'][auto_stage]}\n"
        ),
    )
    write_log_event(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        event={
            "stage": auto_stage,
            "status": "completed",
            "provider": state["provider_used"][auto_stage],
            "fallback_used": state["fallback_used"][auto_stage],
            "timestamp": _now_iso(),
        },
    )

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


def _artifact_for_stage(stage_id: str) -> str:
    mapping = {
        "research": "research/research-report.md",
        "brand-voice": "strategy/brand-voice-guide.md",
        "positioning": "strategy/positioning-strategy.md",
        "keywords": "strategy/keyword-map.md",
    }
    return mapping.get(stage_id, f"strategy/{stage_id}.md")


def _load_stack_from_state(state: dict) -> dict:
    stack_path = state.get("stack_path")
    if not stack_path:
        raise RuntimeError("stack_path missing from state")
    return load_stack(stack_path)


def approve_stage(runtime_root: Path, project_id: str, thread_id: str, stage_id: str) -> dict:
    output_root = Path("08-output")
    state = load_state(Path(runtime_root), project_id, thread_id)
    stack = _load_stack_from_state(state)
    sequence = stack["sequence"]
    stage_ids = [stage["id"] for stage in sequence]
    if stage_id not in stage_ids:
        raise ValueError(f"Unknown stage: {stage_id}")

    current_stage = state.get("current_stage")
    if current_stage and current_stage != stage_id:
        raise ValueError(f"Stage {stage_id} cannot be approved while current_stage is {current_stage}")

    stage_state = state["stages"][stage_id]
    stage_state["status"] = "running"
    stage_state["attempts"] = int(stage_state.get("attempts", 0)) + 1
    stage_state["status"] = "completed"

    artifact = _artifact_for_stage(stage_id)
    if artifact not in state["artifacts"]:
        state["artifacts"].append(artifact)
    write_artifact_file(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        relative_path=artifact,
        content=f"# {stage_id}\n\nStatus: completed\n",
    )

    next_stage_id = _next_stage_id(sequence, stage_id)
    state["current_stage"] = next_stage_id
    if next_stage_id is None:
        state["status"] = "completed"
        if "final/foundation-brief.md" not in state["artifacts"]:
            state["artifacts"].append("final/foundation-brief.md")
        write_artifact_file(
            output_root=output_root,
            project_id=project_id,
            thread_id=thread_id,
            relative_path="final/foundation-brief.md",
            content="# Foundation Brief\n\nPipeline completed.\n",
        )
    else:
        next_stage = next(stage for stage in sequence if stage["id"] == next_stage_id)
        state["status"] = "waiting_approval" if next_stage.get("approval_required", False) else "running"

    state["updated_at"] = _now_iso()
    write_log_event(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        event={
            "stage": stage_id,
            "status": "completed",
            "next_stage": next_stage_id,
            "pipeline_status": state["status"],
            "timestamp": state["updated_at"],
        },
    )
    save_state(Path(runtime_root), project_id, thread_id, state)
    return state


def get_status(runtime_root: Path, project_id: str, thread_id: str) -> dict:
    return load_state(Path(runtime_root), project_id, thread_id)


def retry_stage(runtime_root: Path, project_id: str, thread_id: str, stage_id: str) -> dict:
    output_root = Path("08-output")
    state = load_state(Path(runtime_root), project_id, thread_id)
    if stage_id not in state["stages"]:
        raise ValueError(f"Unknown stage: {stage_id}")

    stage_state = state["stages"][stage_id]
    stage_state["status"] = "running"
    stage_state["attempts"] = int(stage_state.get("attempts", 0)) + 1

    if stage_id == "research":
        query = state.get("query", "")
        data = run_research_with_fallback(
            premium_runner=lambda: run_perplexity_research(query),
            free_runner=lambda: _default_free_research(query),
        )
        state.setdefault("provider_used", {})[stage_id] = data.get("provider", "unknown")
        state.setdefault("fallback_used", {})[stage_id] = bool(data.get("fallback_used", False))
    stage_state["status"] = "completed"
    state["updated_at"] = _now_iso()
    write_log_event(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        event={
            "stage": stage_id,
            "status": "retried",
            "attempt": stage_state["attempts"],
            "timestamp": state["updated_at"],
        },
    )

    save_state(Path(runtime_root), project_id, thread_id, state)
    return state


def dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
