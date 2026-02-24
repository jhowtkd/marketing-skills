# VM Event-Driven Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-usable event-driven workspace with full in-app flow `Brand -> Project -> Thread`, human+agent collaboration, and an auditable unified timeline.

**Architecture:** Introduce an append-only event store and process all state changes through commands that emit immutable events. Materialize read models via deterministic projectors, then drive UI and APIs from these projections. Add an orchestrator and agent runtime adapter so planning threads can run in semi-automatic mode with explicit human approvals.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), vanilla HTML/CSS/JS, pytest, uv.

**Execution discipline:** Follow `@test-driven-development`, use `@systematic-debugging` on any failing test not explained by the expected red phase, and run `@verification-before-completion` before claiming completion.

---

### Task 1: Add Event Store Core (append-only + optimistic version)

**Files:**
- Create: `09-tools/vm_webapp/events.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_event_store.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.repo import append_event, list_events_by_stream


def test_append_event_enforces_stream_version(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    event = EventEnvelope(
        event_id="evt-1",
        event_type="BrandCreated",
        aggregate_type="brand",
        aggregate_id="brand-1",
        stream_id="brand:brand-1",
        expected_version=0,
        actor_type="human",
        actor_id="workspace-owner",
        payload={"name": "Acme"},
    )

    with session_scope(engine) as session:
        saved = append_event(session, event)
        assert saved.stream_version == 1

    with session_scope(engine) as session:
        rows = list_events_by_stream(session, "brand:brand-1")
        assert len(rows) == 1
        assert rows[0].event_type == "BrandCreated"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_event_store.py::test_append_event_enforces_stream_version -v`  
Expected: FAIL with import errors for missing `events.py` or missing repo functions.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/events.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class EventEnvelope:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    stream_id: str
    expected_version: int
    actor_type: str
    actor_id: str
    payload: dict[str, Any]
    brand_id: str | None = None
    project_id: str | None = None
    thread_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    occurred_at: str = field(default_factory=now_iso)
```

```python
# 09-tools/vm_webapp/repo.py
import json

from sqlalchemy import func, select
from vm_webapp.models import EventLog


def append_event(session: Session, envelope: EventEnvelope) -> EventLog:
    current = session.scalar(
        select(func.max(EventLog.stream_version)).where(EventLog.stream_id == envelope.stream_id)
    )
    current_version = int(current or 0)
    if current_version != envelope.expected_version:
        raise ValueError(
            f"stream version conflict: expected={envelope.expected_version} actual={current_version}"
        )

    row = EventLog(
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        aggregate_type=envelope.aggregate_type,
        aggregate_id=envelope.aggregate_id,
        stream_id=envelope.stream_id,
        stream_version=current_version + 1,
        actor_type=envelope.actor_type,
        actor_id=envelope.actor_id,
        brand_id=envelope.brand_id,
        project_id=envelope.project_id,
        thread_id=envelope.thread_id,
        correlation_id=envelope.correlation_id,
        causation_id=envelope.causation_id,
        payload_json=json.dumps(envelope.payload, ensure_ascii=False),
        occurred_at=envelope.occurred_at,
    )
    session.add(row)
    session.flush()
    return row


def list_events_by_stream(session: Session, stream_id: str) -> list[EventLog]:
    return list(
        session.scalars(
            select(EventLog).where(EventLog.stream_id == stream_id).order_by(EventLog.stream_version.asc())
        )
    )
```

```python
# 09-tools/vm_webapp/models.py
class EventLog(Base):
    __tablename__ = "event_log"

    event_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stream_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    stream_version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    brand_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurred_at: Mapped[str] = mapped_column(String(64), nullable=False)
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_event_store.py::test_append_event_enforces_stream_version -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/events.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_event_store.py
git commit -m "feat(vm-webapp): add append-only event store core"
```

### Task 2: Add Command Idempotency and Command Service (Brand/Project)

**Files:**
- Create: `09-tools/vm_webapp/commands_v2.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_commands_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.commands_v2 import create_brand_command
from vm_webapp.db import build_engine, init_db, session_scope


def test_create_brand_command_is_idempotent(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        first = create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="idem-brand-b1",
        )

    with session_scope(engine) as session:
        second = create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="idem-brand-b1",
        )

    assert first.event_id == second.event_id
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_commands_v2.py::test_create_brand_command_is_idempotent -v`  
Expected: FAIL because command service and idempotency table do not exist.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/models.py
class CommandDedup(Base):
    __tablename__ = "command_dedup"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    command_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
```

```python
# 09-tools/vm_webapp/commands_v2.py
from __future__ import annotations

from uuid import uuid4

from vm_webapp.events import EventEnvelope
from vm_webapp.models import CommandDedup
from vm_webapp.repo import append_event, get_command_dedup, save_command_dedup


def create_brand_command(session: Session, *, brand_id: str, name: str, actor_id: str, idempotency_key: str):
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"brand:{brand_id}"
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="BrandCreated",
        aggregate_type="brand",
        aggregate_id=brand_id,
        stream_id=stream_id,
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={"brand_id": brand_id, "name": name},
        brand_id=brand_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_brand",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "brand_id": brand_id, "name": name},
    )
    return get_command_dedup(session, idempotency_key=idempotency_key)
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_commands_v2.py::test_create_brand_command_is_idempotent -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/commands_v2.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_commands_v2.py
git commit -m "feat(vm-webapp): add v2 command idempotency service"
```

### Task 3: Add Read Models and Deterministic Projectors

**Files:**
- Create: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_projectors_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import append_event
from vm_webapp.events import EventEnvelope
from vm_webapp.repo import list_brands_view


def test_brand_created_event_projects_to_brands_view(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-brand",
                event_type="BrandCreated",
                aggregate_type="brand",
                aggregate_id="b1",
                stream_id="brand:b1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                payload={"brand_id": "b1", "name": "Acme"},
                brand_id="b1",
            ),
        )
        apply_event_to_read_models(session, row)

    with session_scope(engine) as session:
        brands = list_brands_view(session)
        assert len(brands) == 1
        assert brands[0].brand_id == "b1"
        assert brands[0].name == "Acme"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_projectors_v2.py::test_brand_created_event_projects_to_brands_view -v`  
Expected: FAIL due missing projector/read model functions.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/models.py
class BrandView(Base):
    __tablename__ = "brands_view"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ProjectView(Base):
    __tablename__ = "projects_view"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    channels_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    due_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
```

```python
# 09-tools/vm_webapp/projectors_v2.py
from __future__ import annotations

import json

from vm_webapp.models import BrandView, EventLog, ProjectView


def apply_event_to_read_models(session: Session, event: EventLog) -> None:
    payload = json.loads(event.payload_json)

    if event.event_type == "BrandCreated":
        row = session.get(BrandView, payload["brand_id"])
        if row is None:
            row = BrandView(brand_id=payload["brand_id"], name=payload["name"])
            session.add(row)
        else:
            row.name = payload["name"]
        return

    if event.event_type == "ProjectCreated":
        row = session.get(ProjectView, payload["project_id"])
        if row is None:
            row = ProjectView(
                project_id=payload["project_id"],
                brand_id=payload["brand_id"],
                name=payload["name"],
                objective=payload.get("objective", ""),
                channels_json=json.dumps(payload.get("channels", []), ensure_ascii=False),
                due_date=payload.get("due_date"),
            )
            session.add(row)
        return
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_projectors_v2.py::test_brand_created_event_projects_to_brands_view -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_projectors_v2.py
git commit -m "feat(vm-webapp): add v2 read models and projector core"
```

### Task 4: Add V2 API for Brand/Project CRUD (command + read)

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/app.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_v2_create_and_list_brand_and_project(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    b = client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "idem-b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    assert b.status_code == 200

    p = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "idem-p1"},
        json={
            "project_id": "p1",
            "brand_id": "b1",
            "name": "Launch Q2",
            "objective": "Grow qualified pipeline",
            "channels": ["seo", "email"],
            "due_date": "2026-06-30",
        },
    )
    assert p.status_code == 200

    listed = client.get("/api/v2/projects", params={"brand_id": "b1"})
    assert listed.status_code == 200
    assert listed.json()["projects"][0]["project_id"] == "p1"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_create_and_list_brand_and_project -v`  
Expected: FAIL with 404 for missing `/api/v2/*` endpoints.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/api.py
class BrandCreateRequest(BaseModel):
    brand_id: str
    name: str


class ProjectCreateRequest(BaseModel):
    project_id: str
    brand_id: str
    name: str
    objective: str = ""
    channels: list[str] = []
    due_date: str | None = None


@router.post("/v2/brands")
def create_brand_v2(payload: BrandCreateRequest, request: Request) -> dict[str, str]:
    idem = request.headers.get("Idempotency-Key")
    if not idem:
        raise HTTPException(status_code=400, detail="missing Idempotency-Key header")

    with session_scope(request.app.state.engine) as session:
        result = create_brand_command(
            session,
            brand_id=payload.brand_id,
            name=payload.name,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_pending_events(session)
    return {"event_id": result.event_id, "brand_id": payload.brand_id}


@router.get("/v2/projects")
def list_projects_v2(brand_id: str, request: Request) -> dict[str, list[dict[str, object]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_projects_view(session, brand_id=brand_id)
    return {
        "projects": [
            {
                "project_id": row.project_id,
                "brand_id": row.brand_id,
                "name": row.name,
                "objective": row.objective,
                "channels": json.loads(row.channels_json),
                "due_date": row.due_date,
            }
            for row in rows
        ]
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_create_and_list_brand_and_project -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/app.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat(vm-webapp): add v2 brand and project command/read api"
```

### Task 5: Add Thread Creation, Mode Selection, and Timeline Read API

**Files:**
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

```python
def test_v2_thread_lifecycle_with_modes_and_timeline(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post("/api/v2/brands", headers={"Idempotency-Key": "b1"}, json={"brand_id": "b1", "name": "Acme"})
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p1"},
        json={"project_id": "p1", "brand_id": "b1", "name": "Plan"},
    )

    created = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t1"},
        json={"thread_id": "t1", "project_id": "p1", "brand_id": "b1", "title": "Planning"},
    )
    assert created.status_code == 200

    added = client.post(
        "/api/v2/threads/t1/modes",
        headers={"Idempotency-Key": "m1"},
        json={"mode": "plan_90d"},
    )
    assert added.status_code == 200

    timeline = client.get("/api/v2/threads/t1/timeline")
    assert timeline.status_code == 200
    assert any(item["event_type"] == "ThreadModeAdded" for item in timeline.json()["items"])
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_thread_lifecycle_with_modes_and_timeline -v`  
Expected: FAIL because thread/mode/timeline endpoints and projections are missing.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/models.py
class ThreadView(Base):
    __tablename__ = "threads_view"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    modes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    last_activity_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class TimelineItemView(Base):
    __tablename__ = "timeline_items_view"

    timeline_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurred_at: Mapped[str] = mapped_column(String(64), nullable=False)
```

```python
# 09-tools/vm_webapp/projectors_v2.py
if event.event_type == "ThreadCreated":
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

if event.event_type == "ThreadModeAdded":
    row = session.get(ThreadView, payload["thread_id"])
    modes = json.loads(row.modes_json)
    if payload["mode"] not in modes:
        modes.append(payload["mode"])
        row.modes_json = json.dumps(modes, ensure_ascii=False)
        row.last_activity_at = event.occurred_at

if event.thread_id:
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
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_thread_lifecycle_with_modes_and_timeline -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/commands_v2.py 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat(vm-webapp): add v2 thread and mode workflow with timeline"
```

### Task 6: Add Orchestrator for Semi-Automatic Agent Plan + Approval Gates

**Files:**
- Create: `09-tools/vm_webapp/orchestrator_v2.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_orchestrator_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.orchestrator_v2 import process_new_events
from vm_webapp.events import EventEnvelope
from vm_webapp.repo import append_event, list_events_by_thread


def test_orchestrator_requests_approval_after_agent_plan_start(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        append_event(
            session,
            EventEnvelope(
                event_id="evt-start",
                event_type="AgentPlanStarted",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                payload={"thread_id": "t1", "plan_id": "plan-t1"},
                thread_id="t1",
            ),
        )
        process_new_events(session)

    with session_scope(engine) as session:
        events = list_events_by_thread(session, "t1")
        assert any(e.event_type == "ApprovalRequested" for e in events)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_orchestrator_v2.py::test_orchestrator_requests_approval_after_agent_plan_start -v`  
Expected: FAIL because orchestrator and approval events do not exist.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/orchestrator_v2.py
from __future__ import annotations

from uuid import uuid4

from vm_webapp.events import EventEnvelope
from vm_webapp.repo import append_event, list_unprocessed_events, mark_event_processed, get_stream_version


def process_new_events(session: Session) -> None:
    for event in list_unprocessed_events(session):
        if event.event_type == "AgentPlanStarted":
            payload = json.loads(event.payload_json)
            thread_id = payload["thread_id"]
            expected = get_stream_version(session, f"thread:{thread_id}")
            append_event(
                session,
                EventEnvelope(
                    event_id=f"evt-{uuid4().hex[:12]}",
                    event_type="ApprovalRequested",
                    aggregate_type="thread",
                    aggregate_id=thread_id,
                    stream_id=f"thread:{thread_id}",
                    expected_version=expected,
                    actor_type="system",
                    actor_id="orchestrator-v2",
                    payload={
                        "thread_id": thread_id,
                        "approval_id": f"apr-{uuid4().hex[:10]}",
                        "reason": "Human gate before agent execution",
                        "required_role": "editor",
                    },
                    thread_id=thread_id,
                    causation_id=event.event_id,
                    correlation_id=event.correlation_id or event.event_id,
                ),
            )
        mark_event_processed(session, event.event_id)
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_orchestrator_v2.py::test_orchestrator_requests_approval_after_agent_plan_start -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/orchestrator_v2.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/commands_v2.py 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py
git commit -m "feat(vm-webapp): add v2 orchestrator and approval gate events"
```

### Task 7: Add Agent Runtime Adapter and Artifact Events

**Files:**
- Create: `09-tools/vm_webapp/agent_runtime_v2.py`
- Modify: `09-tools/vm_webapp/orchestrator_v2.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_agent_runtime_v2.py`

**Step 1: Write the failing test**

```python
from vm_webapp.agent_runtime_v2 import run_planning_step


def test_run_planning_step_emits_started_and_completed_events(fake_session) -> None:
    emitted = run_planning_step(
        fake_session,
        thread_id="t1",
        project_id="p1",
        brand_id="b1",
        mode="plan_90d",
        request_text="Create 90-day strategy",
        actor_id="agent:vm-planner",
    )
    types = [item.event_type for item in emitted]
    assert "AgentStepStarted" in types
    assert "AgentStepCompleted" in types
    assert "AgentArtifactPublished" in types
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_agent_runtime_v2.py::test_run_planning_step_emits_started_and_completed_events -v`  
Expected: FAIL because runtime adapter does not exist.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/agent_runtime_v2.py
from __future__ import annotations

from uuid import uuid4

from vm_webapp.events import EventEnvelope


def run_planning_step(session: Session, *, thread_id: str, project_id: str, brand_id: str, mode: str, request_text: str, actor_id: str) -> list[EventEnvelope]:
    stream_id = f"thread:{thread_id}"
    current = get_stream_version(session, stream_id)

    started = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentStepStarted",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=current,
        actor_type="agent",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "mode": mode, "request_text": request_text},
        thread_id=thread_id,
        project_id=project_id,
        brand_id=brand_id,
    )
    row_started = append_event(session, started)

    completed = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentStepCompleted",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=row_started.stream_version,
        actor_type="agent",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "mode": mode, "summary": "Step completed"},
        thread_id=thread_id,
        project_id=project_id,
        brand_id=brand_id,
    )
    row_completed = append_event(session, completed)

    artifact = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentArtifactPublished",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=row_completed.stream_version,
        actor_type="agent",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "artifact_path": f"08-output/{thread_id}/{mode}.md"},
        thread_id=thread_id,
        project_id=project_id,
        brand_id=brand_id,
    )
    append_event(session, artifact)
    return [started, completed, artifact]
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_agent_runtime_v2.py::test_run_planning_step_emits_started_and_completed_events -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/agent_runtime_v2.py 09-tools/vm_webapp/orchestrator_v2.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_agent_runtime_v2.py
git commit -m "feat(vm-webapp): add v2 agent runtime artifact events"
```

### Task 8: Add In-App Collaboration Commands (tasks, comments, approvals)

**Files:**
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

```python
def test_v2_collaboration_flow_comment_task_complete_and_approval(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # assume fixture helper creates b1/p1/t1 and one pending approval apr-1
    seed_minimal_thread(client)

    c = client.post(
        "/api/v2/tasks/task-1/comment",
        headers={"Idempotency-Key": "comment-1"},
        json={"message": "Need stronger KPI rationale"},
    )
    assert c.status_code == 200

    done = client.post(
        "/api/v2/tasks/task-1/complete",
        headers={"Idempotency-Key": "task-done-1"},
    )
    assert done.status_code == 200

    granted = client.post(
        "/api/v2/approvals/apr-1/grant",
        headers={"Idempotency-Key": "apr-1-grant"},
    )
    assert granted.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_collaboration_flow_comment_task_complete_and_approval -v`  
Expected: FAIL due missing collaboration endpoints and projections.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/api.py
@router.post("/v2/tasks/{task_id}/comment")
def comment_task_v2(task_id: str, payload: TaskCommentRequest, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = add_comment_command(
            session,
            task_id=task_id,
            message=payload.message,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_pending_events(session)
    return {"event_id": result.event_id, "task_id": task_id}


@router.post("/v2/approvals/{approval_id}/grant")
def grant_approval_v2(approval_id: str, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = grant_approval_command(
            session,
            approval_id=approval_id,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_pending_events(session)
        process_new_events(session)
    return {"event_id": result.event_id, "approval_id": approval_id}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_collaboration_flow_comment_task_complete_and_approval -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/commands_v2.py 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat(vm-webapp): add v2 collaboration commands and api"
```

### Task 9: Build Event-Driven Workspace UI (Brand/Project/Thread/Timeline)

**Files:**
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/styles.css`
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_vm_index_contains_event_driven_workspace_panels() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="brand-create-form"' in html
    assert 'id="project-create-form"' in html
    assert 'id="thread-create-button"' in html
    assert 'id="timeline-list"' in html
    assert 'id="tasks-list"' in html
    assert 'id="approvals-list"' in html


def test_vm_app_js_targets_v2_event_driven_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v2/brands" in js
    assert "/api/v2/projects" in js
    assert "/api/v2/threads" in js
    assert "/api/v2/threads/" in js and "/timeline" in js
    assert "Idempotency-Key" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_event_driven_workspace_panels -v`  
Expected: FAIL because new workspace structure is missing.

**Step 3: Write minimal implementation**

```html
<!-- 09-tools/web/vm/index.html -->
<section class="panel" id="brand-workspace-panel">
  <h2>Brands</h2>
  <form id="brand-create-form">
    <input id="brand-id-input" placeholder="brand id" />
    <input id="brand-name-input" placeholder="brand name" />
    <button type="submit">Create Brand</button>
  </form>
  <div id="brands-list"></div>
</section>

<section class="panel" id="project-workspace-panel">
  <h2>Projects</h2>
  <form id="project-create-form"></form>
  <div id="projects-list"></div>
</section>

<section class="panel" id="thread-workspace-panel">
  <h2>Threads</h2>
  <button id="thread-create-button" type="button">New Thread</button>
  <div id="threads-list"></div>
  <div id="timeline-list"></div>
  <div id="tasks-list"></div>
  <div id="approvals-list"></div>
</section>
```

```javascript
// 09-tools/web/vm/app.js
const API_V2 = "/api/v2";

function buildIdempotencyKey(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

async function postV2(path, body, prefix) {
  return fetchJson(`${API_V2}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": buildIdempotencyKey(prefix),
    },
    body: JSON.stringify(body),
  });
}

async function createBrand() {
  await postV2("/brands", { brand_id: brandIdInput.value, name: brandNameInput.value }, "brand");
  await loadBrands();
}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_event_driven_workspace_panels -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(vm-webapp): add v2 event-driven workspace ui shell"
```

### Task 10: Reliability and End-to-End Verification (idempotency, conflict, gates)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_event_driven_e2e.py`
- Modify: `09-tools/tests/test_vm_webapp_api_v2.py`
- Modify: `09-tools/vm_webapp/api.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient


def test_duplicate_idempotency_key_returns_same_event(client: TestClient) -> None:
    body = {"brand_id": "b1", "name": "Acme"}
    one = client.post("/api/v2/brands", headers={"Idempotency-Key": "dup-1"}, json=body)
    two = client.post("/api/v2/brands", headers={"Idempotency-Key": "dup-1"}, json=body)

    assert one.status_code == 200
    assert two.status_code == 200
    assert one.json()["event_id"] == two.json()["event_id"]


def test_stream_conflict_returns_409(client: TestClient) -> None:
    # force stale expected_version path through dedicated test helper endpoint
    bad = client.post("/api/v2/test/force-conflict", json={"thread_id": "t1"})
    assert bad.status_code == 409


def test_approval_gate_blocks_agent_run_until_granted(client: TestClient) -> None:
    seed = seed_thread_with_pending_approval(client)
    start = client.post(
        f"/api/v2/threads/{seed['thread_id']}/agent-plan/start",
        headers={"Idempotency-Key": "start-1"},
    )
    assert start.status_code == 200

    timeline_before = client.get(f"/api/v2/threads/{seed['thread_id']}/timeline").json()["items"]
    assert not any(i["event_type"] == "AgentStepCompleted" for i in timeline_before)

    grant = client.post(f"/api/v2/approvals/{seed['approval_id']}/grant", headers={"Idempotency-Key": "grant-1"})
    assert grant.status_code == 200

    timeline_after = client.get(f"/api/v2/threads/{seed['thread_id']}/timeline").json()["items"]
    assert any(i["event_type"] == "AgentStepCompleted" for i in timeline_after)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py -v`  
Expected: FAIL with missing conflict/gate paths or incorrect idempotency behavior.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/api.py
@app.exception_handler(ValueError)
async def value_error_to_http(_request, exc: ValueError):
    message = str(exc)
    if "stream version conflict" in message:
        return JSONResponse(status_code=409, content={"detail": message})
    return JSONResponse(status_code=400, content={"detail": message})
```

```python
# ensure every mutation path uses require_idempotency + command dedup lookup
# ensure orchestrator only emits AgentStep* after ApprovalGranted event
```

**Step 4: Run test to verify it passes + run full targeted suite**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_event_store.py 09-tools/tests/test_vm_webapp_commands_v2.py 09-tools/tests/test_vm_webapp_projectors_v2.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py 09-tools/tests/test_vm_webapp_agent_runtime_v2.py 09-tools/tests/test_vm_webapp_api_v2.py 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_ui_assets.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_api_v2.py 09-tools/vm_webapp/api.py
git commit -m "test(vm-webapp): verify v2 event-driven flow reliability and gates"
```

---

## Final Verification Checklist

1. Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py -v`
2. Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py -v`
3. Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`
4. Run: `uv run python -m pytest 09-tools/tests -v`
5. Manual smoke: start server and validate create Brand -> Project -> Thread -> add modes -> propose/start plan -> approve -> see timeline and artifacts.

