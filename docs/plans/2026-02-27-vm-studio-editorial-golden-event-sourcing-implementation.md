# VM Studio Editorial Golden Decision (Event-Sourcing) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar decisao editorial auditavel (golden global + golden por objetivo) com baseline oficial `objective > global > previous` no backend e frontend do VM Studio.

**Architecture:** Slice incremental sobre a arquitetura event-driven existente: novo comando/evento `EditorialGoldenMarked`, projection para read-model `editorial_decisions_view`, endpoint de baseline resolvido por run e consumo no React para scorecard/diff/regeneracao guiada.

**Tech Stack:** FastAPI + SQLAlchemy + Event Log/Projectors v2, React + TypeScript + Vite, pytest, Vitest + Testing Library.

---

### Task 1: Criar resolver de objetivo e baseline (backend puro)

**Files:**
- Create: `09-tools/vm_webapp/editorial_decisions.py`
- Create: `09-tools/tests/test_vm_webapp_editorial_decisions.py`

**Step 1: Write the failing test**

Criar `09-tools/tests/test_vm_webapp_editorial_decisions.py` com cenarios:

```python
from vm_webapp.editorial_decisions import derive_objective_key, resolve_baseline


def test_derive_objective_key_is_stable() -> None:
    a = derive_objective_key("Campanha Lancamento 2026 - Redes Sociais")
    b = derive_objective_key("campanha lancamento 2026 redes sociais")
    assert a == b


def test_resolve_baseline_priority_objective_global_previous() -> None:
    runs = [
        {"run_id": "run-3", "objective_key": "obj-a"},
        {"run_id": "run-2", "objective_key": "obj-a"},
        {"run_id": "run-1", "objective_key": "obj-b"},
    ]
    decisions = {
        "global": {"run_id": "run-1"},
        "objective": {"obj-a": {"run_id": "run-2"}},
    }
    baseline = resolve_baseline(active_run_id="run-3", active_objective_key="obj-a", runs=runs, decisions=decisions)
    assert baseline["baseline_run_id"] == "run-2"
    assert baseline["source"] == "objective_golden"
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_editorial_decisions.py -q
```

Expected: FAIL (`ModuleNotFoundError` or missing functions).

**Step 3: Write minimal implementation**

Criar `09-tools/vm_webapp/editorial_decisions.py`:

```python
from __future__ import annotations

import hashlib
import re
from typing import Any


def derive_objective_key(request_text: str) -> str:
    normalized = re.sub(r"\s+", " ", request_text.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:48] or "objective"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def resolve_baseline(*, active_run_id: str, active_objective_key: str | None, runs: list[dict[str, Any]], decisions: dict[str, Any]) -> dict[str, str | None]:
    objective = (decisions.get("objective") or {}) if isinstance(decisions, dict) else {}
    if active_objective_key and isinstance(objective.get(active_objective_key), dict):
        run_id = str(objective[active_objective_key].get("run_id", ""))
        if run_id and run_id != active_run_id:
            return {"baseline_run_id": run_id, "source": "objective_golden"}

    global_decision = decisions.get("global") if isinstance(decisions, dict) else None
    if isinstance(global_decision, dict):
        run_id = str(global_decision.get("run_id", ""))
        if run_id and run_id != active_run_id:
            return {"baseline_run_id": run_id, "source": "global_golden"}

    ids = [str(row.get("run_id", "")) for row in runs]
    if active_run_id in ids:
        idx = ids.index(active_run_id)
        prev = ids[idx + 1] if idx + 1 < len(ids) else ""
        if prev:
            return {"baseline_run_id": prev, "source": "previous"}

    return {"baseline_run_id": None, "source": "none"}
```

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_editorial_decisions.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/editorial_decisions.py 09-tools/tests/test_vm_webapp_editorial_decisions.py
git commit -m "feat(vm-runtime): add editorial baseline resolver and objective-key derivation"
```

---

### Task 2: Projetar read-model de decisoes editoriais

**Files:**
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/tests/test_vm_webapp_projectors_v2.py`

**Step 1: Write the failing test**

Adicionar em `test_vm_webapp_projectors_v2.py`:

```python
def test_editorial_golden_marked_projects_to_decisions_view(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-golden",
                event_type="EditorialGoldenMarked",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                thread_id="t1",
                payload={
                    "thread_id": "t1",
                    "run_id": "run-1",
                    "scope": "global",
                    "objective_key": None,
                    "justification": "best final quality",
                },
            ),
        )
        apply_event_to_read_models(session, row)

    with session_scope(engine) as session:
        rows = list_editorial_decisions_view(session, thread_id="t1")
        assert len(rows) == 1
        assert rows[0].run_id == "run-1"
        assert rows[0].scope == "global"
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_projectors_v2.py::test_editorial_golden_marked_projects_to_decisions_view -q
```

Expected: FAIL (missing model/repo projection).

**Step 3: Write minimal implementation**

1. Em `models.py`, criar model:

```python
class EditorialDecisionView(Base):
    __tablename__ = "editorial_decisions_view"

    decision_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    objective_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
```

2. Em `repo.py`, expor:

```python
def list_editorial_decisions_view(session: Session, *, thread_id: str) -> list[EditorialDecisionView]:
    return list(
        session.scalars(
            select(EditorialDecisionView)
            .where(EditorialDecisionView.thread_id == thread_id)
            .order_by(EditorialDecisionView.updated_at.desc())
        )
    )
```

3. Em `projectors_v2.py`, projetar `EditorialGoldenMarked` com chave:

```python
decision_key = f"{thread_id}|{scope}|{objective_key or '-'}"
```

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_projectors_v2.py::test_editorial_golden_marked_projects_to_decisions_view -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_projectors_v2.py
git commit -m "feat(api-v2): project editorial golden decisions into read model"
```

---

### Task 3: Adicionar comando idempotente para marcar golden

**Files:**
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Modify: `09-tools/tests/test_vm_webapp_commands_v2.py`

**Step 1: Write the failing test**

Adicionar em `test_vm_webapp_commands_v2.py`:

```python
def test_mark_editorial_golden_command_is_idempotent(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        first = mark_editorial_golden_command(
            session,
            thread_id="t1",
            run_id="run-1",
            scope="global",
            objective_key=None,
            justification="best editorial result",
            actor_id="workspace-owner",
            idempotency_key="idem-golden-1",
        )

    with session_scope(engine) as session:
        second = mark_editorial_golden_command(
            session,
            thread_id="t1",
            run_id="run-1",
            scope="global",
            objective_key=None,
            justification="best editorial result",
            actor_id="workspace-owner",
            idempotency_key="idem-golden-1",
        )

    assert first.event_id == second.event_id
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_commands_v2.py::test_mark_editorial_golden_command_is_idempotent -q
```

Expected: FAIL (command missing).

**Step 3: Write minimal implementation**

Adicionar em `commands_v2.py`:

```python
def mark_editorial_golden_command(
    session: Session,
    *,
    thread_id: str,
    run_id: str,
    scope: str,
    objective_key: str | None,
    justification: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="EditorialGoldenMarked",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        thread_id=thread_id,
        payload={
            "thread_id": thread_id,
            "run_id": run_id,
            "scope": scope,
            "objective_key": objective_key,
            "justification": justification,
        },
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="mark_editorial_golden",
        event_id=saved.event_id,
        response={
            "event_id": saved.event_id,
            "thread_id": thread_id,
            "run_id": run_id,
            "scope": scope,
            "objective_key": objective_key,
        },
    )
    return get_command_dedup(session, idempotency_key=idempotency_key)
```

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_commands_v2.py::test_mark_editorial_golden_command_is_idempotent -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/commands_v2.py 09-tools/tests/test_vm_webapp_commands_v2.py
git commit -m "feat(api-v2): add idempotent command for editorial golden marking"
```

---

### Task 4: Expor endpoints v2 para marcar e consultar decisoes editoriais

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

Adicionar em `test_vm_webapp_api_v2.py`:

```python
def test_editorial_decisions_endpoints_mark_and_list(tmp_path: Path) -> None:
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    # seed brand/project/thread/run
    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "ed-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "ed-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "ed-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "ed-run"}, json={"request_text": "Campanha Lancamento", "mode": "content_calendar"}).json()["run_id"]

    marked = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "ed-mark-1"},
        json={"run_id": run_id, "scope": "global", "justification": "melhor equilibrio editorial"},
    )
    assert marked.status_code == 200

    listed = client.get(f"/api/v2/threads/{thread_id}/editorial-decisions")
    assert listed.status_code == 200
    assert listed.json()["global"]["run_id"] == run_id
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_editorial_decisions_endpoints_mark_and_list -q
```

Expected: FAIL (404 endpoint missing).

**Step 3: Write minimal implementation**

Em `api.py`:

1. criar `EditorialGoldenMarkRequest(BaseModel)`

```python
class EditorialGoldenMarkRequest(BaseModel):
    run_id: str
    scope: str
    objective_key: str | None = None
    justification: str
```

2. endpoint POST mark:

- valida `scope in {"global", "objective"}`
- valida `objective_key` quando objective
- valida tamanho de `justification`
- valida run pertence ao thread
- chama `mark_editorial_golden_command`
- projeta evento com `project_command_event`

3. endpoint GET list:

- `list_editorial_decisions_view`
- monta payload `{global, objective[]}`

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_editorial_decisions_endpoints_mark_and_list -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat(api-v2): add editorial decisions endpoints for golden marks"
```

---

### Task 5: Expor objective_key em runs e endpoint de baseline resolvido

**Files:**
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

Adicionar em `test_vm_webapp_api_v2.py`:

```python
def test_workflow_run_baseline_endpoint_respects_priority(tmp_path: Path) -> None:
    # seed 3 runs in same thread
    # mark global on run-1, objective on run-2 (same objective as run-3)
    # GET /baseline for run-3 => run-2 + source objective_golden
    ...
```

E contrato aditivo:

```python
assert "objective_key" in listed_run
assert "objective_key" in detail
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_workflow_run_baseline_endpoint_respects_priority -q
```

Expected: FAIL.

**Step 3: Write minimal implementation**

1. Em `workflow_runtime_v2.py`, ao escrever `plan.json`, incluir:

```python
"objective_key": derive_objective_key(request_text),
```

2. Em `api.py`:

- incluir `objective_key` em list/detail de runs (lendo `plan.json`)
- criar `GET /api/v2/workflow-runs/{run_id}/baseline`
- usar `resolve_baseline(...)` com runs do thread + read-model de decisoes

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_workflow_run_baseline_endpoint_respects_priority -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat(vm-runtime): expose objective_key and resolved baseline for workflow runs"
```

---

### Task 6: Integrar dados editoriais no hook de workspace (frontend)

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts`
- Modify: `09-tools/web/vm-ui/src/features/workspace/presentation.ts`
- Create: `09-tools/web/vm-ui/src/features/workspace/useWorkspace.editorialDecision.test.tsx`

**Step 1: Write the failing test**

Criar `useWorkspace.editorialDecision.test.tsx` para validar:

- hook busca `/editorial-decisions`
- hook busca `/baseline` da run ativa
- fallback local continua funcional se endpoint falhar

Exemplo minimo:

```ts
it("loads resolved baseline for effective active run", async () => {
  // mock fetchJson returning runs + baseline payload
  // expect result.current.baseline.source toBe("objective_golden")
});
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/useWorkspace.editorialDecision.test.tsx
```

Expected: FAIL (state/fields missing).

**Step 3: Write minimal implementation**

Em `useWorkspace.ts`:

- novo estado `editorialDecisions`
- novo estado `resolvedBaselineByRun`
- novo fetch `/api/v2/threads/{thread_id}/editorial-decisions`
- novo fetch `/api/v2/workflow-runs/{run_id}/baseline`
- novo metodo `markGoldenDecision(...)`

Em `presentation.ts`:

- helper `toBaselineSourceLabel(source)`

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/useWorkspace.editorialDecision.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts 09-tools/web/vm-ui/src/features/workspace/presentation.ts 09-tools/web/vm-ui/src/features/workspace/useWorkspace.editorialDecision.test.tsx
git commit -m "feat(vm-ui): load editorial decisions and resolved baseline in workspace hook"
```

---

### Task 7: Implementar UX para marcar golden (modal + badges + baseline label)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/workspace/GoldenDecisionModal.tsx`
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Create: `09-tools/web/vm-ui/src/features/workspace/WorkspaceGoldenDecisionFlow.test.tsx`

**Step 1: Write the failing test**

Criar `WorkspaceGoldenDecisionFlow.test.tsx` cobrindo:

- botao `Definir como golden global`
- botao `Definir como golden deste objetivo`
- bloqueio de submit sem justificativa
- badge renderizado na run marcada
- label de baseline exibindo fonte correta

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/WorkspaceGoldenDecisionFlow.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

1. `GoldenDecisionModal.tsx`:

```tsx
// props: isOpen, scope, onClose, onSubmit
// textarea obrigatoria
```

2. Em `WorkspacePanel.tsx`:

- adicionar acoes nos cards de versao
- abrir modal para coletar justificativa
- chamar `markGoldenDecision`
- mostrar badges `Golden global` e `Golden objetivo`
- mostrar label `Comparando com: <fonte>`

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/WorkspaceGoldenDecisionFlow.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/GoldenDecisionModal.tsx 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/features/workspace/WorkspaceGoldenDecisionFlow.test.tsx
git commit -m "feat(vm-ui): add golden decision modal, badges, and baseline source labels"
```

---

### Task 8: Verificacao final e release note

**Files:**
- Create: `docs/releases/2026-02-27-vm-studio-editorial-golden-event-sourcing.md`

**Step 1: Run backend targeted suite**

Run:

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest \
  09-tools/tests/test_vm_webapp_editorial_decisions.py \
  09-tools/tests/test_vm_webapp_projectors_v2.py \
  09-tools/tests/test_vm_webapp_commands_v2.py \
  09-tools/tests/test_vm_webapp_api_v2.py -q
```

Expected: PASS.

**Step 2: Run frontend targeted suite**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/
```

Expected: PASS.

**Step 3: Build frontend**

Run:

```bash
cd 09-tools/web/vm-ui && npm run build
```

Expected: PASS (bundle gerado sem erro).

**Step 4: Write release note**

Criar `docs/releases/2026-02-27-vm-studio-editorial-golden-event-sourcing.md` com:

- problema resolvido
- endpoints novos
- mudancas de UX
- evidencias de testes
- riscos residuais

**Step 5: Commit**

```bash
git add docs/releases/2026-02-27-vm-studio-editorial-golden-event-sourcing.md
git commit -m "docs(release): record editorial golden event-sourcing rollout"
```

---

## Guardrails de Execucao

- Aplicar `@test-driven-development` em toda task (teste falhando antes de codigo).
- Se algo quebrar fora do esperado, aplicar `@systematic-debugging` antes de corrigir.
- Antes de declarar pronto, aplicar `@verification-before-completion` com evidencias de comando.
- Nao tocar `.agents/` e `.claude/`.

## Sequencia Recomendada no Kimi CLI

1. Executar Task 1-3 (foundation backend) e parar para checkpoint.
2. Executar Task 4-5 (API + contrato) e parar para checkpoint.
3. Executar Task 6-7 (frontend) e parar para checkpoint.
4. Executar Task 8 (verificacao + release note) e entao integrar.

Plan complete and saved to `docs/plans/2026-02-27-vm-studio-editorial-golden-event-sourcing-implementation.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
