from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vm_webapp.models import Brand, Product
from vm_webapp.workspace import Workspace


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


def create_product(
    session: Session,
    *,
    brand_id: str,
    product_id: str,
    name: str,
    canonical: dict[str, Any],
    ws: Workspace,
    essence_md: str,
) -> Product:
    product = Product(
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


def get_product(session: Session, product_id: str) -> Product | None:
    return session.scalar(select(Product).where(Product.product_id == product_id))
