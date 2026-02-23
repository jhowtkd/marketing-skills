# VM Web App Inteligente Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a local-first FastAPI web app that manages Brand/Product profiles (soul/essence), runs all stacks with approval gates, and uses automatic RAG (zvec) before every Kimi generation.

**Architecture:** FastAPI (ASGI) backend serving a static UI + JSON API. SQLite stores relational state and the filesystem stores blobs (markdown, artifacts, logs). zvec is a semantic index used for retrieval only. A background run engine executes stack stages and publishes events over SSE.

**Tech Stack:** Python 3.12 (via uv), FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy (SQLite), pytest, httpx, zvec.

---

## Pre-Flight Notes

- The repo currently runs on Python 3.9.6. zvec requires Python 3.10-3.12, so this plan standardizes on Python 3.12 for the web app runtime.
- Implementation should happen in a dedicated branch/worktree. Keep changes scoped; avoid refactors unrelated to the web app.
- Keep the current `09-tools/*` CLIs working; the web app is additive.

## Proposed Code Layout (new)

- Create: `09-tools/vm_webapp/__init__.py`
- Create: `09-tools/vm_webapp/app.py` (FastAPI app factory)
- Create: `09-tools/vm_webapp/settings.py` (env/config)
- Create: `09-tools/vm_webapp/workspace.py` (filesystem layout helpers)
- Create: `09-tools/vm_webapp/db.py` (SQLite engine + session)
- Create: `09-tools/vm_webapp/models.py` (SQLAlchemy models)
- Create: `09-tools/vm_webapp/repo.py` (CRUD functions)
- Create: `09-tools/vm_webapp/memory.py` (zvec index + retrieval)
- Create: `09-tools/vm_webapp/llm.py` (Kimi OpenAI-compatible client)
- Create: `09-tools/vm_webapp/stacking.py` (stack loader + stage contracts)
- Create: `09-tools/vm_webapp/run_engine.py` (execute runs + gates)
- Create: `09-tools/vm_webapp/events.py` (event bus + SSE helpers)
- Create: `09-tools/vm_webapp/api.py` (API router)
- Create: `09-tools/vm_webapp/__main__.py` (CLI `serve`)
- Create: `09-tools/web/vm/index.html`
- Create: `09-tools/web/vm/styles.css`
- Create: `09-tools/web/vm/app.js`

## Test Layout (new)

- Create: `09-tools/tests/test_vm_webapp_workspace.py`
- Create: `09-tools/tests/test_vm_webapp_repo.py`
- Create: `09-tools/tests/test_vm_webapp_memory.py`
- Create: `09-tools/tests/test_vm_webapp_llm.py`
- Create: `09-tools/tests/test_vm_webapp_run_engine.py`
- Create: `09-tools/tests/test_vm_webapp_api.py`

## Task 1: Set Up Python 3.12 + uv + deps

**Files:**
- Create: `pyproject.toml`
- Modify: `.gitignore`
- Create: `.env.example`

**Step 1: Add `pyproject.toml` (failing import check)**

Create `pyproject.toml` with (minimal) dependencies:

```toml
[project]
name = "marketing-skills"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "pydantic-settings>=2.2",
  "sqlalchemy>=2.0",
  "httpx>=0.27",
  "zvec>=0.1",
]

[tool.pytest.ini_options]
testpaths = ["09-tools/tests"]
```

**Step 2: Add `.env.example`**

```env
# Kimi OpenAI-compatible
KIMI_BASE_URL=https://api.kimi.com/coding/v1
KIMI_MODEL=kimi-for-coding
KIMI_API_KEY=

# Workspace
VM_WORKSPACE_ROOT=runtime/vm
VM_DB_PATH=runtime/vm/workspace.sqlite3
```

**Step 3: Ignore runtime data**

Add to `.gitignore`:

```gitignore
runtime/
```

**Step 4: Install Python + deps**

Run:

```bash
uv --version
uv python install 3.12
uv venv --python 3.12
uv pip install -r 09-tools/requirements.txt
uv pip install -e .
```

Expected: `python -c "import fastapi; import zvec"` exits `0`.

**Step 5: Commit**

```bash
git add pyproject.toml .env.example .gitignore
git commit -m "chore: add pyproject, uv runtime config"
```

## Task 2: Workspace Layout Helper (filesystem)

**Files:**
- Create: `09-tools/vm_webapp/workspace.py`
- Test: `09-tools/tests/test_vm_webapp_workspace.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.workspace import Workspace


def test_workspace_paths(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path)
    brand_id = "b1"
    product_id = "p1"

    assert ws.brand_dir(brand_id) == tmp_path / "brands" / brand_id
    assert ws.brand_soul_path(brand_id).name == "soul.md"
    assert ws.product_essence_path(brand_id, product_id).name == "essence.md"
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_workspace.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vm_webapp'` (or missing symbols).

**Step 3: Write minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path

    def brand_dir(self, brand_id: str) -> Path:
        return self.root / "brands" / brand_id

    def brand_soul_path(self, brand_id: str) -> Path:
        return self.brand_dir(brand_id) / "soul.md"

    def product_dir(self, brand_id: str, product_id: str) -> Path:
        return self.brand_dir(brand_id) / "products" / product_id

    def product_essence_path(self, brand_id: str, product_id: str) -> Path:
        return self.product_dir(brand_id, product_id) / "essence.md"
```

Also create `09-tools/vm_webapp/__init__.py` to make `vm_webapp` importable.

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_workspace.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/__init__.py 09-tools/vm_webapp/workspace.py 09-tools/tests/test_vm_webapp_workspace.py
git commit -m "feat: add workspace path helpers"
```

## Task 3: SQLite DB + Models (Brand/Product/Thread/Run)

**Files:**
- Create: `09-tools/vm_webapp/db.py`
- Create: `09-tools/vm_webapp/models.py`
- Test: `09-tools/tests/test_vm_webapp_repo.py`

**Step 1: Write failing test (create schema + insert Brand)**

```python
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import create_brand, list_brands


def test_brand_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    engine = build_engine(db_path)
    init_db(engine)

    with session_scope(engine) as session:
        create_brand(session, brand_id="b1", name="Acme", canonical={"tone": "pragmatic"})

    with session_scope(engine) as session:
        brands = list_brands(session)
        assert len(brands) == 1
        assert brands[0].brand_id == "b1"
        assert brands[0].name == "Acme"
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_repo.py::test_brand_roundtrip -v`
Expected: FAIL (missing `db.py/models.py/repo.py`).

**Step 3: Minimal implementation**

- `db.py`:
  - `build_engine(db_path: Path) -> Engine`
  - `init_db(engine) -> None` calling `Base.metadata.create_all(engine)`
  - `session_scope(engine)` context manager (commit/rollback/close)
- `models.py`:
  - SQLAlchemy `Base`
  - `Brand` table with `brand_id` (PK), `name`, `canonical_json`, `created_at`, `updated_at`

Example `Brand` model:

```python
from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text


class Base(DeclarativeBase):
    pass


class Brand(Base):
    __tablename__ = "brands"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(32), default=lambda: datetime.utcnow().isoformat())
    updated_at: Mapped[str] = mapped_column(String(32), default=lambda: datetime.utcnow().isoformat())
```

Also create `repo.py` with `create_brand` and `list_brands`.

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_repo.py::test_brand_roundtrip -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/db.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_repo.py
git commit -m "feat: add sqlite db and brand model"
```

## Task 4: Brand/Product CRUD + soul/essence files

**Files:**
- Modify: `09-tools/vm_webapp/models.py` (add `Product`)
- Modify: `09-tools/vm_webapp/repo.py` (CRUD)
- Modify: `09-tools/vm_webapp/workspace.py` (helpers if needed)
- Test: `09-tools/tests/test_vm_webapp_repo.py`

**Step 1: Add failing tests**

```python
from pathlib import Path

from vm_webapp.workspace import Workspace
from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import create_brand, create_product, get_product


def test_create_brand_writes_soul(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path)
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_brand(session, brand_id="b1", name="Acme", canonical={"tone": "pragmatic"}, ws=ws, soul_md="# Soul\\n")

    assert ws.brand_soul_path("b1").read_text(encoding="utf-8").startswith("# Soul")


def test_create_product_writes_essence(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path)
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_brand(session, brand_id="b1", name="Acme", canonical={}, ws=ws, soul_md="")
        create_product(session, brand_id="b1", product_id="p1", name="Widget", canonical={}, ws=ws, essence_md="# Essence\\n")

    assert ws.product_essence_path("b1", "p1").read_text(encoding="utf-8") == "# Essence\\n"
    with session_scope(engine) as session:
        product = get_product(session, product_id="p1")
        assert product is not None
        assert product.name == "Widget"
```

**Step 2: Run tests to verify they fail**

Run: `pytest 09-tools/tests/test_vm_webapp_repo.py -v`
Expected: FAIL (missing Product model + file writes).

**Step 3: Implement minimal Product model + repo functions**

- Add `Product` model (`product_id` PK, `brand_id` FK-like string, `name`, `canonical_json`, timestamps)
- Update repo layer:
  - `create_brand(..., ws: Workspace, soul_md: str) -> Brand`
  - `create_product(..., ws: Workspace, essence_md: str) -> Product`
  - `get_product(session, product_id) -> Product | None`
- Ensure filesystem writes:
  - create parent dirs
  - write UTF-8

**Step 4: Run tests to verify pass**

Run: `pytest 09-tools/tests/test_vm_webapp_repo.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_repo.py
git commit -m "feat: add product model and filesystem soul/essence storage"
```

## Task 5: Memory Index (zvec) + Retrieval

**Files:**
- Create: `09-tools/vm_webapp/memory.py`
- Test: `09-tools/tests/test_vm_webapp_memory.py`

**Step 1: Write failing test (index soul and retrieve)**

```python
from pathlib import Path

from vm_webapp.memory import MemoryIndex


def test_memory_index_retrieves_brand_soul(tmp_path: Path) -> None:
    index = MemoryIndex(root=tmp_path / "zvec")
    index.upsert_doc(
        doc_id="brand:b1:soul",
        text="Acme speaks with calm, evidence-led clarity.",
        meta={"brand_id": "b1", "kind": "soul"},
    )

    hits = index.search("evidence clarity", filters={"brand_id": "b1"}, top_k=3)
    assert hits
    assert "evidence-led" in hits[0].text
```

**Step 2: Run to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_memory.py -v`
Expected: FAIL (missing MemoryIndex).

**Step 3: Implement minimal MemoryIndex**

Implement:

- `MemoryIndex(root: Path)`
- `upsert_doc(doc_id: str, text: str, meta: dict) -> None`
- `search(query: str, *, filters: dict, top_k: int) -> list[Hit]`

Important: implement a fallback mode if dense embeddings are unavailable:

- default: BM25/sparse (no model download)
- optional: sentence-transformers dense when installed/configured

**Step 4: Run to verify pass**

Run: `pytest 09-tools/tests/test_vm_webapp_memory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/memory.py 09-tools/tests/test_vm_webapp_memory.py
git commit -m "feat: add zvec-backed memory index with filters"
```

## Task 6: Kimi OpenAI-Compatible Client (httpx)

**Files:**
- Create: `09-tools/vm_webapp/llm.py`
- Test: `09-tools/tests/test_vm_webapp_llm.py`

**Step 1: Write failing test using httpx MockTransport**

```python
import json
import httpx

from vm_webapp.llm import KimiClient


def test_kimi_chat_completions_request_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "kimi-for-coding"
        assert payload["messages"][-1]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            },
        )

    transport = httpx.MockTransport(handler)
    client = KimiClient(base_url="https://api.kimi.com/coding/v1", api_key="sk-test", transport=transport)
    out = client.chat(
        model="kimi-for-coding",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_tokens=128,
    )
    assert out == "ok"
```

**Step 2: Run and confirm failure**

Run: `pytest 09-tools/tests/test_vm_webapp_llm.py -v`
Expected: FAIL (missing client).

**Step 3: Implement minimal client**

Implement:

- `KimiClient(..., transport: httpx.BaseTransport | None = None)`
- `chat(...) -> str`
- POST to `{base_url}/chat/completions` with OpenAI-style payload
- Header: `Authorization: Bearer <api_key>`

**Step 4: Run and confirm pass**

Run: `pytest 09-tools/tests/test_vm_webapp_llm.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/llm.py 09-tools/tests/test_vm_webapp_llm.py
git commit -m "feat: add kimi openai-compatible client"
```

## Task 7: Stack Loader + Stage Contract + Prompt Builder (Context Pack)

**Files:**
- Create: `09-tools/vm_webapp/stacking.py`
- Modify: `09-tools/vm_webapp/memory.py` (helpers for chunk meta if needed)
- Test: `09-tools/tests/test_vm_webapp_run_engine.py`

**Step 1: Write failing test (build context pack includes soul/essence + retrieved)**

```python
from pathlib import Path

from vm_webapp.stacking import build_context_pack


def test_context_pack_contains_canonical_and_retrieved(tmp_path: Path) -> None:
    ctx = build_context_pack(
        brand_soul_md="# Soul\\nAcme: evidence-led.",
        product_essence_md="# Essence\\nWidget: simple.",
        retrieved=[{"title": "old run", "text": "We tried X and it failed."}],
        stage_contract="Write output in Markdown.",
        user_request="Create landing copy.",
    )
    assert "Acme: evidence-led." in ctx
    assert "Widget: simple." in ctx
    assert "We tried X and it failed." in ctx
```

**Step 2: Run failing test**

Run: `pytest 09-tools/tests/test_vm_webapp_run_engine.py::test_context_pack_contains_canonical_and_retrieved -v`
Expected: FAIL (missing build_context_pack).

**Step 3: Implement minimal builder**

- `load_stack(path: str) -> dict` (reuse `09-tools/stack_loader.py` or duplicate minimal)
- `build_context_pack(...) -> str` string that concatenates sections deterministically

**Step 4: Run passing**

Run: `pytest 09-tools/tests/test_vm_webapp_run_engine.py::test_context_pack_contains_canonical_and_retrieved -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/stacking.py 09-tools/tests/test_vm_webapp_run_engine.py
git commit -m "feat: add stack parsing and context pack builder"
```

## Task 8: Run Engine (generic) + Gates + Artifacts + Event Log

**Files:**
- Create: `09-tools/vm_webapp/run_engine.py`
- Create: `09-tools/vm_webapp/events.py`
- Modify: `09-tools/vm_webapp/models.py` (Run/Stage tables)
- Modify: `09-tools/vm_webapp/repo.py` (Run CRUD)
- Test: `09-tools/tests/test_vm_webapp_run_engine.py`

**Step 1: Write failing test (run pauses at approval_required)**

```python
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.workspace import Workspace
from vm_webapp.run_engine import RunEngine
from vm_webapp.memory import MemoryIndex


def test_run_pauses_on_gate(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path / "ws")
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    memory = MemoryIndex(root=tmp_path / "zvec")

    # Minimal: use foundation stack which has approval_required stages.
    run_engine = RunEngine(
        engine=engine,
        workspace=ws,
        memory=memory,
        llm=None,  # stage runner can be stubbed for this test
    )

    run = run_engine.start_run(
        brand_id="b1",
        product_id="p1",
        thread_id="t1",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        user_request="crm para clinicas",
    )
    run_engine.run_until_gate(run.run_id)
    run2 = run_engine.get_run(run.run_id)
    assert run2.status == "waiting_approval"
```

**Step 2: Run and confirm failure**

Run: `pytest 09-tools/tests/test_vm_webapp_run_engine.py::test_run_pauses_on_gate -v`
Expected: FAIL (missing models/engine).

**Step 3: Implement minimal Run/Stage storage + engine**

- Models:
  - `Run` with `run_id`, `thread_id`, `stack_path`, `status`, timestamps
  - `Stage` with `run_id`, `stage_id`, `status`, `attempts`, `approval_required`
- Engine:
  - `start_run(...)` populates stages from stack.yaml
  - `run_until_gate(run_id)` iterates stages; on `approval_required`, stop
  - For V1: stage execution can be stubbed to write placeholder markdown artifact per stage
  - Persist artifact file under `runtime/vm/runs/<run_id>/artifacts/...`
  - Append events to `events.jsonl`

**Step 4: Run and confirm pass**

Run: `pytest 09-tools/tests/test_vm_webapp_run_engine.py::test_run_pauses_on_gate -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/run_engine.py 09-tools/vm_webapp/events.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_run_engine.py
git commit -m "feat: add generic run engine with approval gates"
```

## Task 9: FastAPI App + API Router + SSE

**Files:**
- Create: `09-tools/vm_webapp/settings.py`
- Create: `09-tools/vm_webapp/app.py`
- Create: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Write failing API test (health + brand list)**

```python
from fastapi.testclient import TestClient

from vm_webapp.app import create_app


def test_api_health_and_list_brands() -> None:
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True

    res = client.get("/api/v1/brands")
    assert res.status_code == 200
    assert res.json()["brands"] == []
```

**Step 2: Run failing test**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py -v`
Expected: FAIL (missing app).

**Step 3: Implement minimal FastAPI app**

- `settings.py`: read env vars (workspace root, db path, kimi config)
- `app.py`: `create_app()` wires settings, db init, and router
- `api.py`: endpoints:
  - `GET /api/v1/health`
  - `GET /api/v1/brands` (empty list if none)

**Step 4: Run passing**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/settings.py 09-tools/vm_webapp/app.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add fastapi app and initial api"
```

## Task 10: Serve Static UI (V1)

**Files:**
- Create: `09-tools/web/vm/index.html`
- Create: `09-tools/web/vm/styles.css`
- Create: `09-tools/web/vm/app.js`
- Modify: `09-tools/vm_webapp/app.py` (static mount)
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Add failing test (GET / returns HTML)**

```python
from fastapi.testclient import TestClient

from vm_webapp.app import create_app


def test_root_serves_ui() -> None:
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "VM Web App" in res.text
```

**Step 2: Run failing test**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_root_serves_ui -v`
Expected: FAIL

**Step 3: Implement minimal UI + static serving**

- Add `index.html` with placeholder layout:
  - Brand/Product selector
  - Chat panel
  - Runs panel
- Mount static files from `09-tools/web/vm/`

**Step 4: Run passing**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_root_serves_ui -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/web/vm/app.js 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: serve vm web ui static assets"
```

## Task 11: Wire Chat + Auto-RAG + Kimi Generation

**Files:**
- Modify: `09-tools/vm_webapp/api.py` (chat endpoint)
- Modify: `09-tools/vm_webapp/run_engine.py` (stage runner uses llm)
- Modify: `09-tools/vm_webapp/memory.py` (index artifacts on write)
- Test: `09-tools/tests/test_vm_webapp_api.py`

**Step 1: Add failing test (chat uses retrieval hook)**

Implement using a fake memory index + fake llm client in app dependency injection, then assert the retrieved snippet appears in the prompt sent to llm (use MockTransport).

**Step 2: Run failing test**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py -v`
Expected: FAIL

**Step 3: Implement**

- `POST /api/v1/chat`:
  - accept `brand_id/product_id/thread_id/message`
  - run retrieval (`top_k`) and build context pack
  - call kimi client and return assistant message
  - append chat message to `chat.jsonl` and index it (optional)

**Step 4: Run passing**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/run_engine.py 09-tools/vm_webapp/memory.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add chat endpoint with auto-rag and kimi"
```

## Task 12: CLI `serve` (uvicorn)

**Files:**
- Create: `09-tools/vm_webapp/__main__.py`
- Test: `09-tools/tests/test_vm_webapp_api.py` (import smoke)

**Step 1: Add failing import test**

```python
def test_cli_module_imports() -> None:
    import vm_webapp.__main__  # noqa: F401
```

**Step 2: Run failing**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_cli_module_imports -v`
Expected: FAIL

**Step 3: Implement CLI**

Implement `python -m vm_webapp serve --host 127.0.0.1 --port 8766` that runs uvicorn with `create_app()`.

**Step 4: Run passing**

Run: `pytest 09-tools/tests/test_vm_webapp_api.py::test_cli_module_imports -v`
Expected: PASS

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/__main__.py 09-tools/tests/test_vm_webapp_api.py
git commit -m "feat: add vm webapp serve cli"
```

## Verification Checklist (end-to-end)

- Run unit tests: `pytest 09-tools/tests -v`
- Run server: `uv run python -m vm_webapp serve`
- Open UI, create Brand + Product, edit soul/essence, start a Foundation run, observe gate pause, approve, and see artifacts appear.

## Execution Choice

Plan complete. Two execution options:

1. **Subagent-Driven (this session)**: use superpowers:subagent-driven-development to implement task-by-task with reviews.
2. **Parallel Session**: open a new session and implement using superpowers:executing-plans, following this plan sequentially.

Which approach?

