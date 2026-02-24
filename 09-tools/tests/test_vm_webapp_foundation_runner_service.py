from __future__ import annotations

from pathlib import Path

import vm_webapp.foundation_runner_service as foundation_module
from vm_webapp.foundation_runner_service import FoundationRunnerService


def _write_foundation_artifact(
    output_root: Path,
    *,
    run_date: str,
    project_id: str,
    thread_id: str,
    relative_path: str,
    content: str,
) -> None:
    artifact_path = output_root / run_date / project_id / thread_id / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(content, encoding="utf-8")


def test_service_runs_research_with_run_until_gate_then_manual_stages(
    tmp_path: Path, monkeypatch
) -> None:
    service = FoundationRunnerService(workspace_root=tmp_path)
    calls: list[str] = []

    def _fake_run_until_gate(
        runtime_root: Path,
        project_id: str,
        thread_id: str,
        stack_path: str,
        query: str,
        output_root: Path,
    ) -> dict[str, object]:
        calls.append("run_until_gate")
        assert runtime_root == service.runtime_root
        assert stack_path == service.stack_path
        assert query == "crm"
        assert thread_id == "t1--run-1"
        _write_foundation_artifact(
            output_root,
            run_date="2026-02-24",
            project_id=project_id,
            thread_id=thread_id,
            relative_path="research/research-report.md",
            content="# Research\n\ncrm\n",
        )
        return {
            "status": "waiting_approval",
            "output_root": str(output_root),
            "run_date": "2026-02-24",
            "artifacts": ["research/research-report.md"],
        }

    def _fake_approve_stage(
        runtime_root: Path,
        project_id: str,
        thread_id: str,
        stage_id: str,
    ) -> dict[str, object]:
        calls.append("approve_stage")
        assert runtime_root == service.runtime_root
        assert thread_id == "t1--run-1"
        assert stage_id == "brand-voice"
        _write_foundation_artifact(
            service.output_root,
            run_date="2026-02-24",
            project_id=project_id,
            thread_id=thread_id,
            relative_path="strategy/brand-voice-guide.md",
            content="# Brand Voice\n\nclear\n",
        )
        return {
            "status": "waiting_approval",
            "output_root": str(service.output_root),
            "run_date": "2026-02-24",
            "artifacts": [
                "research/research-report.md",
                "strategy/brand-voice-guide.md",
            ],
        }

    monkeypatch.setattr(foundation_module.executor, "run_until_gate", _fake_run_until_gate)
    monkeypatch.setattr(foundation_module.executor, "approve_stage", _fake_approve_stage)

    stage1 = service.execute_stage(
        run_id="run-1",
        thread_id="t1",
        project_id="p1",
        request_text="crm",
        stage_key="research",
    )
    assert stage1.pipeline_status in {"running", "waiting_approval"}
    assert stage1.artifacts["research/research-report.md"].startswith("# Research")

    stage2 = service.execute_stage(
        run_id="run-1",
        thread_id="t1",
        project_id="p1",
        request_text="crm",
        stage_key="brand-voice",
    )
    assert stage2.stage_key == "brand-voice"
    assert stage2.artifacts["strategy/brand-voice-guide.md"].startswith("# Brand Voice")
    assert calls == ["run_until_gate", "approve_stage"]


def test_service_keeps_llm_handle_and_uses_default_model(tmp_path: Path) -> None:
    class FakeLLM:
        def __init__(self) -> None:
            self.calls = []

        def chat(self, **kwargs):
            self.calls.append(kwargs)
            return "ok"

    service = FoundationRunnerService(
        workspace_root=tmp_path,
        llm=FakeLLM(),
        llm_model="kimi-for-coding",
    )
    assert service.llm is not None
    assert service.llm_model == "kimi-for-coding"


def test_stage_prompt_builder_has_contract_for_all_foundation_stages(tmp_path: Path) -> None:
    service = FoundationRunnerService(workspace_root=tmp_path)
    for stage in ("research", "brand-voice", "positioning", "keywords"):
        prompt = service._build_stage_prompt(
            stage_key=stage,
            request_text="crm para clinicas",
            previous_artifacts={"research/research-report.md": "insights"},
        )
        assert stage in prompt.lower()
        assert "request" in prompt.lower()


def test_service_isolates_foundation_thread_per_run(tmp_path: Path, monkeypatch) -> None:
    service = FoundationRunnerService(workspace_root=tmp_path)
    seen_thread_ids: list[str] = []

    def _fake_run_until_gate(
        runtime_root: Path,
        project_id: str,
        thread_id: str,
        stack_path: str,
        query: str,
        output_root: Path,
    ) -> dict[str, object]:
        del runtime_root, stack_path, query
        seen_thread_ids.append(thread_id)
        _write_foundation_artifact(
            output_root,
            run_date="2026-02-24",
            project_id=project_id,
            thread_id=thread_id,
            relative_path="research/research-report.md",
            content=f"# Research\n\n{thread_id}\n",
        )
        return {
            "status": "waiting_approval",
            "output_root": str(output_root),
            "run_date": "2026-02-24",
            "artifacts": ["research/research-report.md"],
        }

    monkeypatch.setattr(foundation_module.executor, "run_until_gate", _fake_run_until_gate)

    first = service.execute_stage(
        run_id="run-a",
        thread_id="t-shared",
        project_id="p1",
        request_text="crm",
        stage_key="research",
    )
    second = service.execute_stage(
        run_id="run-b",
        thread_id="t-shared",
        project_id="p1",
        request_text="crm",
        stage_key="research",
    )

    assert seen_thread_ids == ["t-shared--run-a", "t-shared--run-b"]
    assert (
        first.artifacts["research/research-report.md"]
        != second.artifacts["research/research-report.md"]
    )
