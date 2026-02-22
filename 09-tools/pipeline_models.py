from __future__ import annotations

from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_initial_state(
    project_id: str,
    thread_id: str,
    stack_name: str,
    stage_ids: list[str],
) -> dict:
    stages = {stage_id: {"status": "pending", "attempts": 0} for stage_id in stage_ids}

    return {
        "project_id": project_id,
        "thread_id": thread_id,
        "stack": stack_name,
        "current_stage": stage_ids[0] if stage_ids else None,
        "status": "running",
        "stages": stages,
        "artifacts": [],
        "errors": [],
        "updated_at": _now_iso(),
    }

