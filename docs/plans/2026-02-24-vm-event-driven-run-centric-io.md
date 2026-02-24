# VM Event-Driven Run-Centric IO Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a real thread-driven workflow where each request creates a run with stage-versioned artifacts (`.md`/`.json`) in workspace and auditable timeline events.

**Architecture:** Add a dedicated v2 workflow runtime that writes stage outputs with atomic manifests, emits workflow events into the event store, and is triggered by orchestrator processing of `WorkflowRunRequested`. Expose read endpoints to list runs and artifacts per thread/run and update the UI to operate as input/output workflow. Keep scope YAGNI: one default stage profile for MVP while preserving compatibility with existing run tables.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), event store/projectors v2, vanilla HTML/CSS/JS, pytest.

**Execution discipline:** Follow `@test-driven-development`, use `@systematic-debugging` for unexpected failures, and run `@verification-before-completion` before any success claim. Frequent commits per task.

---

### Task 1: Create Atomic Stage Artifact Writer

**Files:**
- Create: `09-tools/vm_webapp/artifacts.py`
- Test: `09-tools/tests/test_vm_webapp_artifacts.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.artifacts import write_stage_outputs


def test_write_stage_outputs_creates_manifest_with_hashes(tmp_path: Path) -> None:
    stage_dir = tmp_path / "runs" / "run-1" / "stages" / "01-plan"
    result = write_stage_outputs(
        stage_dir=stage_dir,
        run_id="run-1",
        thread_id="t1",
        stage_key="plan",
        stage_position=1,
        attempt=1,
        input_payload={"request_text": "Build plan"},
        output_payload={"summary": "Done"},
        artifacts={
            "plan.md": "# Plan\n\nOutput",
            "meta.json": "{\"ok\": true}",
        },
        event_id="evt-1",
        status="completed",
    )

    manifest = stage_dir / "manifest.json"
    assert manifest.exists()
    assert (stage_dir / "input.json").exists()
    assert (stage_dir / "output.json").exists()
    assert len(result["artifacts"]) == 2
    assert all(item["sha256"] for item in result["artifacts"])


def test_write_stage_outputs_uses_atomic_writes(tmp_path: Path) -> None:
    stage_dir = tmp_path / "runs" / "run-2" / "stages" / "01-plan"
    write_stage_outputs(
        stage_dir=stage_dir,
        run_id="run-2",
        thread_id="t2",
        stage_key="plan",
        stage_position=1,
        attempt=1,
        input_payload={"request_text": "Build plan"},
        output_payload={"summary": "Done"},
        artifacts={"plan.md": "# Plan"},
        event_id="evt-2",
        status="completed",
    )

    leftovers = list(stage_dir.rglob("*.tmp"))
    assert leftovers == []
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_artifacts.py -v`  
Expected: FAIL with `ModuleNotFoundError` for `vm_webapp.artifacts`.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/artifacts.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_stage_outputs(
    *,
    stage_dir: Path,
    run_id: str,
    thread_id: str,
    stage_key: str,
    stage_position: int,
    attempt: int,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    artifacts: dict[str, str],
    event_id: str,
    status: str,
) -> dict[str, Any]:
    artifacts_dir = stage_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    _write_text_atomic(stage_dir / "input.json", json.dumps(input_payload, ensure_ascii=False, indent=2))
    _write_text_atomic(stage_dir / "output.json", json.dumps(output_payload, ensure_ascii=False, indent=2))

    manifest_items: list[dict[str, Any]] = []
    for name, content in artifacts.items():
        data = content.encode("utf-8")
        file_path = artifacts_dir / name
        _write_text_atomic(file_path, content)
        manifest_items.append(
            {
                "path": str(file_path.relative_to(stage_dir)),
                "kind": file_path.suffix.lstrip("."),
                "sha256": _sha256_bytes(data),
                "size": len(data),
            }
        )

    manifest = {
        "run_id": run_id,
        "thread_id": thread_id,
        "stage_key": stage_key,
        "stage_position": stage_position,
        "attempt": attempt,
        "status": status,
        "event_id": event_id,
        "artifacts": manifest_items,
    }
    _write_text_atomic(stage_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_artifacts.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/artifacts.py 09-tools/tests/test_vm_webapp_artifacts.py
git commit -m "feat(vm-webapp): add atomic stage artifact writer"
```

### Task 2: Add Workflow Runtime v2 (Run + Stage + Stage IO)

**Files:**
- Create: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_workflow_runtime_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.memory import MemoryIndex
from vm_webapp.models import ThreadView
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace


def test_workflow_runtime_creates_run_and_stage_artifacts(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    workspace = Workspace(root=tmp_path / "runtime" / "vm")
    memory = MemoryIndex(root=tmp_path / "zvec")

    with session_scope(engine) as session:
        session.add(
            ThreadView(
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
                title="Planning",
                status="open",
                modes_json='["plan_90d"]',
            )
        )

    runtime = WorkflowRuntimeV2(engine=engine, workspace=workspace, memory=memory, llm=None)
    result = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Create campaign workflow",
        mode="plan_90d",
        actor_id="agent:vm-planner",
    )

    run_root = workspace.root / "runs" / result["run_id"]
    assert (run_root / "run.json").exists()
    manifests = list(run_root.glob("stages/*/manifest.json"))
    assert manifests


def test_workflow_runtime_never_overwrites_previous_run(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    workspace = Workspace(root=tmp_path / "runtime" / "vm")
    memory = MemoryIndex(root=tmp_path / "zvec")

    runtime = WorkflowRuntimeV2(engine=engine, workspace=workspace, memory=memory, llm=None)
    first = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Run one",
        mode="plan_90d",
        actor_id="agent:vm-planner",
    )
    second = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Run two",
        mode="plan_90d",
        actor_id="agent:vm-planner",
    )

    assert first["run_id"] != second["run_id"]
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py -v`  
Expected: FAIL because `WorkflowRuntimeV2` does not exist.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/workflow_runtime_v2.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import Engine

from vm_webapp.artifacts import write_stage_outputs
from vm_webapp.db import session_scope
from vm_webapp.events import EventEnvelope, now_iso
from vm_webapp.memory import MemoryIndex
from vm_webapp.repo import append_event, create_run, create_stage, update_run_status, update_stage_status
from vm_webapp.workspace import Workspace


class WorkflowRuntimeV2:
    def __init__(self, *, engine: Engine, workspace: Workspace, memory: MemoryIndex, llm: Any) -> None:
        self.engine = engine
        self.workspace = workspace
        self.memory = memory
        self.llm = llm

    def execute_thread_run(
        self,
        *,
        thread_id: str,
        brand_id: str,
        project_id: str,
        request_text: str,
        mode: str,
        actor_id: str,
    ) -> dict[str, str]:
        run_id = uuid4().hex[:16]
        stage_key = f"plan-{mode}"
        stage_dir = self.workspace.root / "runs" / run_id / "stages" / f"01-{stage_key}"

        with session_scope(self.engine) as session:
            create_run(
                session,
                run_id=run_id,
                brand_id=brand_id,
                product_id=project_id,
                thread_id=thread_id,
                stack_path="v2/workflow",
                user_request=request_text,
                status="running",
            )
            stage = create_stage(
                session,
                run_id=run_id,
                stage_id=stage_key,
                position=0,
                approval_required=False,
                status="running",
            )

            started = append_event(
                session,
                EventEnvelope(
                    event_id=f"evt-{uuid4().hex[:12]}",
                    event_type="WorkflowRunStarted",
                    aggregate_type="thread",
                    aggregate_id=thread_id,
                    stream_id=f"thread:{thread_id}",
                    expected_version=0,
                    actor_type="agent",
                    actor_id=actor_id,
                    payload={"thread_id": thread_id, "run_id": run_id, "mode": mode},
                    thread_id=thread_id,
                    brand_id=brand_id,
                    project_id=project_id,
                ),
            )

            artifact_text = f"# Workflow Output\n\nRequest: {request_text}\nMode: {mode}\n"
            manifest = write_stage_outputs(
                stage_dir=stage_dir,
                run_id=run_id,
                thread_id=thread_id,
                stage_key=stage_key,
                stage_position=1,
                attempt=1,
                input_payload={"request_text": request_text, "mode": mode},
                output_payload={"summary": "Workflow completed"},
                artifacts={"result.md": artifact_text},
                event_id=started.event_id,
                status="completed",
            )

            update_stage_status(session, stage_pk=stage.stage_pk, status="completed", attempts=1)
            update_run_status(session, run_id=run_id, status="completed")

        run_root = self.workspace.root / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / "run.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "brand_id": brand_id,
                    "project_id": project_id,
                    "mode": mode,
                    "status": "completed",
                    "created_at": now_iso(),
                    "manifest_paths": [str(stage_dir.relative_to(run_root) / "manifest.json")],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.memory.upsert_doc(
            doc_id=f"workflow:{run_id}",
            text=artifact_text,
            meta={"thread_id": thread_id, "run_id": run_id, "kind": "workflow_artifact"},
        )
        return {"run_id": run_id, "status": "completed", "manifest_count": str(len(manifest["artifacts"]))}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py
git commit -m "feat(vm-webapp): add v2 workflow runtime with stage-versioned artifacts"
```

### Task 3: Integrate Orchestrator v2 with WorkflowRunRequested

**Files:**
- Modify: `09-tools/vm_webapp/orchestrator_v2.py`
- Modify: `09-tools/vm_webapp/app.py`
- Test: `09-tools/tests/test_vm_webapp_orchestrator_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.orchestrator_v2 import process_new_events
from vm_webapp.repo import append_event, list_runs_by_thread, list_timeline_items_view
from vm_webapp.settings import Settings


def test_orchestrator_executes_workflow_run_requested_and_publishes_timeline(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )

    with session_scope(app.state.engine) as session:
        append_event(
            session,
            EventEnvelope(
                event_id="evt-run-request",
                event_type="WorkflowRunRequested",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                payload={
                    "thread_id": "t1",
                    "brand_id": "b1",
                    "project_id": "p1",
                    "request_text": "Build workflow output",
                    "mode": "plan_90d",
                },
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
            ),
        )
        process_new_events(session)

    with session_scope(app.state.engine) as session:
        runs = list_runs_by_thread(session, "t1")
        timeline = list_timeline_items_view(session, thread_id="t1")
        assert runs
        assert any(i.event_type == "WorkflowRunCompleted" for i in timeline)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_orchestrator_v2.py::test_orchestrator_executes_workflow_run_requested_and_publishes_timeline -v`  
Expected: FAIL because orchestrator does not process `WorkflowRunRequested`.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/app.py (wire runtime)
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2

workflow_runtime = WorkflowRuntimeV2(engine=engine, workspace=workspace, memory=memory, llm=llm)
app.state.workflow_runtime = workflow_runtime
```

```python
# 09-tools/vm_webapp/orchestrator_v2.py (new branch)
if event.event_type == "WorkflowRunRequested":
    payload = json.loads(event.payload_json)
    runtime = getattr(session.bind, "_workflow_runtime", None)
    # Prefer explicit runtime in app path; fallback injected callable in tests.
    executor = globals().get("_workflow_executor")
    if executor is None:
        raise ValueError("workflow runtime not configured")
    result = executor(
        thread_id=payload["thread_id"],
        brand_id=payload["brand_id"],
        project_id=payload["project_id"],
        request_text=payload["request_text"],
        mode=payload.get("mode", "plan_90d"),
        actor_id="agent:vm-workflow",
    )
    # emit completion event to timeline
    expected = get_stream_version(session, f"thread:{payload['thread_id']}")
    completed = append_event(
        session,
        EventEnvelope(
            event_id=f"evt-{uuid4().hex[:12]}",
            event_type="WorkflowRunCompleted",
            aggregate_type="thread",
            aggregate_id=payload["thread_id"],
            stream_id=f"thread:{payload['thread_id']}",
            expected_version=expected,
            actor_type="agent",
            actor_id="agent:vm-workflow",
            payload={"thread_id": payload["thread_id"], "run_id": result["run_id"]},
            thread_id=payload["thread_id"],
            brand_id=payload["brand_id"],
            project_id=payload["project_id"],
        ),
    )
    apply_event_to_read_models(session, completed)
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_orchestrator_v2.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/orchestrator_v2.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py
git commit -m "feat(vm-webapp): process workflow run requests in v2 orchestrator"
```

### Task 4: Add API v2 Endpoints for Workflow Run Input/Output

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_v2_workflow_run_endpoints_create_and_list_artifacts(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post("/api/v2/brands", headers={"Idempotency-Key": "b"}, json={"name": "Acme"})
    brands = client.get("/api/v2/brands").json()["brands"]
    brand_id = brands[0]["brand_id"]

    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p"},
        json={"brand_id": brand_id, "name": "Launch"},
    )
    project_id = client.get("/api/v2/projects", params={"brand_id": brand_id}).json()["projects"][0]["project_id"]

    thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()

    started = client.post(
        f"/api/v2/threads/{thread['thread_id']}/workflow-runs",
        headers={"Idempotency-Key": "run-1"},
        json={"request_text": "Generate plan assets", "mode": "plan_90d"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    listed = client.get(f"/api/v2/threads/{thread['thread_id']}/workflow-runs")
    assert listed.status_code == 200
    assert any(row["run_id"] == run_id for row in listed.json()["runs"])

    artifacts = client.get(f"/api/v2/workflow-runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()["stages"]
    assert artifacts.json()["stages"][0]["artifacts"]
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_workflow_run_endpoints_create_and_list_artifacts -v`  
Expected: FAIL with `404` for missing workflow run endpoints.

**Step 3: Write minimal implementation**

```python
# 09-tools/vm_webapp/api.py
class WorkflowRunRequest(BaseModel):
    request_text: str
    mode: str = "plan_90d"


@router.post("/v2/threads/{thread_id}/workflow-runs")
def start_workflow_run_v2(thread_id: str, payload: WorkflowRunRequest, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        event = append_event(
            session,
            EventEnvelope(
                event_id=f"evt-{uuid4().hex[:12]}",
                event_type="WorkflowRunRequested",
                aggregate_type="thread",
                aggregate_id=thread_id,
                stream_id=f"thread:{thread_id}",
                expected_version=get_stream_version(session, f"thread:{thread_id}"),
                actor_type="human",
                actor_id="workspace-owner",
                payload={
                    "thread_id": thread_id,
                    "brand_id": thread.brand_id,
                    "project_id": thread.project_id,
                    "request_text": payload.request_text,
                    "mode": payload.mode,
                },
                thread_id=thread_id,
                brand_id=thread.brand_id,
                project_id=thread.project_id,
            ),
        )
        apply_event_to_read_models(session, event)
        process_new_events(session)

        run = list_runs_by_thread(session, thread_id)[0]
    return {"run_id": run.run_id, "status": run.status}


@router.get("/v2/threads/{thread_id}/workflow-runs")
def list_workflow_runs_v2(thread_id: str, request: Request) -> dict[str, list[dict[str, object]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_runs_by_thread(session, thread_id)
    return {"runs": [{"run_id": r.run_id, "status": r.status, "created_at": r.created_at} for r in rows]}


@router.get("/v2/workflow-runs/{run_id}/artifacts")
def list_workflow_run_artifacts_v2(run_id: str, request: Request) -> dict[str, object]:
    root = Path(request.app.state.workspace.root) / "runs" / run_id / "stages"
    stages: list[dict[str, object]] = []
    if root.exists():
        for stage_dir in sorted(root.iterdir()):
            manifest = stage_dir / "manifest.json"
            if manifest.exists():
                stages.append(json.loads(manifest.read_text(encoding="utf-8")))
    return {"run_id": run_id, "stages": stages}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_v2_workflow_run_endpoints_create_and_list_artifacts -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/commands_v2.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat(vm-webapp): expose v2 workflow run input and artifact output endpoints"
```

### Task 5: Add Workflow Input/Output Panel in VM UI

**Files:**
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_vm_index_contains_workflow_io_panel() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="workflow-run-form"' in html
    assert 'id="workflow-request-input"' in html
    assert 'id="workflow-runs-list"' in html
    assert 'id="workflow-artifacts-list"' in html


def test_vm_app_js_calls_workflow_run_endpoints() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v2/threads/" in js and "/workflow-runs" in js
    assert "/api/v2/workflow-runs/" in js and "/artifacts" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`  
Expected: FAIL with missing workflow panel ids/endpoints.

**Step 3: Write minimal implementation**

```html
<!-- 09-tools/web/vm/index.html -->
<section class="panel" id="workflow-io-panel">
  <h3>Workflow Input / Output</h3>
  <form id="workflow-run-form" class="stack">
    <input id="workflow-request-input" placeholder="describe the workflow output you need" />
    <input id="workflow-mode-input" placeholder="mode (default plan_90d)" />
    <button type="submit">Run Workflow</button>
  </form>
  <h4>Runs</h4>
  <div id="workflow-runs-list" class="list"></div>
  <h4>Artifacts</h4>
  <div id="workflow-artifacts-list" class="list"></div>
</section>
```

```javascript
// 09-tools/web/vm/app.js
const workflowRunForm = document.getElementById("workflow-run-form");
const workflowRequestInput = document.getElementById("workflow-request-input");
const workflowModeInput = document.getElementById("workflow-mode-input");
const workflowRunsList = document.getElementById("workflow-runs-list");
const workflowArtifactsList = document.getElementById("workflow-artifacts-list");

async function loadWorkflowRuns() {
  if (!activeThreadId) return;
  const body = await fetchJson(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/workflow-runs`);
  // render runs...
}

async function loadWorkflowArtifacts(runId) {
  const body = await fetchJson(`/api/v2/workflow-runs/${encodeURIComponent(runId)}/artifacts`);
  // render stage artifacts...
}

workflowRunForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeThreadId) return;
  const payload = {
    request_text: workflowRequestInput.value.trim(),
    mode: workflowModeInput.value.trim() || "plan_90d",
  };
  await postV2(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/workflow-runs`, payload, "workflow-run");
  workflowRunForm.reset();
  await loadWorkflowRuns();
});
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(vm-webapp): add workflow input-output panel with run and artifact lists"
```

### Task 6: Add End-to-End Coverage and Full Verification

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_event_driven_e2e.py`
- Modify: `09-tools/tests/test_vm_webapp_api_v2.py`
- Modify: `09-tools/tests/test_vm_webapp_orchestrator_v2.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_thread_workflow_request_generates_versioned_artifacts_and_timeline(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "b1"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p1"},
        json={"brand_id": brand_id, "name": "Launch"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t1"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()["thread_id"]

    r1 = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "run-a"},
        json={"request_text": "First output", "mode": "plan_90d"},
    ).json()
    r2 = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "run-b"},
        json={"request_text": "Second output", "mode": "plan_90d"},
    ).json()

    assert r1["run_id"] != r2["run_id"]

    timeline = client.get(f"/api/v2/threads/{thread_id}/timeline").json()["items"]
    assert any(item["event_type"] == "WorkflowRunCompleted" for item in timeline)

    runs_root = app.state.workspace.root / "runs"
    assert (runs_root / r1["run_id"]).exists()
    assert (runs_root / r2["run_id"]).exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py::test_thread_workflow_request_generates_versioned_artifacts_and_timeline -v`  
Expected: FAIL until run-centric endpoints/runtime/timeline are fully integrated.

**Step 3: Complete remaining implementation gaps**

```python
# Align any missing glue discovered by E2E:
# - ensure apply_event_to_read_models is called for workflow events
# - ensure run list ordering stable by created_at desc
# - ensure stage manifest discovery works for all generated stage dirs
# - ensure timeline events include thread_id for projection
```

**Step 4: Run full verification suite**

Run: `uv run python -m pytest 09-tools/tests/test_vm_webapp_*.py -v`  
Expected: PASS for all `vm_webapp` tests.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_api_v2.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py
git commit -m "test(vm-webapp): cover end-to-end run-centric workflow io"
```

### Task 7: Local Runtime Verification Checklist (pre-merge)

**Files:**
- Modify (if needed): `docs/plans/2026-02-24-vm-event-driven-run-centric-io.md`

**Step 1: Start local server**

Run:

```bash
PYTHONPATH=09-tools ./.venv/bin/python -m vm_webapp serve --host 127.0.0.1 --port 8766
```

Expected: server healthy at `GET /api/v1/health`.

**Step 2: Manual smoke flow**

1. Create brand/project/thread in UI.
2. Submit workflow request text in new IO panel.
3. Confirm run appears with status.
4. Open artifacts list and confirm stage files listed.
5. Re-run with new input and confirm new `run_id` and separate directory.

**Step 3: Verify filesystem outputs**

Run:

```bash
find runtime/vm/runs -maxdepth 4 -type f | sort
```

Expected: each run has `run.json`, per-stage `manifest.json`, `input.json`, `output.json`, and artifact files.

**Step 4: Final commit (docs-only if adjustments were needed)**

```bash
git add docs/plans/2026-02-24-vm-event-driven-run-centric-io.md
git commit -m "docs: update run-centric io verification notes"
```
