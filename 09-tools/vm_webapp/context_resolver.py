from __future__ import annotations
from typing import Any
from sqlalchemy.orm import Session

class ContextPolicyError(ValueError):
    pass

def resolve_hierarchical_context(
    session: Session,
    *,
    brand_id: str,
    campaign_id: str | None = None,
    task_id: str | None = None
) -> dict[str, Any]:
    return {"brand_id": brand_id, "campaign_id": campaign_id, "task_id": task_id}
