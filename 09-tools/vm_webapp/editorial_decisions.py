from __future__ import annotations

import hashlib
import re
from typing import Any


def derive_objective_key(request_text: str) -> str:
    normalized = re.sub(r"\s+", " ", request_text.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:48] or "objective"
    digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def resolve_baseline(*, active_run_id: str, active_objective_key: str | None, runs: list[dict[str, Any]], decisions: dict[str, Any]) -> dict[str, str | None]:
    objective = (decisions.get("objective") or {}) if isinstance(decisions, dict) else {}
    if active_objective_key and isinstance(objective.get(active_objective_key), dict):
        run_id = str(objective[active_objective_key].get("run_id", ""))
        if run_id and run_id != active_run_id:
            return {"baseline_run_id": run_id, "source": "objective_golden"}

    global_decision = decisions.get("global") if isinstance(decisions, dict) else None
    if isinstance(global_decision, dict):
        run_id = str(global_decision.get("run_id", ""))
        if run_id and run_id != active_run_id:
            return {"baseline_run_id": run_id, "source": "global_golden"}

    ids = [str(row.get("run_id", "")) for row in runs]
    if active_run_id in ids:
        idx = ids.index(active_run_id)
        prev = ids[idx + 1] if idx + 1 < len(ids) else ""
        if prev:
            return {"baseline_run_id": prev, "source": "previous"}

    return {"baseline_run_id": None, "source": "none"}
