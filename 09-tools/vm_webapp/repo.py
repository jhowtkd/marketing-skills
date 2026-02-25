from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from vm_webapp.events import EventEnvelope
from vm_webapp.models import (
    ApprovalView,
    Brand,
    BrandView,
    CommandDedup,
    EventLog,
    Project,
    ProjectView,
    Run,
    Stage,
    TaskView,
    Thread,
    ThreadView,
    TimelineItemView,
    ToolCredential,
    ToolPermission,
)


def get_tool_permission(
    session: Session, brand_id: str, tool_id: str
) -> ToolPermission | None:
    return session.scalar(
        select(ToolPermission).where(
            ToolPermission.brand_id == brand_id, ToolPermission.tool_id == tool_id
        )
    )


def get_tool_credential(
    session: Session, brand_id: str, tool_id: str
) -> ToolCredential | None:
    return session.scalar(
        select(ToolCredential).where(
            ToolCredential.brand_id == brand_id, ToolCredential.tool_id == tool_id
        )
    )


def create_brand(
    session: Session,
    *,
    brand_id: str,
    name: str,
    canonical: dict[str, Any],
    ws: Workspace | None = None,
    soul_md: str = "",
) -> Brand:
    brand = Brand(
        brand_id=brand_id,
        name=name,
        canonical_json=json.dumps(canonical),
    )
    session.add(brand)
    session.flush()
    if ws is not None:
        soul_path = ws.brand_soul_path(brand_id)
        soul_path.parent.mkdir(parents=True, exist_ok=True)
        soul_path.write_text(soul_md, encoding="utf-8")
    return brand


def list_brands(session: Session) -> list[Brand]:
    return list(session.scalars(select(Brand).order_by(Brand.brand_id)))


def list_products_by_brand(session: Session, brand_id: str) -> list[Project]:
    return list(
        session.scalars(
            select(Project)
            .where(Project.brand_id == brand_id)
            .order_by(Project.product_id.asc())
        )
    )


def create_product(
    session: Session,
    *,
    brand_id: str,
    product_id: str,
    name: str,
    canonical: dict[str, Any],
    ws: Workspace,
    essence_md: str,
) -> Project:
    product = Project(
        product_id=product_id,
        brand_id=brand_id,
        name=name,
        canonical_json=json.dumps(canonical),
    )
    session.add(product)
    session.flush()

    essence_path = ws.product_essence_path(brand_id, product_id)
    essence_path.parent.mkdir(parents=True, exist_ok=True)
    essence_path.write_text(essence_md, encoding="utf-8")
    return product


def get_product(session: Session, product_id: str) -> Project | None:
    return session.scalar(select(Project).where(Project.product_id == product_id))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run(
    session: Session,
    *,
    run_id: str,
    brand_id: str,
    product_id: str,
    thread_id: str,
    stack_path: str,
    user_request: str,
    status: str = "running",
) -> Run:
    run = Run(
        run_id=run_id,
        brand_id=brand_id,
        product_id=product_id,
        thread_id=thread_id,
        stack_path=stack_path,
        user_request=user_request,
        status=status,
    )
    session.add(run)
    session.flush()
    return run


def create_thread(
    session: Session,
    *,
    thread_id: str,
    brand_id: str,
    product_id: str,
    title: str,
) -> Thread:
    thread = Thread(
        thread_id=thread_id,
        brand_id=brand_id,
        product_id=product_id,
        title=title,
        status="open",
    )
    session.add(thread)
    session.flush()
    return thread


def list_threads(session: Session, brand_id: str, product_id: str) -> list[Thread]:
    return list(
        session.scalars(
            select(Thread)
            .where(Thread.brand_id == brand_id, Thread.product_id == product_id)
            .order_by(Thread.last_activity_at.desc())
        )
    )


def get_thread(session: Session, thread_id: str) -> Thread | None:
    return session.get(Thread, thread_id)


def close_thread(session: Session, thread_id: str) -> None:
    session.execute(
        update(Thread)
        .where(Thread.thread_id == thread_id)
        .values(status="closed", updated_at=_now_iso())
    )


def touch_thread_activity(session: Session, thread_id: str) -> None:
    session.execute(
        update(Thread)
        .where(Thread.thread_id == thread_id)
        .values(last_activity_at=_now_iso(), updated_at=_now_iso())
    )


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def list_runs_by_thread(session: Session, thread_id: str) -> list[Run]:
    return list(
        session.scalars(
            select(Run).where(Run.thread_id == thread_id).order_by(Run.created_at.desc())
        )
    )


def update_run_status(session: Session, run_id: str, status: str) -> None:
    session.execute(
        update(Run)
        .where(Run.run_id == run_id)
        .values(status=status, updated_at=_now_iso())
    )


def claim_run_for_execution(
    session: Session,
    *,
    run_id: str,
    allowed_statuses: tuple[str, ...],
    target_status: str = "running",
) -> bool:
    if not allowed_statuses:
        return False
    result = session.execute(
        update(Run)
        .where(Run.run_id == run_id, Run.status.in_(allowed_statuses))
        .values(status=target_status, updated_at=_now_iso())
    )
    return int(result.rowcount or 0) > 0


def create_stage(
    session: Session,
    *,
    run_id: str,
    stage_id: str,
    position: int,
    approval_required: bool,
    status: str = "pending",
) -> Stage:
    stage = Stage(
        run_id=run_id,
        stage_id=stage_id,
        position=position,
        approval_required=approval_required,
        status=status,
    )
    session.add(stage)
    session.flush()
    return stage


def list_stages(session: Session, run_id: str) -> list[Stage]:
    return list(
        session.scalars(
            select(Stage).where(Stage.run_id == run_id).order_by(Stage.position.asc())
        )
    )


def get_waiting_stage(session: Session, run_id: str) -> Stage | None:
    return session.scalar(
        select(Stage)
        .where(Stage.run_id == run_id, Stage.status == "waiting_approval")
        .order_by(Stage.position.asc())
    )


def update_stage_status(session: Session, stage_pk: int, status: str, attempts: int) -> None:
    session.execute(
        update(Stage)
        .where(Stage.stage_pk == stage_pk)
        .values(status=status, attempts=attempts, updated_at=_now_iso())
    )


def append_event(session: Session, envelope: EventEnvelope) -> EventLog:
    current = session.scalar(
        select(func.max(EventLog.stream_version)).where(
            EventLog.stream_id == envelope.stream_id
        )
    )
    current_version = int(current or 0)
    if current_version != envelope.expected_version:
        raise ValueError(
            f"stream version conflict: expected={envelope.expected_version} actual={current_version}"
        )

    row = EventLog(
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        aggregate_type=envelope.aggregate_type,
        aggregate_id=envelope.aggregate_id,
        stream_id=envelope.stream_id,
        stream_version=current_version + 1,
        actor_type=envelope.actor_type,
        actor_id=envelope.actor_id,
        brand_id=envelope.brand_id,
        project_id=envelope.project_id,
        thread_id=envelope.thread_id,
        correlation_id=envelope.correlation_id,
        causation_id=envelope.causation_id,
        payload_json=json.dumps(envelope.payload, ensure_ascii=False),
        occurred_at=envelope.occurred_at,
    )
    session.add(row)
    session.flush()
    return row


def list_events_by_stream(session: Session, stream_id: str) -> list[EventLog]:
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.stream_id == stream_id)
            .order_by(EventLog.stream_version.asc())
        )
    )


def get_stream_version(session: Session, stream_id: str) -> int:
    current = session.scalar(
        select(func.max(EventLog.stream_version)).where(EventLog.stream_id == stream_id)
    )
    return int(current or 0)


def list_events_by_thread(session: Session, thread_id: str) -> list[EventLog]:
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .order_by(EventLog.stream_version.asc())
        )
    )


def list_unprocessed_events(session: Session) -> list[EventLog]:
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.processed_at.is_(None))
            .order_by(EventLog.event_pk.asc())
        )
    )


def mark_event_processed(session: Session, event_id: str) -> None:
    session.execute(
        update(EventLog)
        .where(EventLog.event_id == event_id)
        .values(processed_at=_now_iso())
    )


def get_command_dedup(session: Session, *, idempotency_key: str) -> CommandDedup | None:
    return session.get(CommandDedup, idempotency_key)


def save_command_dedup(
    session: Session,
    *,
    idempotency_key: str,
    command_name: str,
    event_id: str,
    response: dict[str, Any],
) -> CommandDedup:
    row = CommandDedup(
        idempotency_key=idempotency_key,
        command_name=command_name,
        event_id=event_id,
        response_json=json.dumps(response, ensure_ascii=False),
    )
    session.add(row)
    session.flush()
    return row


def list_brands_view(session: Session) -> list[BrandView]:
    return list(session.scalars(select(BrandView).order_by(BrandView.brand_id.asc())))


def get_brand_view(session: Session, brand_id: str) -> BrandView | None:
    return session.get(BrandView, brand_id)


def list_projects_view(session: Session, *, brand_id: str) -> list[ProjectView]:
    return list(
        session.scalars(
            select(ProjectView)
            .where(ProjectView.brand_id == brand_id)
            .order_by(ProjectView.project_id.asc())
        )
    )


def get_project_view(session: Session, project_id: str) -> ProjectView | None:
    return session.get(ProjectView, project_id)


def get_event_by_id(session: Session, event_id: str) -> EventLog | None:
    return session.scalar(select(EventLog).where(EventLog.event_id == event_id))


def get_event_by_causation(
    session: Session,
    *,
    thread_id: str,
    causation_id: str,
    event_type: str | None = None,
) -> EventLog | None:
    query = select(EventLog).where(
        EventLog.thread_id == thread_id,
        EventLog.causation_id == causation_id,
    )
    if event_type:
        query = query.where(EventLog.event_type == event_type)
    query = query.order_by(EventLog.event_pk.desc())
    return session.scalar(query)


def list_threads_view(session: Session, *, project_id: str) -> list[ThreadView]:
    return list(
        session.scalars(
            select(ThreadView)
            .where(ThreadView.project_id == project_id)
            .order_by(ThreadView.last_activity_at.desc())
        )
    )


def get_thread_view(session: Session, thread_id: str) -> ThreadView | None:
    return session.get(ThreadView, thread_id)


def list_timeline_items_view(session: Session, *, thread_id: str) -> list[TimelineItemView]:
    return list(
        session.scalars(
            select(TimelineItemView)
            .where(TimelineItemView.thread_id == thread_id)
            .order_by(TimelineItemView.timeline_pk.asc())
        )
    )


def get_task_view(session: Session, task_id: str) -> TaskView | None:
    return session.get(TaskView, task_id)


def list_tasks_view(session: Session, *, thread_id: str) -> list[TaskView]:
    return list(
        session.scalars(
            select(TaskView)
            .where(TaskView.thread_id == thread_id)
            .order_by(TaskView.task_id.asc())
        )
    )


def get_approval_view(session: Session, approval_id: str) -> ApprovalView | None:
    return session.get(ApprovalView, approval_id)


def list_approvals_view(session: Session, *, thread_id: str) -> list[ApprovalView]:
    return list(
        session.scalars(
            select(ApprovalView)
            .where(ApprovalView.thread_id == thread_id)
            .order_by(ApprovalView.approval_id.asc())
        )
    )
