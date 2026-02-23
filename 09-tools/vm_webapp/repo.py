from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vm_webapp.models import Brand


def create_brand(
    session: Session,
    *,
    brand_id: str,
    name: str,
    canonical: dict[str, Any],
) -> Brand:
    brand = Brand(
        brand_id=brand_id,
        name=name,
        canonical_json=json.dumps(canonical),
    )
    session.add(brand)
    session.flush()
    return brand


def list_brands(session: Session) -> list[Brand]:
    return list(session.scalars(select(Brand).order_by(Brand.brand_id)))
