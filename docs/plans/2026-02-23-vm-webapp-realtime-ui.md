# VM Web App Realtime UI (Chat + Runs + SSE) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Entregar uma UI funcional para chat e runs foundation com atualização em tempo real via SSE e gate de aprovação.

**Architecture:** O backend FastAPI expõe endpoints para produtos, runs, aprovação e stream de eventos por run. O `RunEngine` permanece responsável pela execução e gates, enquanto a UI em `09-tools/web/vm/app.js` consome APIs REST + EventSource para renderizar chat, timeline e ações. O fluxo híbrido de start (`/run foundation` + botão) é resolvido no frontend com endpoint único no backend.

**Tech Stack:** Python 3.12, FastAPI/TestClient, SQLAlchemy/SQLite, EventSource (SSE), JavaScript vanilla, pytest.

---

## Pre-Flight Notes

- Execute em branch/worktree isolado.
- Siga TDD estrito em cada task: RED -> GREEN -> COMMIT.
- Preserve escopo YAGNI deste estágio:
  - stack fixa `06-stacks/foundation-stack/stack.yaml`
  - gate com `Approve` somente
  - sem retry/edit/autenticação.

## Task 1: Products API by Brand

**Files:**
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write the failing test**

Add test:

```python
def test_list_products_by_brand() -> None:
    app = create_app()
    ws = app.state.workspace
    engine = app.state.engine

    with session_scope(engine) as session:
        create_brand(session, brand_id="b1", name="Acme", canonical={}, ws=ws, soul_md="")
        create_product(
            session,
            brand_id="b1",
            product_id="p1",
            name="Widget",
            canonical={},
            ws=ws,
            essence_md="",
        )

    client = TestClient(app)
    res = client.get("/api/v1/products", params={"brand_id": "b1"})
    assert res.status_code == 200
    assert res.json()["products"][0]["product_id"] == "p1"
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_list_products_by_brand -v`
Expected: FAIL (`404` or missing endpoint/helper).

**Step 3: Write minimal implementation**

- Add in `repo.py`:

```python
def list_products_by_brand(session: Session, brand_id: str) -> list[Product]:
    return list(
        session.scalars(
            select(Product)
            .where(Product.brand_id == brand_id)
            .order_by(Product.product_id.asc())
        )
    )
```

- Add in `api.py` endpoint:

```python
@router.get("/products")
def products(brand_id: str, request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_products_by_brand(session, brand_id)
    return {
        "products": [
            {"product_id": row.product_id, "brand_id": row.brand_id, "name": row.name}
            for row in rows
        ]
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_list_products_by_brand -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add products api filtered by brand"
```

## Task 2: Start Foundation Run + List Runs API

**Files:**
- Modify: `09-tools/vm_webapp/app.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_start_foundation_run_returns_run_id_and_status() -> None:
    app = create_app()
    client = TestClient(app)

    res = client.post(
        "/api/v1/runs/foundation",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": "t1",
            "user_request": "crm para clinicas",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["run_id"]
    assert body["status"] in {"running", "waiting_approval", "completed"}


def test_list_runs_by_thread() -> None:
    app = create_app()
    client = TestClient(app)

    start = client.post(
        "/api/v1/runs/foundation",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": "thread-xyz",
            "user_request": "crm para clinicas",
        },
    )
    assert start.status_code == 200

    res = client.get("/api/v1/runs", params={"thread_id": "thread-xyz"})
    assert res.status_code == 200
    assert len(res.json()["runs"]) >= 1
```

**Step 2: Run tests to verify they fail**

Run:
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_start_foundation_run_returns_run_id_and_status -v`
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_list_runs_by_thread -v`

Expected: FAIL (missing endpoints/run engine wiring).

**Step 3: Write minimal implementation**

- In `app.py`, create and store run engine:

```python
from vm_webapp.run_engine import RunEngine

run_engine = RunEngine(engine=engine, workspace=workspace, memory=memory, llm=llm)
app.state.run_engine = run_engine
```

- In `repo.py` add query helper:

```python
def list_runs_by_thread(session: Session, thread_id: str) -> list[Run]:
    return list(
        session.scalars(
            select(Run)
            .where(Run.thread_id == thread_id)
            .order_by(Run.created_at.desc())
        )
    )
```

- In `api.py` add:
  - `POST /api/v1/runs/foundation` (stack fixo)
  - `GET /api/v1/runs?thread_id=...`

Use `run_engine.start_run(...)` + `run_engine.run_until_gate(run_id)`.

**Step 4: Run tests to verify they pass**

Run:
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_start_foundation_run_returns_run_id_and_status -v`
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_list_runs_by_thread -v`

Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/app.py 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add foundation run start and run listing api"
```

## Task 3: Approve Gate Flow in RunEngine + API

**Files:**
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/vm_webapp/run_engine.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_run_engine.py`
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write failing tests**

- In `test_vm_webapp_run_engine.py`:

```python
def test_approve_waiting_stage_continues_run(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path / "ws")
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    memory = MemoryIndex(root=tmp_path / "zvec")
    run_engine = RunEngine(engine=engine, workspace=ws, memory=memory, llm=None)

    run = run_engine.start_run(
        brand_id="b1",
        product_id="p1",
        thread_id="t1",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        user_request="crm para clinicas",
    )
    run_engine.run_until_gate(run.run_id)
    run_engine.approve_and_continue(run.run_id)

    updated = run_engine.get_run(run.run_id)
    assert updated.status in {"waiting_approval", "completed"}
```

- In `test_vm_webapp_api.py`:

```python
def test_approve_endpoint_continues_waiting_run() -> None:
    app = create_app()
    client = TestClient(app)

    start = client.post(
        "/api/v1/runs/foundation",
        json={"brand_id": "b1", "product_id": "p1", "thread_id": "t1", "user_request": "crm"},
    )
    run_id = start.json()["run_id"]

    res = client.post(f"/api/v1/runs/{run_id}/approve")
    assert res.status_code == 200
    assert res.json()["run_id"] == run_id
```

**Step 2: Run tests to verify they fail**

Run:
- `pytest 09-tools/tests/test_vm_webapp_run_engine.py::test_approve_waiting_stage_continues_run -v`
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_approve_endpoint_continues_waiting_run -v`

Expected: FAIL (missing approve flow).

**Step 3: Write minimal implementation**

- In `repo.py` add helper:

```python
def get_waiting_stage(session: Session, run_id: str) -> Stage | None:
    return session.scalar(
        select(Stage)
        .where(Stage.run_id == run_id, Stage.status == "waiting_approval")
        .order_by(Stage.position.asc())
    )
```

- In `run_engine.py` add method `approve_and_continue(run_id: str)`:
  - locate waiting stage
  - execute stage gated
  - mark stage `completed`
  - emit `stage_completed`
  - continue fluxo normal até próximo gate/completed.

- In `api.py` add `POST /api/v1/runs/{run_id}/approve`.

**Step 4: Run tests to verify they pass**

Run:
- `pytest 09-tools/tests/test_vm_webapp_run_engine.py::test_approve_waiting_stage_continues_run -v`
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_approve_endpoint_continues_waiting_run -v`

Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/run_engine.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_run_engine.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add run approval flow for waiting gates"
```

## Task 4: SSE Events Endpoint for Run Timeline

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write failing test**

```python
def test_run_events_sse_streams_existing_events() -> None:
    app = create_app()
    ws = app.state.workspace
    run_id = "run-abc"
    events_path = ws.root / "runs" / run_id / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        '{"type":"run_started","run_id":"run-abc"}\n',
        encoding="utf-8",
    )

    client = TestClient(app)
    with client.stream(
        "GET",
        f"/api/v1/runs/{run_id}/events",
        params={"from_start": "true", "max_events": 1},
    ) as res:
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        first = next(res.iter_text())
        assert "run_started" in first
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_run_events_sse_streams_existing_events -v`
Expected: FAIL (missing SSE endpoint).

**Step 3: Write minimal implementation**

Add endpoint:

```python
@router.get("/runs/{run_id}/events")
def run_events(run_id: str, request: Request, from_start: bool = False, max_events: int = 100):
    ...
    return StreamingResponse(event_iter(), media_type="text/event-stream")
```

`event_iter()` should:
- tail `runtime/vm/runs/<run_id>/events.jsonl`
- emit lines as `data: <json>\n\n`
- obey `max_events` to make tests deterministic.

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_run_events_sse_streams_existing_events -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add sse endpoint for run events"
```

## Task 5: UI Structure for Chat + Run Controls

**Files:**
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/styles.css`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py` (new)

**Step 1: Write failing asset tests**

Create `test_vm_webapp_ui_assets.py`:

```python
from pathlib import Path


def test_vm_index_contains_chat_and_run_controls() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="chat-form"' in html
    assert 'id="chat-input"' in html
    assert 'id="start-foundation-run"' in html
    assert 'id="runs-timeline"' in html
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`
Expected: FAIL (IDs/structure missing).

**Step 3: Write minimal implementation**

Update `index.html` with:
- `#brand-select`, `#product-select`
- chat list `#chat-messages`
- form `#chat-form` + input `#chat-input`
- button `#start-foundation-run`
- timeline `#runs-timeline`
- status area `#run-status`

Adjust `styles.css` for readable layout and state badges.

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat: add vm ui structure for chat and run controls"
```

## Task 6: Frontend API Integration (Brands/Products/Chat + `/run foundation`)

**Files:**
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write failing tests for JS integration markers**

Add tests:

```python
def test_vm_app_js_calls_expected_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v1/brands" in js
    assert "/api/v1/products" in js
    assert "/api/v1/chat" in js
    assert "/api/v1/runs/foundation" in js


def test_vm_app_js_supports_run_slash_command() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/run foundation" in js
```

**Step 2: Run tests to verify they fail**

Run:
- `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_calls_expected_endpoints -v`
- `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_supports_run_slash_command -v`

Expected: FAIL

**Step 3: Write minimal implementation**

In `app.js`:
- bootstrapping:
  - fetch brands
  - on brand change fetch products
  - generate/persist `thread_id`
- chat submit:
  - if message starts with `/run foundation`, call start run endpoint
  - else call `/api/v1/chat`
- append messages to `#chat-messages`.

**Step 4: Run tests to verify they pass**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat: wire vm frontend chat and hybrid run start"
```

## Task 7: Frontend Realtime Runs Panel + Approve Action

**Files:**
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write failing tests**

- JS marker tests:

```python
def test_vm_app_js_uses_eventsource_and_approve_api() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "new EventSource" in js
    assert "/events" in js
    assert "/approve" in js
```

- API integration test:

```python
def test_run_listing_includes_stages_for_panel() -> None:
    app = create_app()
    client = TestClient(app)

    start = client.post(
        "/api/v1/runs/foundation",
        json={"brand_id": "b1", "product_id": "p1", "thread_id": "t-ui", "user_request": "crm"},
    )
    run_id = start.json()["run_id"]

    res = client.get("/api/v1/runs", params={"thread_id": "t-ui"})
    assert res.status_code == 200
    assert any(r["run_id"] == run_id for r in res.json()["runs"])
    assert "stages" in res.json()["runs"][0]
```

**Step 2: Run tests to verify they fail**

Run:
- `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_uses_eventsource_and_approve_api -v`
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_run_listing_includes_stages_for_panel -v`

Expected: FAIL

**Step 3: Write minimal implementation**

- `GET /api/v1/runs` should include stage list/status per run.
- `app.js` should:
  - load runs for thread
  - render timeline in `#runs-timeline`
  - open SSE for active run
  - on `approval_required`, render `Approve` button
  - call `POST /api/v1/runs/{run_id}/approve` and refresh list/stream.

**Step 4: Run tests to verify they pass**

Run:
- `pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`
- `pytest 09-tools/tests/test_vm_webapp_api.py::test_run_listing_includes_stages_for_panel -v`

Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/web/vm/app.js 09-tools/vm_webapp/api.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add realtime runs panel with approve action"
```

## Task 8: Final Verification

**Files:**
- No code changes expected (unless fix needed)

**Step 1: Run focused VM webapp tests**

Run:

```bash
pytest 09-tools/tests/test_vm_webapp_api.py -v
pytest 09-tools/tests/test_vm_webapp_run_engine.py -v
pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v
```

Expected: PASS

**Step 2: Run full test suite**

Run: `pytest 09-tools/tests -v`
Expected: PASS

**Step 3: Manual smoke**

Run:

```bash
uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766
```

Manual checks:
- abrir UI
- enviar chat normal
- enviar `/run foundation`
- clicar `Start Foundation Run`
- observar `approval_required`
- clicar `Approve` e confirmar continuidade

**Step 4: Commit only if fixes were needed**

```bash
git add <only-fixed-files>
git commit -m "fix: stabilize vm realtime ui integration"
```

**Step 5: Handoff**

Documentar no resumo final:
- endpoints adicionados
- comportamento da UI
- evidências de teste + smoke
- limitações que ficaram fora do escopo.
