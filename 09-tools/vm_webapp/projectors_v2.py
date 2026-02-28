from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import datetime, timedelta, timezone

from vm_webapp.models import (
    ApprovalView,
    BrandView,
    CampaignView,
    EditorialDecisionView,
    EventLog,
    FirstRunOutcomeView,
    ProjectView,
    TaskView,
    ThreadView,
    TimelineItemView,
)
from vm_webapp.repo import (
    mark_outcome_failed_by_new_run,
    upsert_first_run_outcome,
    upsert_first_run_outcome_aggregate,
)


def apply_event_to_read_models(session: Session, event: EventLog) -> None:
    payload = json.loads(event.payload_json)

    if event.event_type in {"BrandCreated", "BrandUpdated"}:
        row = session.get(BrandView, payload["brand_id"])
        if row is None:
            row = BrandView(
                brand_id=payload["brand_id"],
                name=payload["name"],
                updated_at=event.occurred_at,
            )
            session.add(row)
        else:
            row.name = payload["name"]
            row.updated_at = event.occurred_at
        return

    if event.event_type in {"ProjectCreated", "ProjectUpdated"}:
        row = session.get(ProjectView, payload["project_id"])
        if row is None:
            row = ProjectView(
                project_id=payload["project_id"],
                brand_id=payload["brand_id"],
                name=payload["name"],
                objective=payload.get("objective", ""),
                channels_json=json.dumps(payload.get("channels", []), ensure_ascii=False),
                due_date=payload.get("due_date"),
                updated_at=event.occurred_at,
            )
            session.add(row)
        else:
            row.name = payload["name"]
            row.objective = payload.get("objective", row.objective)
            row.channels_json = json.dumps(payload.get("channels", []), ensure_ascii=False)
            row.due_date = payload.get("due_date")
            row.updated_at = event.occurred_at
        return

    if event.event_type == "ThreadCreated":
        row = session.get(ThreadView, payload["thread_id"])
        if row is None:
            session.add(
                ThreadView(
                    thread_id=payload["thread_id"],
                    brand_id=payload["brand_id"],
                    project_id=payload["project_id"],
                    title=payload["title"],
                    status="open",
                    modes_json="[]",
                    last_activity_at=event.occurred_at,
                )
            )
        return

    if event.event_type == "ThreadModeAdded":
        row = session.get(ThreadView, payload["thread_id"])
        if row is None:
            return
        modes = json.loads(row.modes_json)
        if payload["mode"] not in modes:
            modes.append(payload["mode"])
            row.modes_json = json.dumps(modes, ensure_ascii=False)
        row.last_activity_at = event.occurred_at

    if event.event_type == "ThreadRenamed":
        row = session.get(ThreadView, payload["thread_id"])
        if row is not None:
            row.title = payload["title"]
            row.last_activity_at = event.occurred_at

    if event.event_type == "ThreadModeRemoved":
        row = session.get(ThreadView, payload["thread_id"])
        if row is not None:
            modes = json.loads(row.modes_json)
            row.modes_json = json.dumps(
                [value for value in modes if value != payload["mode"]],
                ensure_ascii=False,
            )
            row.last_activity_at = event.occurred_at

    if event.event_type == "CampaignCreated":
        row = session.get(CampaignView, payload["campaign_id"])
        if row is None:
            row = CampaignView(
                campaign_id=payload["campaign_id"],
                brand_id=payload["brand_id"],
                project_id=payload["project_id"],
                title=payload.get("title", ""),
                updated_at=event.occurred_at,
            )
            session.add(row)
        else:
            row.title = payload.get("title", row.title)
            row.updated_at = event.occurred_at
        return

    if event.event_type == "TaskCommentAdded":
        row = session.get(TaskView, payload["task_id"])
        if row is None and event.thread_id:
            row = TaskView(
                task_id=payload["task_id"],
                thread_id=event.thread_id,
                title=payload["task_id"],
                status="open",
                updated_at=event.occurred_at,
            )
            session.add(row)
        if row is not None:
            row.updated_at = event.occurred_at

    if event.event_type == "TaskCreated":
        row = session.get(TaskView, payload["task_id"])
        if row is None and event.thread_id:
            row = TaskView(
                task_id=payload["task_id"],
                thread_id=event.thread_id,
                campaign_id=payload.get("campaign_id"),
                brand_id=payload.get("brand_id") or event.brand_id,
                title=payload.get("title", payload["task_id"]),
                status=payload.get("status", "open"),
                updated_at=event.occurred_at,
            )
            session.add(row)
        elif row is not None:
            row.title = payload.get("title", row.title)
            row.status = payload.get("status", row.status)
            row.campaign_id = payload.get("campaign_id", row.campaign_id)
            row.brand_id = payload.get("brand_id", row.brand_id)
            row.updated_at = event.occurred_at

    if event.event_type == "TaskCompleted":
        row = session.get(TaskView, payload["task_id"])
        if row is None and event.thread_id:
            row = TaskView(
                task_id=payload["task_id"],
                thread_id=event.thread_id,
                title=payload["task_id"],
                status="completed",
                updated_at=event.occurred_at,
            )
            session.add(row)
        if row is not None:
            row.status = "completed"
            row.updated_at = event.occurred_at

    if event.event_type == "ApprovalRequested":
        approval_id = payload["approval_id"]
        row = session.get(ApprovalView, approval_id)
        if row is None and event.thread_id:
            row = ApprovalView(
                approval_id=approval_id,
                thread_id=event.thread_id,
                status="pending",
                reason=payload.get("reason", ""),
                required_role=payload.get("required_role", "editor"),
                updated_at=event.occurred_at,
            )
            session.add(row)
        elif row is not None:
            row.status = "pending"
            row.reason = payload.get("reason", row.reason)
            row.required_role = payload.get("required_role", row.required_role)
            row.updated_at = event.occurred_at

    if event.event_type == "ApprovalGranted":
        approval_id = payload["approval_id"]
        row = session.get(ApprovalView, approval_id)
        if row is not None:
            row.status = "granted"
            row.updated_at = event.occurred_at

    if event.thread_id:
        timeline_item = session.scalar(
            select(TimelineItemView).where(TimelineItemView.event_id == event.event_id)
        )
        if timeline_item is None:
            session.add(
                TimelineItemView(
                    event_id=event.event_id,
                    thread_id=event.thread_id,
                    event_type=event.event_type,
                    actor_type=event.actor_type,
                    actor_id=event.actor_id,
                    payload_json=event.payload_json,
                    occurred_at=event.occurred_at,
                )
            )

    if event.event_type == "EditorialGoldenMarked":
        thread_id = payload.get("thread_id", event.thread_id or "")
        scope = payload.get("scope", "global")
        objective_key = payload.get("objective_key")
        decision_key = f"{thread_id}|{scope}|{objective_key or '-'}"
        row = session.get(EditorialDecisionView, decision_key)
        if row is None:
            row = EditorialDecisionView(
                decision_key=decision_key,
                thread_id=thread_id,
                scope=scope,
                objective_key=objective_key,
                run_id=payload.get("run_id", ""),
                justification=payload.get("justification", ""),
                event_id=event.event_id,
                updated_at=event.occurred_at,
            )
            session.add(row)
        else:
            row.run_id = payload.get("run_id", row.run_id)
            row.justification = payload.get("justification", row.justification)
            row.event_id = event.event_id
            row.updated_at = event.occurred_at

    # First-run outcome tracking (v12)
    if event.event_type == "RunCompleted":
        run_id = payload.get("run_id", event.aggregate_id)
        thread_id = payload.get("thread_id", event.thread_id or "")
        brand_id = payload.get("brand_id", event.brand_id or "")
        project_id = payload.get("project_id", event.project_id or "")
        profile = payload.get("profile", "default")
        mode = payload.get("mode", "balanced")
        approved = payload.get("approved", False)
        quality_score = payload.get("quality_score", 0.0)
        duration_ms = payload.get("duration_ms", 0.0)
        completed_at = payload.get("completed_at", event.occurred_at)
        
        # Assume success_24h=True initially (will be marked False if new run created)
        outcome = upsert_first_run_outcome(
            session,
            outcome_id=run_id,
            run_id=run_id,
            thread_id=thread_id,
            brand_id=brand_id,
            project_id=project_id,
            profile=profile,
            mode=mode,
            approved=approved,
            success_24h=approved,  # Only approved runs can be successful
            quality_score=quality_score,
            duration_ms=duration_ms,
            completed_at=completed_at,
        )
        
        # Update aggregate
        upsert_first_run_outcome_aggregate(
            session,
            brand_id=brand_id,
            project_id=project_id,
            profile=profile,
            mode=mode,
            approved=approved,
            success_24h=approved,
            quality_score=quality_score,
            duration_ms=duration_ms,
        )

    if event.event_type == "RunCreated":
        # When a new run is created, mark previous runs in the same thread
        # within 24h as not successful (user regenerated)
        thread_id = payload.get("thread_id", event.thread_id or "")
        created_at = payload.get("created_at", event.occurred_at)
        
        if thread_id:
            # Mark outcomes completed within 24h before this new run as failed
            mark_outcome_failed_by_new_run(
                session,
                thread_id=thread_id,
                before_timestamp=created_at,
            )
