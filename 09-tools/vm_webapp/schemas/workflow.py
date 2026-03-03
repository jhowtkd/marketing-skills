from __future__ import annotations

from datetime import datetime
from typing import Literal, Any, Optional

from .base import VMBaseModel, Timestamped


class WorkflowRunStatus(VMBaseModel):
    run_id: str
    thread_id: str
    status: Literal["pending", "running", "paused", "completed", "failed"]
    current_stage: Optional[str] = None
    progress_pct: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class StartWorkflowRunRequest(VMBaseModel):
    thread_id: str
    profile_mode: str = "foundation_stack"
    input_payload: dict[str, Any] = {}


class TaskResponse(VMBaseModel):
    task_id: str
    title: str
    status: Literal["pending", "in_progress", "completed", "blocked"]
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class TasksListResponse(VMBaseModel):
    tasks: list[TaskResponse]


class ApprovalResponse(VMBaseModel):
    approval_id: str
    run_id: str
    stage_key: str
    status: Literal["pending", "approved", "rejected"]
    requested_at: datetime
    responded_at: Optional[datetime] = None


class ApprovalsListResponse(VMBaseModel):
    approvals: list[ApprovalResponse]


class WorkflowProfileResponse(VMBaseModel):
    mode: str
    description: str
    stages: list[dict[str, Any]]


class WorkflowProfilesListResponse(VMBaseModel):
    profiles: list[WorkflowProfileResponse]
