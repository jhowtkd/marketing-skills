# VM Web App Brand Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a real Brand Workspace UI with brand tabs and product-scoped threads so chat and runs always operate on one active thread.

**Architecture:** Add a persisted `Thread` entity in SQLite and expose thread lifecycle APIs (`list/create/close/messages`). Keep the existing FastAPI + vanilla frontend stack and evolve the UI into a 3-panel workspace (Threads, Chat, Runs) scoped by brand tab and product filter. Enforce open-thread validation in backend endpoints so Kimi interactions always use a valid active thread.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), vanilla HTML/CSS/JS, pytest, uv.

---

### Task 1: Persist Thread Entity and Repository Operations

**Files:**
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/tests/test_vm_webapp_repo.py`

**Step 1: Write the failing test**

```python
def test_thread_roundtrip_and_close(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_thread(
            session,
            thread_id="t1",
            brand_id="b1",
            product_id="p1",
            title="Thread 1",
        )
        create_thread(
            session,
            thread_id="t2",
            brand_id="b1",
            product_id="p2",
            title="Thread 2",
        )

    with session_scope(engine) as session:
        rows = list_threads(session, brand_id="b1", product_id="p1")
        assert len(rows) == 1
        assert rows[0].thread_id == "t1"
        assert rows[0].status == "open"

        close_thread(session, thread_id="t1")
        thread = get_thread(session, thread_id="t1")
        assert thread is not None
        assert thread.status == "closed"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_repo.py::test_thread_roundtrip_and_close -v`  
Expected: FAIL with import/name errors for missing thread model/repo functions.

**Step 3: Write minimal implementation**

```python
class Thread(Base):
    __tablename__ = "threads"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    last_activity_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
```

```python
def create_thread(session: Session, *, thread_id: str, brand_id: str, product_id: str, title: str) -> Thread:
    thread = Thread(
        thread_id=thread_id,
        brand_id=brand_id,
        product_id=product_id,
        title=title,
        status="open",
    )
    session.add(thread)
    session.flush()
    return thread


def list_threads(session: Session, brand_id: str, product_id: str) -> list[Thread]:
    return list(
        session.scalars(
            select(Thread)
            .where(Thread.brand_id == brand_id, Thread.product_id == product_id)
            .order_by(Thread.last_activity_at.desc())
        )
    )


def get_thread(session: Session, thread_id: str) -> Thread | None:
    return session.get(Thread, thread_id)


def close_thread(session: Session, thread_id: str) -> None:
    session.execute(
        update(Thread)
        .where(Thread.thread_id == thread_id)
        .values(status="closed", updated_at=_now_iso())
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_repo.py::test_thread_roundtrip_and_close -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_repo.py
git commit -m "feat(vm-webapp): add thread entity and repository operations"
```

### Task 2: Add Thread Lifecycle APIs (list, create, close, messages)

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write the failing test**

```python
def test_thread_lifecycle_and_messages_api(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    created = client.post(
        "/api/v1/threads",
        json={"brand_id": "b1", "product_id": "p1", "title": "Discovery"},
    )
    assert created.status_code == 200
    thread_id = created.json()["thread_id"]

    listed = client.get("/api/v1/threads", params={"brand_id": "b1", "product_id": "p1"})
    assert listed.status_code == 200
    assert any(t["thread_id"] == thread_id for t in listed.json()["threads"])

    chat_path = tmp_path / "runtime" / "vm" / "threads" / thread_id / "chat.jsonl"
    chat_path.parent.mkdir(parents=True, exist_ok=True)
    chat_path.write_text('{"role":"user","content":"hello"}\n', encoding="utf-8")

    messages = client.get(f"/api/v1/threads/{thread_id}/messages")
    assert messages.status_code == 200
    assert messages.json()["messages"][0]["content"] == "hello"

    closed = client.post(f"/api/v1/threads/{thread_id}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api.py::test_thread_lifecycle_and_messages_api -v`  
Expected: FAIL with 404 for missing `/threads` endpoints.

**Step 3: Write minimal implementation**

```python
class ThreadCreateRequest(BaseModel):
    brand_id: str
    product_id: str
    title: str | None = None


@router.get("/threads")
def threads(brand_id: str, product_id: str, request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_threads(session, brand_id=brand_id, product_id=product_id)
    return {
        "threads": [
            {
                "thread_id": row.thread_id,
                "brand_id": row.brand_id,
                "product_id": row.product_id,
                "title": row.title,
                "status": row.status,
                "last_activity_at": row.last_activity_at,
            }
            for row in rows
        ]
    }


@router.post("/threads")
def create_thread_api(payload: ThreadCreateRequest, request: Request) -> dict[str, str]:
    thread_id = f"thread-{uuid4().hex[:12]}"
    title = payload.title or "New Thread"
    with session_scope(request.app.state.engine) as session:
        row = create_thread(
            session,
            thread_id=thread_id,
            brand_id=payload.brand_id,
            product_id=payload.product_id,
            title=title,
        )
    return {"thread_id": row.thread_id, "status": row.status, "title": row.title}


@router.post("/threads/{thread_id}/close")
def close_thread_api(thread_id: str, request: Request) -> dict[str, str]:
    with session_scope(request.app.state.engine) as session:
        row = get_thread(session, thread_id=thread_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        close_thread(session, thread_id=thread_id)
    return {"thread_id": thread_id, "status": "closed"}


@router.get("/threads/{thread_id}/messages")
def thread_messages(thread_id: str, request: Request) -> dict[str, list[dict[str, str]]]:
    chat_path = Path(request.app.state.workspace.root) / "threads" / thread_id / "chat.jsonl"
    if not chat_path.exists():
        return {"messages": []}
    messages: list[dict[str, str]] = []
    for line in chat_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return {"messages": messages}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api.py::test_thread_lifecycle_and_messages_api -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat(vm-webapp): add thread lifecycle api endpoints"
```

### Task 3: Enforce Open Thread Validation for Chat and Runs

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write the failing test**

```python
def test_chat_and_run_reject_closed_thread(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    created = client.post("/api/v1/threads", json={"brand_id": "b1", "product_id": "p1"})
    thread_id = created.json()["thread_id"]
    client.post(f"/api/v1/threads/{thread_id}/close")

    chat = client.post(
        "/api/v1/chat",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": thread_id,
            "message": "hello",
        },
    )
    assert chat.status_code == 409

    run = client.post(
        "/api/v1/runs/foundation",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": thread_id,
            "user_request": "start",
        },
    )
    assert run.status_code == 409
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api.py::test_chat_and_run_reject_closed_thread -v`  
Expected: FAIL because endpoints still accept closed threads.

**Step 3: Write minimal implementation**

```python
def _require_open_thread(session, *, thread_id: str, brand_id: str, product_id: str):
    row = get_thread(session, thread_id=thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
    if row.brand_id != brand_id or row.product_id != product_id:
        raise HTTPException(status_code=409, detail="thread context mismatch")
    if row.status != "open":
        raise HTTPException(status_code=409, detail=f"thread is {row.status}")
    return row
```

```python
with session_scope(request.app.state.engine) as session:
    _require_open_thread(
        session,
        thread_id=payload.thread_id,
        brand_id=payload.brand_id,
        product_id=payload.product_id,
    )
```

Also update thread activity timestamp after successful chat/run:

```python
def touch_thread_activity(session: Session, thread_id: str) -> None:
    session.execute(
        update(Thread)
        .where(Thread.thread_id == thread_id)
        .values(last_activity_at=_now_iso(), updated_at=_now_iso())
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api.py::test_chat_and_run_reject_closed_thread -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "fix(vm-webapp): require open thread for chat and foundation runs"
```

### Task 4: Build Brand Workspace UI Skeleton (Tabs + Threads Panel)

**Files:**
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/styles.css`
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_vm_index_contains_brand_workspace_thread_controls() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="brand-tabs"' in html
    assert 'id="new-thread-button"' in html
    assert 'id="threads-list"' in html
    assert 'id="close-thread-button"' in html
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_brand_workspace_thread_controls -v`  
Expected: FAIL because IDs are not in current HTML.

**Step 3: Write minimal implementation**

```html
<section class="panel">
  <nav id="brand-tabs" class="brand-tabs"></nav>
  <div class="toolbar">
    <label>Product <select id="product-select"></select></label>
    <button id="new-thread-button" type="button">Nova Thread</button>
  </div>
</section>

<section class="workspace-grid">
  <aside class="panel">
    <h2>Threads</h2>
    <button id="close-thread-button" type="button">Encerrar Thread</button>
    <div id="threads-list" class="threads-list"></div>
  </aside>
  <section class="panel">...</section>
  <section class="panel">...</section>
</section>
```

```css
.workspace-grid { display: grid; gap: 16px; grid-template-columns: 280px 1fr 1fr; }
.brand-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.thread-item.active { border-color: #111827; background: #f3f4f6; }
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_brand_workspace_thread_controls -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(vm-webapp): add brand workspace layout and thread panel skeleton"
```

### Task 5: Implement Frontend Thread State and API Wiring

**Files:**
- Modify: `09-tools/web/vm/app.js`
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_vm_app_js_supports_threads_api_and_workspace_state() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v1/threads" in js
    assert "/messages" in js
    assert "/close" in js
    assert "new-thread-button" in js
    assert "loadThreads(" in js
    assert "selectThread(" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_supports_threads_api_and_workspace_state -v`  
Expected: FAIL because thread endpoints/state handlers are missing.

**Step 3: Write minimal implementation**

```javascript
const ENDPOINT_THREADS = "/api/v1/threads";
const brandTabs = document.getElementById("brand-tabs");
const threadsList = document.getElementById("threads-list");
const newThreadButton = document.getElementById("new-thread-button");
const closeThreadButton = document.getElementById("close-thread-button");

let activeBrandId = "";
let activeThreadId = "";

async function loadThreads() {
  if (!activeBrandId || !productSelect.value) return;
  const body = await fetchJson(
    `${ENDPOINT_THREADS}?brand_id=${encodeURIComponent(activeBrandId)}&product_id=${encodeURIComponent(productSelect.value)}`
  );
  renderThreads(body.threads || []);
}

function selectThread(threadId) {
  activeThreadId = threadId;
  loadThreadMessages();
  loadRuns();
}
```

```javascript
async function createThread() {
  const body = await fetchJson(ENDPOINT_THREADS, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brand_id: activeBrandId, product_id: productSelect.value }),
  });
  activeThreadId = body.thread_id;
  await loadThreads();
  await loadThreadMessages();
}
```

```javascript
async function closeActiveThread() {
  if (!activeThreadId) return;
  await fetchJson(`${ENDPOINT_THREADS}/${encodeURIComponent(activeThreadId)}/close`, { method: "POST" });
  await loadThreads();
}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_supports_threads_api_and_workspace_state -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(vm-webapp): wire thread state and api in brand workspace ui"
```

### Task 6: Bind Chat/Run to Active Thread and Add Closed-State Guards in UI

**Files:**
- Modify: `09-tools/web/vm/app.js`
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_vm_app_js_disables_chat_and_run_when_thread_is_missing_or_closed() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "chatInput.disabled = true" in js
    assert "startRunButton.disabled = true" in js
    assert 'activeThread.status === "closed"' in js
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_disables_chat_and_run_when_thread_is_missing_or_closed -v`  
Expected: FAIL because closed-thread guard is not implemented in UI state transitions.

**Step 3: Write minimal implementation**

```javascript
function syncWorkspaceActions(activeThread) {
  const blocked = !activeThread || activeThread.status === "closed";
  chatInput.disabled = blocked;
  startRunButton.disabled = blocked;
}
```

Ensure both payload builders use active thread:

```javascript
const payload = {
  brand_id: activeBrandId,
  product_id: productSelect.value,
  thread_id: activeThreadId,
  message,
};
```

```javascript
const payload = {
  brand_id: activeBrandId,
  product_id: productSelect.value,
  thread_id: activeThreadId,
  user_request: userRequest,
};
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_disables_chat_and_run_when_thread_is_missing_or_closed -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "fix(vm-webapp): bind chat and run to active thread with closed-state guards"
```

### Task 7: Regression Verification and PR Preparation

**Files:**
- Verify only: `09-tools/tests/test_vm_webapp_repo.py`
- Verify only: `09-tools/tests/test_vm_webapp_api.py`
- Verify only: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Verify only: `09-tools/vm_webapp/api.py`
- Verify only: `09-tools/web/vm/app.js`

**Step 1: Run focused backend tests**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_repo.py 09-tools/tests/test_vm_webapp_api.py -q`  
Expected: PASS.

**Step 2: Run frontend asset tests**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py -q`  
Expected: PASS.

**Step 3: Run full project regression**

Run: `uv run python -m pytest -q`  
Expected: PASS with no regressions.

**Step 4: Confirm scoped diff**

Run: `git status --short`  
Expected: only intended files modified plus known local artifacts (`09-tools/marketing_skills.egg-info/`, `uv.lock`) left unstaged.

**Step 5: Push branch and open PR**

```bash
git push -u origin <feature-branch>
gh -R jhowtkd/marketing-skills pr create --fill
```

Expected: PR URL created with summary of brand tabs + threads + active-thread binding.

### Execution Notes

- Use @superpowers/test-driven-development at every task loop.
- Use @superpowers/verification-before-completion before claiming done.
- Keep YAGNI for MVP: no brand/product CRUD, no multi-product threads, no frontend framework migration.
