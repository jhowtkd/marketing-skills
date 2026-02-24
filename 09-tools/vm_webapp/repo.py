from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from vm_webapp.models import Brand, Product, Run, Stage
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


def list_products_by_brand(session: Session, brand_id: str) -> list[Product]:
    return list(
        session.scalars(
            select(Product)
            .where(Product.brand_id == brand_id)
            .order_by(Product.product_id.asc())
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
