from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import ToolPermission, ToolCredential, _now_iso

class ToolPermissionError(Exception):
    pass

class ToolGovernance:
    def __init__(self, session: Session):
        self.session = session

    def grant_permission(self, brand_id: str, tool_id: str, max_calls_per_day: int = 100) -> None:
        stmt = select(ToolPermission).where(
            ToolPermission.brand_id == brand_id,
            ToolPermission.tool_id == tool_id
        )
        perm = self.session.execute(stmt).scalar_one_or_none()
        if not perm:
            perm = ToolPermission(brand_id=brand_id, tool_id=tool_id, max_calls_per_day=max_calls_per_day)
            self.session.add(perm)
        else:
            perm.max_calls_per_day = max_calls_per_day
        self.session.commit()

    def authorize_call(self, brand_id: str, tool_id: str) -> None:
        stmt = select(ToolPermission).where(
            ToolPermission.brand_id == brand_id,
            ToolPermission.tool_id == tool_id
        )
        perm = self.session.execute(stmt).scalar_one_or_none()
        if not perm:
            raise ToolPermissionError(f"Brand {brand_id} has no permission for tool {tool_id}")
        
        if perm.current_day_calls >= perm.max_calls_per_day:
            raise ToolPermissionError(f"Tool {tool_id} rate limit exceeded for brand {brand_id}")

    def record_call(self, brand_id: str, tool_id: str) -> None:
        stmt = select(ToolPermission).where(
            ToolPermission.brand_id == brand_id,
            ToolPermission.tool_id == tool_id
        )
        perm = self.session.execute(stmt).scalar_one_or_none()
        if perm:
            perm.current_day_calls += 1
            perm.last_call_at = _now_iso()
            self.session.commit()

    def set_credential_ref(self, brand_id: str, tool_id: str, secret_ref: str) -> None:
        stmt = select(ToolCredential).where(
            ToolCredential.brand_id == brand_id,
            ToolCredential.tool_id == tool_id
        )
        cred = self.session.execute(stmt).scalar_one_or_none()
        if not cred:
            cred = ToolCredential(brand_id=brand_id, tool_id=tool_id, secret_ref=secret_ref)
            self.session.add(cred)
        else:
            cred.secret_ref = secret_ref
        self.session.commit()

    def get_credential_ref(self, brand_id: str, tool_id: str) -> Optional[str]:
        stmt = select(ToolCredential).where(
            ToolCredential.brand_id == brand_id,
            ToolCredential.tool_id == tool_id
        )
        cred = self.session.execute(stmt).scalar_one_or_none()
        return cred.secret_ref if cred else None
