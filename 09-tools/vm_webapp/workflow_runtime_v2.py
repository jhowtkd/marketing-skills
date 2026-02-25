from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vm_webapp.artifacts import write_stage_outputs
from vm_webapp.db import session_scope
from vm_webapp.events import EventEnvelope, now_iso
from vm_webapp.foundation_runner_service import FoundationRunnerService, FoundationStageResult
from vm_webapp.memory import MemoryIndex
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import (
    append_event,
    claim_run_for_execution,
    create_run,
    create_stage,
    get_approval_view,
    get_run,
    get_stream_version,
    list_stages,
    update_run_status,
    update_stage_status,
)
from vm_webapp.resilience import ResiliencePolicy, FallbackChain
from vm_webapp.workflow_profiles import (
    DEFAULT_PROFILES_PATH,
    FOUNDATION_MODE_DEFAULT,
    load_workflow_profiles,
    resolve_workflow_plan_with_contract,
)
from vm_webapp.workspace import Workspace


class StageExecutionError(RuntimeError):
    def __init__(
        self,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
    ) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.retryable = retryable


class WorkflowRuntimeV2:
    def __init__(
        self,
        *,
        engine: Engine,
        workspace: Workspace,
        memory: MemoryIndex,
        llm: Any,
        profiles_path: Path | None = None,
        foundation_runner: FoundationRunnerService | None = None,
        force_foundation_fallback: bool = True,
        foundation_mode: str = FOUNDATION_MODE_DEFAULT,
        llm_model: str = "kimi-for-coding",
    ) -> None:
        self.engine = engine
        self.workspace = workspace
        self.memory = memory
        self.llm = llm
        self.profiles_path = profiles_path or DEFAULT_PROFILES_PATH
        self.profiles = load_workflow_profiles(self.profiles_path)
        self.foundation_runner = foundation_runner or FoundationRunnerService(
            workspace_root=self.workspace.root,
            llm=llm,
            llm_model=llm_model,
        )
        self.force_foundation_fallback = force_foundation_fallback
        self.foundation_mode = foundation_mode
        self._run_locks_guard = threading.Lock()
        self._run_locks: dict[str, threading.Lock] = {}
        self.llm_model = llm_model

    def list_profiles(self) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for mode in sorted(self.profiles):
            profile = self.profiles[mode]
            payload.append(
                {
                    "mode": profile.mode,
                    "description": profile.description,
                    "stages": [
                        {
                            "key": stage.key,
                            "skills": list(stage.skills),
                            "approval_required": stage.approval_required,
                            "retry_policy": dict(stage.retry_policy),
                            "timeout_seconds": stage.timeout_seconds,
                        }
                        for stage in profile.stages
                    ],
                }
            )
        return payload

    def ensure_queued_run(
        self,
        *,
        session: Session,
        run_id: str,
        thread_id: str,
        brand_id: str,
        project_id: str,
        request_text: str,
        mode: str,
        skill_overrides: dict[str, list[str]] | None,
    ) -> dict[str, Any]:
        existing = get_run(session, run_id)
        if existing is not None:
            payload = {"run_id": existing.run_id, "status": existing.status}
            existing_plan = self._load_run_plan_or_none(run_id)
            if existing_plan is not None:
                payload["requested_mode"] = str(
                    existing_plan.get("requested_mode", existing_plan.get("mode", mode))
                )
                payload["effective_mode"] = str(
                    existing_plan.get("effective_mode", existing_plan.get("mode", mode))
                )
            return payload

        resolved = resolve_workflow_plan_with_contract(
            self.profiles,
            requested_mode=mode,
            skill_overrides=skill_overrides or {},
            force_foundation_fallback=self.force_foundation_fallback,
            foundation_mode=self.foundation_mode,
        )
        create_run(
            session,
            run_id=run_id,
            brand_id=brand_id,
            product_id=project_id,
            thread_id=thread_id,
            stack_path=str(resolved["effective_mode"]),
            user_request=request_text,
            status="queued",
        )
        for index, stage in enumerate(resolved["stages"]):
            create_stage(
                session,
                run_id=run_id,
                stage_id=str(stage["key"]),
                position=index,
                approval_required=bool(stage["approval_required"]),
                status="pending",
            )

        self._write_run_plan(
            run_id=run_id,
            plan=resolved,
            thread_id=thread_id,
            brand_id=brand_id,
            project_id=project_id,
            request_text=request_text,
            skill_overrides=skill_overrides or {},
        )
        self._write_run_summary(
            run_id=run_id,
            status="queued",
            thread_id=thread_id,
            brand_id=brand_id,
            project_id=project_id,
            mode=str(resolved["effective_mode"]),
        )
        return {
            "run_id": run_id,
            "status": "queued",
            "requested_mode": str(resolved["requested_mode"]),
            "effective_mode": str(resolved["effective_mode"]),
        }

    def process_event(
        self,
        *,
        session: Session,
        event_type: str,
        payload: dict[str, Any],
        actor_id: str,
        causation_id: str,
        correlation_id: str,
    ) -> dict[str, str]:
        run_id = str(payload.get("run_id") or uuid4().hex[:16])
        thread_id = str(payload["thread_id"])
        brand_id = str(payload.get("brand_id", ""))
        project_id = str(payload.get("project_id", ""))
        request_text = str(payload.get("request_text", ""))
        mode = str(payload.get("mode", "plan_90d"))
        skill_overrides = payload.get("skill_overrides") or {}
        if not isinstance(skill_overrides, dict):
            raise ValueError("skill_overrides must be a mapping")

        self.ensure_queued_run(
            session=session,
            run_id=run_id,
            thread_id=thread_id,
            brand_id=brand_id,
            project_id=project_id,
            request_text=request_text,
            mode=mode,
            skill_overrides=skill_overrides,
        )
        return self.execute_queued_run(
            session=session,
            run_id=run_id,
            actor_id=actor_id,
            causation_id=causation_id,
            correlation_id=correlation_id,
            trigger_event_type=event_type,
        )

    def execute_thread_run(
        self,
        *,
        thread_id: str,
        brand_id: str,
        project_id: str,
        request_text: str,
        mode: str,
        actor_id: str,
        session: Session | None = None,
    ) -> dict[str, str]:
        run_id = uuid4().hex[:16]
        if session is not None:
            self.ensure_queued_run(
                session=session,
                run_id=run_id,
                thread_id=thread_id,
                brand_id=brand_id,
                project_id=project_id,
                request_text=request_text,
                mode=mode,
                skill_overrides={},
            )
            return self.execute_queued_run(
                session=session,
                run_id=run_id,
                actor_id=actor_id,
                causation_id=f"evt-sync-{run_id}",
                correlation_id=f"evt-sync-{run_id}",
                trigger_event_type="WorkflowRunQueued",
            )

        with session_scope(self.engine) as db_session:
            self.ensure_queued_run(
                session=db_session,
                run_id=run_id,
                thread_id=thread_id,
                brand_id=brand_id,
                project_id=project_id,
                request_text=request_text,
                mode=mode,
                skill_overrides={},
            )
            return self.execute_queued_run(
                session=db_session,
                run_id=run_id,
                actor_id=actor_id,
                causation_id=f"evt-sync-{run_id}",
                correlation_id=f"evt-sync-{run_id}",
                trigger_event_type="WorkflowRunQueued",
            )

    def execute_queued_run(
        self,
        *,
        session: Session,
        run_id: str,
        actor_id: str,
        causation_id: str,
        correlation_id: str,
        trigger_event_type: str,
    ) -> dict[str, str]:
        run = get_run(session, run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        if run.status in {"completed", "failed", "canceled"}:
            return {"run_id": run.run_id, "status": run.status}
        run_lock = self._acquire_run_lock(run_id)
        if run_lock is None:
            current = get_run(session, run_id)
            if current is None:
                raise ValueError(f"run not found: {run_id}")
            return {"run_id": current.run_id, "status": current.status}
        try:
            initial_status = run.status
            if initial_status == "running":
                return {"run_id": run.run_id, "status": "running"}
            if initial_status not in {"queued", "waiting_approval"}:
                return {"run_id": run.run_id, "status": initial_status}

            claimed = claim_run_for_execution(
                session,
                run_id=run_id,
                allowed_statuses=(initial_status,),
                target_status="running",
            )
            if not claimed:
                current = get_run(session, run_id)
                if current is None:
                    raise ValueError(f"run not found: {run_id}")
                return {"run_id": current.run_id, "status": current.status}

            plan = self._load_run_plan(run_id)
            stage_map = {stage["key"]: stage for stage in plan["stages"]}
            run_mode = self._effective_mode(plan)

            if initial_status == "queued":
                self._append_thread_event(
                    session=session,
                    thread_id=run.thread_id,
                    brand_id=run.brand_id,
                    project_id=run.product_id,
                    actor_id=actor_id,
                    event_type="WorkflowRunStarted",
                    payload={
                        "thread_id": run.thread_id,
                        "run_id": run.run_id,
                        "mode": run_mode,
                        "trigger_event_type": trigger_event_type,
                    },
                    causation_id=causation_id,
                    correlation_id=correlation_id,
                )

            for stage in list_stages(session, run_id):
                if stage.status == "completed":
                    continue
                stage_cfg = stage_map.get(stage.stage_id)
                if stage_cfg is None:
                    continue

                approval_id = self._approval_id(run_id, stage.stage_id)
                task_id = self._task_id(run_id, stage.stage_id)
                approval = get_approval_view(session, approval_id)
                if stage_cfg["approval_required"] and (
                    approval is None or approval.status != "granted"
                ):
                    if stage.status != "waiting_approval":
                        update_stage_status(
                            session,
                            stage_pk=stage.stage_pk,
                            status="waiting_approval",
                            attempts=stage.attempts,
                        )
                        update_run_status(session, run_id=run_id, status="waiting_approval")
                        self._append_thread_event(
                            session=session,
                            thread_id=run.thread_id,
                            brand_id=run.brand_id,
                            project_id=run.product_id,
                            actor_id=actor_id,
                            event_type="WorkflowRunWaitingApproval",
                            payload={
                                "thread_id": run.thread_id,
                                "run_id": run.run_id,
                                "stage_key": stage.stage_id,
                                "approval_id": approval_id,
                                "task_id": task_id,
                            },
                            causation_id=causation_id,
                            correlation_id=correlation_id,
                        )
                        self._append_thread_event(
                            session=session,
                            thread_id=run.thread_id,
                            brand_id=run.brand_id,
                            project_id=run.product_id,
                            actor_id=actor_id,
                            event_type="TaskCreated",
                            payload={
                                "thread_id": run.thread_id,
                                "run_id": run.run_id,
                                "task_id": task_id,
                                "title": f"Review stage {stage.stage_id}",
                                "stage_key": stage.stage_id,
                            },
                            causation_id=causation_id,
                            correlation_id=correlation_id,
                        )
                        self._append_thread_event(
                            session=session,
                            thread_id=run.thread_id,
                            brand_id=run.brand_id,
                            project_id=run.product_id,
                            actor_id=actor_id,
                            event_type="ApprovalRequested",
                            payload={
                                "thread_id": run.thread_id,
                                "approval_id": approval_id,
                                "reason": f"workflow_gate:{run_id}:{stage.stage_id}",
                                "required_role": "editor",
                            },
                            causation_id=causation_id,
                            correlation_id=correlation_id,
                        )
                    self._write_run_summary(
                        run_id=run_id,
                        status="waiting_approval",
                        thread_id=run.thread_id,
                        brand_id=run.brand_id,
                        project_id=run.product_id,
                        mode=run_mode,
                    )
                    return {"run_id": run.run_id, "status": "waiting_approval"}

                attempts = stage.attempts + 1
                self._append_thread_event(
                    session=session,
                    thread_id=run.thread_id,
                    brand_id=run.brand_id,
                    project_id=run.product_id,
                    actor_id=actor_id,
                    event_type="WorkflowRunStageStarted",
                    payload={
                        "thread_id": run.thread_id,
                        "run_id": run.run_id,
                        "stage_key": stage.stage_id,
                        "attempt": attempts,
                        "skills": list(stage_cfg["skills"]),
                    },
                    causation_id=causation_id,
                    correlation_id=correlation_id,
                )
                try:
                    providers = [self.llm_model] + stage_cfg.get("fallback_providers", [])
                    current_model = providers[(attempts - 1) % len(providers)]

                    manifest = self._execute_stage(
                        run_id=run.run_id,
                        thread_id=run.thread_id,
                        project_id=run.product_id,
                        request_text=run.user_request,
                        mode=run_mode,
                        stage_key=stage.stage_id,
                        stage_position=stage.position,
                        skills=list(stage_cfg["skills"]),
                        attempts=attempts,
                        llm_model=current_model,
                    )
                except Exception as exc:
                    error_code = "stage_execution_error"
                    error_message = str(exc)
                    retryable = True
                    if isinstance(exc, StageExecutionError):
                        error_code = exc.error_code
                        error_message = exc.error_message
                        retryable = exc.retryable

                    max_attempts = int(stage_cfg["retry_policy"]["max_attempts"])
                    # If we have multiple providers, we might want to allow more attempts
                    total_allowed = max_attempts * len(providers)
                    policy = ResiliencePolicy(max_attempts=total_allowed)
                    decision = policy.next_action(attempt=attempts, retryable=retryable)

                    if decision.action in {"retry", "fallback"}:
                        update_stage_status(
                            session,
                            stage_pk=stage.stage_pk,
                            status="pending",
                            attempts=attempts,
                        )
                        update_run_status(session, run_id=run_id, status="queued")
                        
                        self._append_thread_event(
                            session=session,
                            thread_id=run.thread_id,
                            brand_id=run.brand_id,
                            project_id=run.product_id,
                            actor_id=actor_id,
                            event_type="WorkflowRunStageRetrying",
                            payload={
                                "thread_id": run.thread_id,
                                "run_id": run.run_id,
                                "stage_key": stage.stage_id,
                                "attempt": attempts,
                                "error_code": error_code,
                                "error_message": error_message,
                                "retryable": retryable,
                                "next_action": decision.action,
                                "delay_seconds": decision.delay_seconds,
                            },
                            causation_id=causation_id,
                            correlation_id=correlation_id,
                        )
                        return {"run_id": run.run_id, "status": "queued"}

                    update_stage_status(
                        session,
                        stage_pk=stage.stage_pk,
                        status="failed",
                        attempts=attempts,
                    )
                    update_run_status(session, run_id=run_id, status="failed")
                    self._append_thread_event(
                        session=session,
                        thread_id=run.thread_id,
                        brand_id=run.brand_id,
                        project_id=run.product_id,
                        actor_id=actor_id,
                        event_type="WorkflowRunStageFailed",
                        payload={
                            "thread_id": run.thread_id,
                            "run_id": run.run_id,
                            "stage_key": stage.stage_id,
                            "attempt": attempts,
                            "error_code": error_code,
                            "error_message": error_message,
                            "retryable": False,
                        },
                        causation_id=causation_id,
                        correlation_id=correlation_id,
                    )
                    self._append_thread_event(
                        session=session,
                        thread_id=run.thread_id,
                        brand_id=run.brand_id,
                        project_id=run.product_id,
                        actor_id=actor_id,
                        event_type="WorkflowRunFailed",
                        payload={"thread_id": run.thread_id, "run_id": run.run_id},
                        causation_id=causation_id,
                        correlation_id=correlation_id,
                    )
                    self._write_run_summary(
                        run_id=run_id,
                        status="failed",
                        thread_id=run.thread_id,
                        brand_id=run.brand_id,
                        project_id=run.product_id,
                        mode=run_mode,
                    )
                    return {"run_id": run.run_id, "status": "failed"}

                update_stage_status(
                    session,
                    stage_pk=stage.stage_pk,
                    status="completed",
                    attempts=attempts,
                )
                self._append_thread_event(
                    session=session,
                    thread_id=run.thread_id,
                    brand_id=run.brand_id,
                    project_id=run.product_id,
                    actor_id=actor_id,
                    event_type="WorkflowRunStageCompleted",
                    payload={
                        "thread_id": run.thread_id,
                        "run_id": run.run_id,
                        "stage_key": stage.stage_id,
                        "attempt": attempts,
                        "artifact_count": len(manifest["artifacts"]),
                    },
                    causation_id=causation_id,
                    correlation_id=correlation_id,
                )

            update_run_status(session, run_id=run_id, status="completed")
            self._append_thread_event(
                session=session,
                thread_id=run.thread_id,
                brand_id=run.brand_id,
                project_id=run.product_id,
                actor_id=actor_id,
                event_type="WorkflowRunCompleted",
                payload={"thread_id": run.thread_id, "run_id": run.run_id},
                causation_id=causation_id,
                correlation_id=correlation_id,
            )
            self._write_run_summary(
                run_id=run_id,
                status="completed",
                thread_id=run.thread_id,
                brand_id=run.brand_id,
                project_id=run.product_id,
                mode=run_mode,
            )
            return {"run_id": run.run_id, "status": "completed"}
        finally:
            run_lock.release()

    def _execute_stage(
        self,
        *,
        run_id: str,
        thread_id: str,
        project_id: str,
        request_text: str,
        mode: str,
        stage_key: str,
        stage_position: int,
        skills: list[str],
        attempts: int,
        llm_model: str | None = None,
    ) -> dict[str, Any]:
        result = self.foundation_runner.execute_stage(
            run_id=run_id,
            thread_id=thread_id,
            project_id=project_id,
            request_text=request_text,
            stage_key=stage_key,
            llm_model=llm_model,
        )
        if result.error_code:
            raise StageExecutionError(
                error_code=result.error_code,
                error_message=result.error_message or result.error_code,
                retryable=result.retryable,
            )

        output_payload = dict(result.output_payload)
        output_payload.setdefault("summary", f"stage {stage_key} completed")
        output_payload.setdefault("skills", skills)
        output_payload.setdefault("mode", mode)

        artifacts = dict(result.artifacts)
        if not artifacts:
            artifacts = {
                "result.json": json.dumps(output_payload, ensure_ascii=False, indent=2)
            }

        manifest = write_stage_outputs(
            stage_dir=self._stage_dir(run_id, stage_position, stage_key),
            run_id=run_id,
            thread_id=thread_id,
            stage_key=stage_key,
            stage_position=stage_position + 1,
            attempt=attempts,
            input_payload={
                "request_text": request_text,
                "mode": mode,
                "skills": skills,
            },
            output_payload=output_payload,
            artifacts=artifacts,
            event_id=f"evt-stage-{run_id}-{stage_key}-{attempts}",
            status="completed",
        )
        memory_text = self._memory_text_from_stage_result(result)
        if memory_text:
            skills_field = result.output_payload.get("skills", skills)
            if isinstance(skills_field, list):
                skills_csv = ",".join(str(item) for item in skills_field)
            else:
                skills_csv = ",".join(skills)
            self.memory.upsert_doc(
                doc_id=f"workflow:{run_id}:{stage_key}",
                text=memory_text,
                meta={
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "stage_key": stage_key,
                    "skills": skills_csv,
                    "mode": str(result.output_payload.get("mode", mode)),
                    "kind": "workflow_stage_output",
                },
            )
        return manifest

    @staticmethod
    def _memory_text_from_stage_result(result: FoundationStageResult) -> str:
        for path, content in result.artifacts.items():
            if path.endswith(".md") and content.strip():
                return content
        for content in result.artifacts.values():
            if content.strip():
                return content
        summary = result.output_payload.get("summary")
        return str(summary) if isinstance(summary, str) else ""

    @staticmethod
    def _effective_mode(plan: dict[str, Any]) -> str:
        effective = plan.get("effective_mode")
        if isinstance(effective, str) and effective:
            return effective
        mode = plan.get("mode")
        if isinstance(mode, str) and mode:
            return mode
        return FOUNDATION_MODE_DEFAULT

    def _load_run_plan_or_none(self, run_id: str) -> dict[str, Any] | None:
        path = self._run_plan_path(run_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _resolve_profile_version(self, plan: dict[str, Any]) -> str:
        value = plan.get("profile_version")
        if isinstance(value, str) and value:
            return value
        return "v1"

    def _resolve_requested_mode(self, plan: dict[str, Any]) -> str:
        value = plan.get("requested_mode")
        if isinstance(value, str) and value:
            return value
        return self._effective_mode(plan)

    def _resolve_fallback_applied(self, plan: dict[str, Any]) -> bool:
        value = plan.get("fallback_applied")
        if isinstance(value, bool):
            return value
        return self._resolve_requested_mode(plan) != self._effective_mode(plan)

    def _append_thread_event(
        self,
        *,
        session: Session,
        thread_id: str,
        brand_id: str,
        project_id: str,
        actor_id: str,
        event_type: str,
        payload: dict[str, Any],
        causation_id: str,
        correlation_id: str,
    ) -> None:
        row = append_event(
            session,
            EventEnvelope(
                event_id=f"evt-{uuid4().hex[:12]}",
                event_type=event_type,
                aggregate_type="thread",
                aggregate_id=thread_id,
                stream_id=f"thread:{thread_id}",
                expected_version=get_stream_version(session, f"thread:{thread_id}"),
                actor_type="agent",
                actor_id=actor_id,
                payload=payload,
                thread_id=thread_id,
                brand_id=brand_id or None,
                project_id=project_id or None,
                causation_id=causation_id,
                correlation_id=correlation_id,
            ),
        )
        apply_event_to_read_models(session, row)

    def _run_root(self, run_id: str) -> Path:
        return self.workspace.root / "runs" / run_id

    def _acquire_run_lock(self, run_id: str) -> threading.Lock | None:
        with self._run_locks_guard:
            lock = self._run_locks.get(run_id)
            if lock is None:
                lock = threading.Lock()
                self._run_locks[run_id] = lock
        acquired = lock.acquire(blocking=False)
        return lock if acquired else None

    def _stage_dir(self, run_id: str, stage_position: int, stage_key: str) -> Path:
        return self._run_root(run_id) / "stages" / f"{stage_position + 1:02d}-{stage_key}"

    def _run_plan_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "plan.json"

    def _run_summary_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "run.json"

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _write_run_plan(
        self,
        *,
        run_id: str,
        plan: dict[str, Any],
        thread_id: str,
        brand_id: str,
        project_id: str,
        request_text: str,
        skill_overrides: dict[str, list[str]],
    ) -> None:
        effective_mode = self._effective_mode(plan)
        payload = {
            "run_id": run_id,
            "thread_id": thread_id,
            "brand_id": brand_id,
            "project_id": project_id,
            "request_text": request_text,
            "mode": effective_mode,
            "requested_mode": self._resolve_requested_mode(plan),
            "effective_mode": effective_mode,
            "profile_version": self._resolve_profile_version(plan),
            "fallback_applied": self._resolve_fallback_applied(plan),
            "description": plan.get("description", ""),
            "skill_overrides": skill_overrides,
            "stages": plan.get("stages", []),
            "created_at": now_iso(),
        }
        self._write_json(self._run_plan_path(run_id), payload)

    def _load_run_plan(self, run_id: str) -> dict[str, Any]:
        path = self._run_plan_path(run_id)
        if not path.exists():
            raise ValueError(f"workflow plan not found for run: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_run_summary(
        self,
        *,
        run_id: str,
        status: str,
        thread_id: str,
        brand_id: str,
        project_id: str,
        mode: str,
    ) -> None:
        stages_root = self._run_root(run_id) / "stages"
        manifest_paths: list[str] = []
        if stages_root.exists():
            for stage_dir in sorted(stages_root.iterdir()):
                manifest = stage_dir / "manifest.json"
                if manifest.exists():
                    manifest_paths.append(
                        str(Path("stages") / stage_dir.name / "manifest.json")
                    )
        payload = {
            "run_id": run_id,
            "thread_id": thread_id,
            "brand_id": brand_id,
            "project_id": project_id,
            "mode": mode,
            "status": status,
            "updated_at": now_iso(),
            "manifest_paths": manifest_paths,
        }
        self._write_json(self._run_summary_path(run_id), payload)

    @staticmethod
    def _approval_id(run_id: str, stage_key: str) -> str:
        return f"apr-{run_id[:8]}-{stage_key[:24]}"

    @staticmethod
    def _task_id(run_id: str, stage_key: str) -> str:
        return f"task-{run_id[:8]}-{stage_key[:23]}"
