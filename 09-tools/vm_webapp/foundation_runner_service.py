from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import executor


FOUNDATION_STACK_PATH_DEFAULT = "06-stacks/foundation-stack/stack.yaml"
RESEARCH_STAGE_KEY = "research"
STAGE_ARTIFACT_CANDIDATES = {
    "research": ("research/research-report.md",),
    "brand-voice": ("strategy/brand-voice-guide.md",),
    "positioning": ("strategy/positioning-strategy.md",),
    "keywords": ("strategy/keyword-map.md", "final/foundation-brief.md"),
}


@dataclass(slots=True)
class FoundationStageResult:
    stage_key: str
    pipeline_status: str
    output_payload: dict[str, Any]
    artifacts: dict[str, str]
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


class FoundationRunnerService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        stack_path: str = FOUNDATION_STACK_PATH_DEFAULT,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.runtime_root = self.workspace_root / "foundation-runtime"
        self.output_root = self.workspace_root / "foundation-output"
        self.stack_path = stack_path

    def execute_stage(
        self,
        *,
        run_id: str,
        thread_id: str,
        project_id: str,
        request_text: str,
        stage_key: str,
    ) -> FoundationStageResult:
        foundation_thread_id = self._foundation_thread_id(thread_id, run_id)
        before_state = self._try_get_status(project_id=project_id, thread_id=foundation_thread_id)
        before_artifacts = self._artifact_set(before_state)

        try:
            if stage_key == RESEARCH_STAGE_KEY:
                state = executor.run_until_gate(
                    runtime_root=self.runtime_root,
                    project_id=project_id,
                    thread_id=foundation_thread_id,
                    stack_path=self.stack_path,
                    query=request_text,
                    output_root=self.output_root,
                )
            else:
                state = executor.approve_stage(
                    runtime_root=self.runtime_root,
                    project_id=project_id,
                    thread_id=foundation_thread_id,
                    stage_id=stage_key,
                )
        except Exception as exc:
            return FoundationStageResult(
                stage_key=stage_key,
                pipeline_status="failed",
                output_payload={},
                artifacts={},
                error_code="foundation_execution_error",
                error_message=str(exc),
                retryable=False,
            )

        artifacts = self._load_stage_artifacts(
            state=state,
            project_id=project_id,
            thread_id=foundation_thread_id,
            stage_key=stage_key,
            before_artifacts=before_artifacts,
        )
        output_payload = self._build_output_payload(state=state, stage_key=stage_key)
        return FoundationStageResult(
            stage_key=stage_key,
            pipeline_status=str(state.get("status", "running")),
            output_payload=output_payload,
            artifacts=artifacts,
        )

    @staticmethod
    def _foundation_thread_id(thread_id: str, run_id: str) -> str:
        return f"{thread_id}--{run_id}"

    def _try_get_status(self, *, project_id: str, thread_id: str) -> dict[str, Any] | None:
        try:
            state = executor.get_status(
                runtime_root=self.runtime_root,
                project_id=project_id,
                thread_id=thread_id,
            )
        except FileNotFoundError:
            return None
        return state if isinstance(state, dict) else None

    @staticmethod
    def _artifact_set(state: dict[str, Any] | None) -> set[str]:
        if not isinstance(state, dict):
            return set()
        artifacts = state.get("artifacts")
        if not isinstance(artifacts, list):
            return set()
        return {item for item in artifacts if isinstance(item, str) and item}

    def _load_stage_artifacts(
        self,
        *,
        state: dict[str, Any],
        project_id: str,
        thread_id: str,
        stage_key: str,
        before_artifacts: set[str],
    ) -> dict[str, str]:
        all_artifacts = [
            path
            for path in state.get("artifacts", [])
            if isinstance(path, str) and path.strip()
        ]
        new_artifacts = [path for path in all_artifacts if path not in before_artifacts]
        candidates = set(STAGE_ARTIFACT_CANDIDATES.get(stage_key, ()))

        selected: list[str] = []
        if candidates:
            selected = [path for path in new_artifacts if path in candidates]
            if not selected:
                selected = [path for path in all_artifacts if path in candidates]
        if not selected:
            selected = new_artifacts or all_artifacts

        base_dir = self._artifact_base_dir(state=state, project_id=project_id, thread_id=thread_id)
        payload: dict[str, str] = {}
        for relative_path in selected:
            artifact_path = base_dir / relative_path
            if artifact_path.exists():
                payload[relative_path] = artifact_path.read_text(encoding="utf-8")
        return payload

    @staticmethod
    def _artifact_base_dir(*, state: dict[str, Any], project_id: str, thread_id: str) -> Path:
        output_root = state.get("output_root")
        run_date = state.get("run_date")
        if not isinstance(output_root, str) or not output_root:
            raise ValueError("foundation state missing output_root")
        if not isinstance(run_date, str) or not run_date:
            raise ValueError("foundation state missing run_date")
        return Path(output_root) / run_date / project_id / thread_id

    @staticmethod
    def _build_output_payload(*, state: dict[str, Any], stage_key: str) -> dict[str, Any]:
        stage_state: dict[str, Any] = {}
        stages = state.get("stages")
        if isinstance(stages, dict):
            candidate = stages.get(stage_key)
            if isinstance(candidate, dict):
                stage_state = candidate
        return {
            "stage_key": stage_key,
            "pipeline_status": state.get("status"),
            "current_stage": state.get("current_stage"),
            "stage_status": stage_state.get("status"),
            "attempts": stage_state.get("attempts"),
            "run_date": state.get("run_date"),
        }
