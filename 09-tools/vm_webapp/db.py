from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vm_webapp.models import Base


def build_engine(db_path: Path | None = None, *, db_url: str | None = None) -> Engine:
    if db_url:
        kwargs = {"pool_pre_ping": True}
        if db_url.startswith("sqlite"):
            kwargs = {"connect_args": {"check_same_thread": False}}
        return create_engine(db_url, **kwargs)

    if db_path is None:
        raise ValueError("db_path or db_url must be provided")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite+pysqlite:///{db_path}")


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
