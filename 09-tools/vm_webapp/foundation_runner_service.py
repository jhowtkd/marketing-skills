from __future__ import annotations

import sys
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


# Python 3.9 compatibility: slots is only available in Python 3.10+
_dataclass_kwargs = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_dataclass_kwargs)
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
        llm: Any | None = None,
        llm_model: str = "kimi-for-coding",
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.runtime_root = self.workspace_root / "foundation-runtime"
        self.output_root = self.workspace_root / "foundation-output"
        self.stack_path = stack_path
        self.llm = llm
        self.llm_model = llm_model

    def execute_stage(
        self,
        *,
        run_id: str,
        thread_id: str,
        project_id: str,
        request_text: str,
        stage_key: str,
        llm_model: str | None = None,
    ) -> FoundationStageResult:
        model_to_use = llm_model or self.llm_model
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

        # Generate LLM-enhanced content if LLM is available
        llm_used_successfully = False
        if self.llm is not None:
            # Build accumulated context from all artifacts in state
            accumulated_artifacts = self._load_all_artifacts_from_state(
                state=state,
                project_id=project_id,
                thread_id=foundation_thread_id,
            )
            prompt = self._build_stage_prompt(
                stage_key=stage_key,
                request_text=request_text,
                previous_artifacts=accumulated_artifacts,
            )
            # Replace the primary artifact with LLM-generated content
            candidates = STAGE_ARTIFACT_CANDIDATES.get(stage_key, ())
            for candidate in candidates:
                if candidate in artifacts:
                    # Use current artifact content as fallback to avoid data loss
                    current_content = artifacts[candidate]
                    llm_content = self._render_stage_markdown(
                        prompt=prompt,
                        fallback=current_content,
                        llm_model=model_to_use,
                    )
                    artifacts[candidate] = llm_content
                    # Update accumulated_artifacts so brief uses fresh content
                    accumulated_artifacts[candidate] = llm_content
                    llm_used_successfully = llm_content != current_content
                    break

            # Generate final brief when keywords stage completes the pipeline
            if stage_key == "keywords" and state.get("status") == "completed":
                brief_prompt = self._build_final_brief_prompt(
                    request_text=request_text,
                    artifacts=accumulated_artifacts,
                )
                existing_brief = accumulated_artifacts.get("final/foundation-brief.md", "")
                brief_md = self._render_stage_markdown(
                    prompt=brief_prompt,
                    fallback=existing_brief,
                    llm_model=model_to_use,
                )
                artifacts["final/foundation-brief.md"] = brief_md

        output_payload = self._build_output_payload(
            state=state,
            stage_key=stage_key,
            llm_enabled=self.llm is not None and llm_used_successfully,
            llm_model=model_to_use if (self.llm is not None and llm_used_successfully) else None,
        )
        return FoundationStageResult(
            stage_key=stage_key,
            pipeline_status=str(state.get("status", "running")),
            output_payload=output_payload,
            artifacts=artifacts,
        )

    def _render_stage_markdown(
        self,
        *,
        prompt: str,
        fallback: str,
        llm_model: str | None = None,
    ) -> str:
        if self.llm is None:
            return fallback
        try:
            return self.llm.chat(
                model=llm_model or self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1200,
            )
        except Exception:
            return fallback

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

    def _load_all_artifacts_from_state(
        self,
        *,
        state: dict[str, Any],
        project_id: str,
        thread_id: str,
    ) -> dict[str, str]:
        """Load all artifacts from state for context building (not just stage-specific)."""
        base_dir = self._artifact_base_dir(state=state, project_id=project_id, thread_id=thread_id)
        all_artifacts = [
            path
            for path in state.get("artifacts", [])
            if isinstance(path, str) and path.strip()
        ]
        payload: dict[str, str] = {}
        for relative_path in all_artifacts:
            artifact_path = base_dir / relative_path
            if artifact_path.exists():
                payload[relative_path] = artifact_path.read_text(encoding="utf-8")
        return payload

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

    def _build_stage_prompt(
        self,
        *,
        stage_key: str,
        request_text: str,
        previous_artifacts: dict[str, str],
    ) -> str:
        base = f"User request: {request_text}\n\n"
        if stage_key == "research":
            return (
                base
                + "You are a research analyst. Generate a comprehensive market research report in markdown format. "
                + "Include: market overview, target audience analysis, competitive landscape, and key insights. "
                + f"Stage: {stage_key}"
            )
        if stage_key == "brand-voice":
            research = previous_artifacts.get("research/research-report.md", "")
            return (
                base
                + "You are a brand strategist. Based on the research below, create a brand voice guide in markdown. "
                + "Include: brand personality, tone guidelines, vocabulary, and messaging principles.\n\n"
                + f"Research context:\n{research}\n\n"
                + f"Stage: {stage_key}"
            )
        if stage_key == "positioning":
            research = previous_artifacts.get("research/research-report.md", "")
            brand_voice = previous_artifacts.get("strategy/brand-voice-guide.md", "")
            return (
                base
                + "You are a positioning strategist. Create a positioning strategy in markdown. "
                + "Include: value proposition, unique selling points, market positioning, and key messages.\n\n"
                + f"Research context:\n{research}\n\n"
                + f"Brand voice context:\n{brand_voice}\n\n"
                + f"Stage: {stage_key}"
            )
        if stage_key == "keywords":
            research = previous_artifacts.get("research/research-report.md", "")
            positioning = previous_artifacts.get("strategy/positioning-strategy.md", "")
            return (
                base
                + "You are an SEO specialist. Create a keyword strategy map in markdown. "
                + "Include: primary keywords, secondary keywords, search intent analysis, and content recommendations.\n\n"
                + f"Research context:\n{research}\n\n"
                + f"Positioning context:\n{positioning}\n\n"
                + f"Stage: {stage_key}"
            )
        return f"Generate markdown for stage {stage_key}."

    def _build_final_brief_prompt(
        self,
        *,
        request_text: str,
        artifacts: dict[str, str],
    ) -> str:
        research = artifacts.get("research/research-report.md", "")
        brand_voice = artifacts.get("strategy/brand-voice-guide.md", "")
        positioning = artifacts.get("strategy/positioning-strategy.md", "")
        keywords = artifacts.get("strategy/keyword-map.md", "")
        return (
            f"User request: {request_text}\n\n"
            + "You are a senior marketing strategist. Synthesize all the foundation work below "
            + "into a comprehensive Foundation Brief in markdown format. "
            + "Include: executive summary, target audience, brand positioning, key messages, "
            + "SEO strategy, and next steps.\n\n"
            + f"## Research\n{research}\n\n"
            + f"## Brand Voice\n{brand_voice}\n\n"
            + f"## Positioning\n{positioning}\n\n"
            + f"## Keywords\n{keywords}\n\n"
            + "Stage: final foundation brief"
        )

    @staticmethod
    def _build_output_payload(
        *,
        state: dict[str, Any],
        stage_key: str,
        llm_enabled: bool = False,
        llm_model: str | None = None,
    ) -> dict[str, Any]:
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
            "llm": {
                "enabled": llm_enabled,
                "model": llm_model,
            },
        }
