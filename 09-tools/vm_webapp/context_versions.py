from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from vm_webapp.models import ContextVersion


def append_context_version(
    session: Session,
    *,
    scope: str,
    scope_id: str,
    payload: dict[str, Any]
) -> str:
    version_id = f"ctxv-{uuid4().hex[:12]}"
    row = ContextVersion(
        version_id=version_id,
        scope=scope,
        scope_id=scope_id,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(row)
    session.flush()
    return version_id
