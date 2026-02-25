from __future__ import annotations

from pathlib import Path
from typing import Any

import vm_webapp.db as db_module
from vm_webapp.db import build_engine


def test_build_engine_accepts_sqlite_path_and_postgres_url(tmp_path: Path, monkeypatch) -> None:
    sqlite_path = tmp_path / "runtime" / "vm" / "workspace.sqlite3"
    sqlite_engine = build_engine(db_path=sqlite_path)
    try:
        assert sqlite_engine.url.drivername == "sqlite+pysqlite"
        assert sqlite_engine.url.database == str(sqlite_path)
    finally:
        sqlite_engine.dispose()

    captured: dict[str, Any] = {}

    class _SentinelEngine:
        pass

    sentinel = _SentinelEngine()

    def fake_create_engine(url: str, **kwargs: Any) -> _SentinelEngine:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)

    postgres_url = "postgresql://user:pass@localhost:5432/vm"
    engine = build_engine(db_url=postgres_url)

    assert engine is sentinel
    assert captured["url"] == postgres_url
    assert captured["kwargs"]["pool_pre_ping"] is True
    assert "connect_args" not in captured["kwargs"]
