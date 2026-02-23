from __future__ import annotations

from pathlib import Path

import executor
from executor import approve_stage, run_until_gate


def _mock_perplexity(query: str) -> dict:
    return {
        "provider": "perplexity",
        "query": query,
        "results": [
            {"url": "https://example.com/a"},
            {"url": "https://example.com/b"},
        ],
    }


def _mock_firecrawl(urls: list[str]) -> dict:
    return {
        "provider": "firecrawl",
        "urls": urls,
        "pages": [{"url": url, "content": "sample"} for url in urls],
    }


def test_run_uses_perplexity_and_firecrawl_when_premium_available(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(executor, "run_perplexity_research", _mock_perplexity)
    monkeypatch.setattr(executor, "run_firecrawl_extract", _mock_firecrawl)

    state = run_until_gate(
        runtime_root=tmp_path / "runtime",
        project_id="acme",
        thread_id="th-001",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        query="crm para clínicas",
        output_root=tmp_path / "out",
    )

    assert state["provider_used"]["research"] == "perplexity+firecrawl"
    assert state["fallback_used"]["research"] is False


def test_output_root_is_persisted_and_reused_after_approve(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(executor, "run_perplexity_research", _mock_perplexity)
    monkeypatch.setattr(executor, "run_firecrawl_extract", _mock_firecrawl)

    output_root = tmp_path / "custom-output"
    state = run_until_gate(
        runtime_root=tmp_path / "runtime",
        project_id="acme",
        thread_id="th-001",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        query="crm para clínicas",
        output_root=output_root,
    )
    approved_state = approve_stage(
        runtime_root=tmp_path / "runtime",
        project_id="acme",
        thread_id="th-001",
        stage_id="brand-voice",
    )

    brand_voice_path = (
        output_root
        / state["run_date"]
        / "acme"
        / "th-001"
        / "strategy"
        / "brand-voice-guide.md"
    )

    assert approved_state["output_root"] == str(output_root)
    assert brand_voice_path.exists()


def test_run_date_is_used_for_artifact_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(executor, "run_perplexity_research", _mock_perplexity)
    monkeypatch.setattr(executor, "run_firecrawl_extract", _mock_firecrawl)

    output_root = tmp_path / "out"
    state = run_until_gate(
        runtime_root=tmp_path / "runtime",
        project_id="acme",
        thread_id="th-001",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        query="crm para clínicas",
        output_root=output_root,
    )

    report = (
        output_root
        / state["run_date"]
        / "acme"
        / "th-001"
        / "research"
        / "research-report.md"
    )
    assert "run_date" in state
    assert state["run_started_at_utc"].startswith(state["run_date"])
    assert report.exists()


def test_brand_voice_artifact_has_structured_content(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(executor, "run_perplexity_research", _mock_perplexity)
    monkeypatch.setattr(executor, "run_firecrawl_extract", _mock_firecrawl)

    output_root = tmp_path / "out"
    state = run_until_gate(
        runtime_root=tmp_path / "runtime",
        project_id="acme",
        thread_id="th-001",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        query="crm para clínicas",
        output_root=output_root,
    )
    approve_stage(
        runtime_root=tmp_path / "runtime",
        project_id="acme",
        thread_id="th-001",
        stage_id="brand-voice",
    )

    brand_voice_path = (
        output_root
        / state["run_date"]
        / "acme"
        / "th-001"
        / "strategy"
        / "brand-voice-guide.md"
    )
    content = brand_voice_path.read_text(encoding="utf-8")
    assert "## Voice Summary" in content
    assert "## Words to Use" in content
    assert "Status: completed" not in content

