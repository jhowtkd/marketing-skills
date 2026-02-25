from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from vm_webapp.models import ContextVersion


class ContextPolicyError(ValueError):
    pass


ALLOWED_OVERRIDES = {"tone", "target_audience", "objective", "channels"}


def resolve_hierarchical_context(
    session: Session,
    *,
    brand_id: str,
    campaign_id: str | None = None,
    task_id: str | None = None
) -> dict[str, Any]:
    context: dict[str, Any] = {}

    # 1. Load Brand (base)
    brand_ctx = _get_latest_payload(session, "brand", brand_id)
    context.update(brand_ctx)

    # 2. Load Campaign
    if campaign_id:
        campaign_ctx = _get_latest_payload(session, "campaign", campaign_id)
        _apply_overrides(context, campaign_ctx, source="campaign")

    # 3. Load Task
    if task_id:
        task_ctx = _get_latest_payload(session, "task", task_id)
        _apply_overrides(context, task_ctx, source="task")

    return context


def _get_latest_payload(session: Session, scope: str, scope_id: str) -> dict[str, Any]:
    row = session.scalar(
        select(ContextVersion)
        .where(ContextVersion.scope == scope, ContextVersion.scope_id == scope_id)
        .order_by(ContextVersion.created_at.desc())
        .limit(1)
    )
    if row is None:
        return {}
    return json.loads(row.payload_json)


def _apply_overrides(base: dict[str, Any], overrides: dict[str, Any], source: str) -> None:
    for key, value in overrides.items():
        if key not in ALLOWED_OVERRIDES and key in base:
            raise ContextPolicyError(f"Override of '{key}' is not allowed by {source}")
        base[key] = value
