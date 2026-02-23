from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from artifact_store import write_artifact_file, write_log_event
from pipeline_models import build_initial_state
from providers.firecrawl_client import run_firecrawl_extract
from providers.free_fallback import run_research_with_fallback
from providers.perplexity_client import run_perplexity_research
from stack_loader import load_stack
from state_store import load_state, save_state


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_free_research(query: str) -> dict:
    return {
        "provider": "duckduckgo-bs4",
        "provider_chain": ["duckduckgo-bs4"],
        "query": query,
        "results": [],
        "sources": [],
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


def _extract_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url:
            urls.append(url)
    return urls


def _run_premium_research(query: str) -> dict:
    perplexity_payload = run_perplexity_research(query)
    urls = _extract_urls(perplexity_payload)[:8]
    firecrawl_payload = run_firecrawl_extract(urls)
    firecrawl_urls = firecrawl_payload.get("urls", []) if isinstance(firecrawl_payload, dict) else []

    sources: list[str] = []
    for url in urls + list(firecrawl_urls):
        if isinstance(url, str) and url and url not in sources:
            sources.append(url)

    return {
        "provider": "perplexity+firecrawl",
        "provider_chain": ["perplexity", "firecrawl"],
        "query": query,
        "perplexity": perplexity_payload,
        "firecrawl": firecrawl_payload,
        "sources": sources,
    }


def _run_date_from_iso(iso_ts: str) -> str:
    return iso_ts[:10]


def _state_output_root(state: dict) -> Path:
    raw = state.get("output_root")
    if raw:
        return Path(raw)
    return Path("08-output").resolve()


def _state_run_date(state: dict) -> str:
    run_date = state.get("run_date")
    if isinstance(run_date, str) and run_date:
        return run_date

    started = state.get("run_started_at_utc")
    if isinstance(started, str) and started:
        return _run_date_from_iso(started)

    updated = state.get("updated_at")
    if isinstance(updated, str) and updated:
        return _run_date_from_iso(updated)

    return _run_date_from_iso(_now_iso())


def _format_provider_chain(chain: list[str]) -> str:
    return " -> ".join(chain) if chain else "unknown"


def _build_research_report(query: str, data: dict, provider_chain: list[str]) -> str:
    sources = data.get("sources", [])
    source_lines = "\n".join(
        f"- {url}" for url in sources if isinstance(url, str) and url
    )
    if not source_lines:
        source_lines = "- No external sources captured in this run."

    return (
        "# Research Report\n\n"
        "## Query\n"
        f"- {query}\n\n"
        "## Provider Chain\n"
        f"- {_format_provider_chain(provider_chain)}\n\n"
        "## Sources Captured\n"
        f"{source_lines}\n\n"
        "## Quick Synthesis\n"
        "- Competitive signals were collected for baseline positioning.\n"
        "- Use findings to inform voice, positioning, and keyword prioritization.\n\n"
        "## Next Step\n"
        "- Await manual approval for `brand-voice`.\n"
    )


def _build_stage_artifact_content(stage_id: str, state: dict) -> str:
    query = state.get("query", "n/a")
    if stage_id == "brand-voice":
        return (
            "# Brand Voice Guide\n\n"
            "## Voice Summary\n"
            f"- Positioning context: {query}\n"
            "- Tone: clear, evidence-led, pragmatic.\n\n"
            "## Words to Use\n"
            "- claro\n"
            "- mensurável\n"
            "- consistente\n\n"
            "## Words to Avoid\n"
            "- revolucionário\n"
            "- game-changing\n"
            "- sinergia\n\n"
            "## Sample Rewrite\n"
            "- Antes: solução revolucionária.\n"
            "- Depois: solução com ganhos mensuráveis em conversão.\n"
        )

    if stage_id == "positioning":
        return (
            "# Positioning Strategy\n\n"
            "## Chosen Angle\n"
            "- Evidence-first differentiation with practical implementation speed.\n\n"
            "## Tradeoffs\n"
            "- Less hype appeal.\n"
            "- Higher trust with technical buyers.\n\n"
            "## Validation Signal\n"
            "- Align messaging with research-derived customer language.\n"
        )

    if stage_id == "keywords":
        return (
            "# Keyword Map\n\n"
            "| Keyword | Intent | Stage |\n"
            "| --- | --- | --- |\n"
            "| crm para clinicas | commercial | middle |\n"
            "| automacao crm clinica | problem-aware | top |\n"
            "| software crm saude | solution-aware | middle |\n"
        )

    return f"# {stage_id}\n\nGenerated by threaded executor.\n"


def _build_foundation_brief(state: dict) -> str:
    return (
        "# Foundation Brief\n\n"
        "## Summary\n"
        f"- Query: {state.get('query', 'n/a')}\n"
        f"- Provider chain: {_format_provider_chain(state.get('provider_chain', {}).get('research', []))}\n"
        f"- Fallback used: {state.get('fallback_used', {}).get('research', False)}\n\n"
        "## Completed Stages\n"
        "- research\n"
        "- brand-voice\n"
        "- positioning\n"
        "- keywords\n\n"
        "## Next Action\n"
        "- Start conversion stack with this foundation context.\n"
    )


def run_until_gate(
    runtime_root: Path,
    project_id: str,
    thread_id: str,
    stack_path: str,
    query: str,
    output_root: Path = Path("08-output"),
) -> dict:
    output_root = Path(output_root).expanduser().resolve()
    stack = load_stack(stack_path)
    sequence = stack["sequence"]
    stage_ids = [stage["id"] for stage in sequence]
    auto_stage = stack.get("execution", {}).get("auto_start_stage", stage_ids[0])
    run_started_at = _now_iso()
    run_date = _run_date_from_iso(run_started_at)

    state = build_initial_state(project_id, thread_id, stack["name"], stage_ids)
    state["current_stage"] = auto_stage
    state["stack_path"] = stack_path
    state["query"] = query
    state["output_root"] = str(output_root)
    state["run_started_at_utc"] = run_started_at
    state["run_date"] = run_date
    state["provider_used"] = {}
    state["provider_chain"] = {}
    state["fallback_used"] = {}
    state["provider_errors"] = {}

    # Stage: research (auto)
    state["stages"][auto_stage]["status"] = "running"
    state["stages"][auto_stage]["attempts"] = 1
    data = run_research_with_fallback(
        premium_runner=lambda: _run_premium_research(query),
        free_runner=lambda: _default_free_research(query),
    )
    state["stages"][auto_stage]["status"] = "completed"
    state["provider_used"][auto_stage] = data.get("provider", "unknown")
    state["provider_chain"][auto_stage] = data.get(
        "provider_chain", [state["provider_used"][auto_stage]]
    )
    state["fallback_used"][auto_stage] = bool(data.get("fallback_used", False))
    if data.get("premium_error"):
        state["provider_errors"][auto_stage] = data["premium_error"]
    state["artifacts"].append("research/research-report.md")
    write_artifact_file(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        relative_path="research/research-report.md",
        run_date=run_date,
        content=_build_research_report(query, data, state["provider_chain"][auto_stage]),
    )
    write_log_event(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        run_date=run_date,
        event={
            "stage": auto_stage,
            "status": "completed",
            "provider": state["provider_used"][auto_stage],
            "provider_chain": state["provider_chain"][auto_stage],
            "fallback_used": state["fallback_used"][auto_stage],
            "premium_error": state["provider_errors"].get(auto_stage),
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
    state = load_state(Path(runtime_root), project_id, thread_id)
    output_root = _state_output_root(state)
    run_date = _state_run_date(state)
    state["output_root"] = str(output_root)
    state["run_date"] = run_date
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
        run_date=run_date,
        content=_build_stage_artifact_content(stage_id, state),
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
            run_date=run_date,
            content=_build_foundation_brief(state),
        )
    else:
        next_stage = next(stage for stage in sequence if stage["id"] == next_stage_id)
        state["status"] = "waiting_approval" if next_stage.get("approval_required", False) else "running"

    state["updated_at"] = _now_iso()
    write_log_event(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        run_date=run_date,
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
    state = load_state(Path(runtime_root), project_id, thread_id)
    output_root = _state_output_root(state)
    run_date = _state_run_date(state)
    state["output_root"] = str(output_root)
    state["run_date"] = run_date
    if stage_id not in state["stages"]:
        raise ValueError(f"Unknown stage: {stage_id}")

    stage_state = state["stages"][stage_id]
    stage_state["status"] = "running"
    stage_state["attempts"] = int(stage_state.get("attempts", 0)) + 1

    if stage_id == "research":
        query = state.get("query", "")
        data = run_research_with_fallback(
            premium_runner=lambda: _run_premium_research(query),
            free_runner=lambda: _default_free_research(query),
        )
        state.setdefault("provider_used", {})[stage_id] = data.get("provider", "unknown")
        state.setdefault("provider_chain", {})[stage_id] = data.get(
            "provider_chain", [state["provider_used"][stage_id]]
        )
        state.setdefault("fallback_used", {})[stage_id] = bool(data.get("fallback_used", False))
        if data.get("premium_error"):
            state.setdefault("provider_errors", {})[stage_id] = data["premium_error"]
        write_artifact_file(
            output_root=output_root,
            project_id=project_id,
            thread_id=thread_id,
            relative_path="research/research-report.md",
            run_date=run_date,
            content=_build_research_report(query, data, state["provider_chain"][stage_id]),
        )
    stage_state["status"] = "completed"
    state["updated_at"] = _now_iso()
    write_log_event(
        output_root=output_root,
        project_id=project_id,
        thread_id=thread_id,
        run_date=run_date,
        event={
            "stage": stage_id,
            "status": "retried",
            "attempt": stage_state["attempts"],
            "provider": state.get("provider_used", {}).get(stage_id),
            "timestamp": state["updated_at"],
        },
    )

    save_state(Path(runtime_root), project_id, thread_id, state)
    return state


def dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
