from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from vm_webapp.events import EventEnvelope
from vm_webapp.models import CommandDedup
from vm_webapp.repo import (
    append_event,
    get_approval_view,
    get_command_dedup,
    get_run,
    get_stream_version,
    get_task_view,
    save_command_dedup,
)


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def create_brand_command(
    session: Session,
    *,
    brand_id: str | None,
    name: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    resolved_brand_id = brand_id or _auto_id("b")
    stream_id = f"brand:{resolved_brand_id}"
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="BrandCreated",
        aggregate_type="brand",
        aggregate_id=resolved_brand_id,
        stream_id=stream_id,
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={"brand_id": resolved_brand_id, "name": name},
        brand_id=resolved_brand_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_brand",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "brand_id": resolved_brand_id, "name": name},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def create_project_command(
    session: Session,
    *,
    project_id: str | None,
    brand_id: str,
    name: str,
    objective: str,
    channels: list[str],
    due_date: str | None,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    resolved_project_id = project_id or _auto_id("p")
    stream_id = f"project:{resolved_project_id}"
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ProjectCreated",
        aggregate_type="project",
        aggregate_id=resolved_project_id,
        stream_id=stream_id,
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "project_id": resolved_project_id,
            "brand_id": brand_id,
            "name": name,
            "objective": objective,
            "channels": channels,
            "due_date": due_date,
        },
        brand_id=brand_id,
        project_id=resolved_project_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_project",
        event_id=saved.event_id,
        response={
            "event_id": saved.event_id,
            "project_id": resolved_project_id,
            "brand_id": brand_id,
        },
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def create_thread_command(
    session: Session,
    *,
    thread_id: str | None,
    project_id: str,
    brand_id: str,
    title: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    resolved_thread_id = thread_id or _auto_id("t")
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ThreadCreated",
        aggregate_type="thread",
        aggregate_id=resolved_thread_id,
        stream_id=f"thread:{resolved_thread_id}",
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "thread_id": resolved_thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
            "title": title,
        },
        brand_id=brand_id,
        project_id=project_id,
        thread_id=resolved_thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_thread",
        event_id=saved.event_id,
        response={
            "event_id": saved.event_id,
            "thread_id": resolved_thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
        },
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def update_brand_command(
    session: Session,
    *,
    brand_id: str,
    name: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"brand:{brand_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="BrandUpdated",
        aggregate_type="brand",
        aggregate_id=brand_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"brand_id": brand_id, "name": name},
        brand_id=brand_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="update_brand",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "brand_id": brand_id, "name": name},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def update_project_command(
    session: Session,
    *,
    project_id: str,
    brand_id: str,
    name: str,
    objective: str,
    channels: list[str],
    due_date: str | None,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"project:{project_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ProjectUpdated",
        aggregate_type="project",
        aggregate_id=project_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "project_id": project_id,
            "brand_id": brand_id,
            "name": name,
            "objective": objective,
            "channels": channels,
            "due_date": due_date,
        },
        brand_id=brand_id,
        project_id=project_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="update_project",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "project_id": project_id},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def rename_thread_command(
    session: Session,
    *,
    thread_id: str,
    title: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ThreadRenamed",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "title": title},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="rename_thread",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "thread_id": thread_id, "title": title},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def add_thread_mode_command(
    session: Session,
    *,
    thread_id: str,
    mode: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ThreadModeAdded",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "mode": mode},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="add_thread_mode",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "thread_id": thread_id, "mode": mode},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def remove_thread_mode_command(
    session: Session,
    *,
    thread_id: str,
    mode: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ThreadModeRemoved",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "mode": mode},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="remove_thread_mode",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "thread_id": thread_id, "mode": mode},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def add_comment_command(
    session: Session,
    *,
    task_id: str,
    message: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    task = get_task_view(session, task_id)
    thread_id = task.thread_id if task is not None else None
    stream_id = f"thread:{thread_id}" if thread_id else f"task:{task_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="TaskCommentAdded",
        aggregate_type="thread" if thread_id else "task",
        aggregate_id=thread_id or task_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"task_id": task_id, "message": message},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="add_comment",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "task_id": task_id},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def complete_task_command(
    session: Session,
    *,
    task_id: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    task = get_task_view(session, task_id)
    thread_id = task.thread_id if task is not None else None
    stream_id = f"thread:{thread_id}" if thread_id else f"task:{task_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="TaskCompleted",
        aggregate_type="thread" if thread_id else "task",
        aggregate_id=thread_id or task_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"task_id": task_id},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="complete_task",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "task_id": task_id},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def grant_approval_command(
    session: Session,
    *,
    approval_id: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    approval = get_approval_view(session, approval_id)
    thread_id = approval.thread_id if approval is not None else None
    stream_id = f"thread:{thread_id}" if thread_id else f"approval:{approval_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ApprovalGranted",
        aggregate_type="thread" if thread_id else "approval",
        aggregate_id=thread_id or approval_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"approval_id": approval_id},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="grant_approval",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "approval_id": approval_id},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def start_agent_plan_command(
    session: Session,
    *,
    thread_id: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentPlanStarted",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "plan_id": f"plan-{thread_id}"},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="start_agent_plan",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "thread_id": thread_id},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def request_workflow_run_command(
    session: Session,
    *,
    thread_id: str,
    brand_id: str,
    project_id: str,
    request_text: str,
    mode: str,
    run_id: str,
    skill_overrides: dict[str, list[str]] | None,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="WorkflowRunQueued",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "thread_id": thread_id,
            "brand_id": brand_id,
            "project_id": project_id,
            "run_id": run_id,
            "request_text": request_text,
            "mode": mode,
            "skill_overrides": skill_overrides or {},
        },
        thread_id=thread_id,
        brand_id=brand_id,
        project_id=project_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="request_workflow_run",
        event_id=saved.event_id,
        response={
            "event_id": saved.event_id,
            "thread_id": thread_id,
            "run_id": run_id,
            "status": "queued",
            "mode": mode,
        },
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def resume_workflow_run_command(
    session: Session,
    *,
    run_id: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    run = get_run(session, run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")

    stream_id = f"thread:{run.thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="WorkflowRunResumed",
        aggregate_type="thread",
        aggregate_id=run.thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "thread_id": run.thread_id,
            "brand_id": run.brand_id,
            "project_id": run.product_id,
            "run_id": run_id,
        },
        thread_id=run.thread_id,
        brand_id=run.brand_id,
        project_id=run.product_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="resume_workflow_run",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "run_id": run_id, "status": "running"},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup
