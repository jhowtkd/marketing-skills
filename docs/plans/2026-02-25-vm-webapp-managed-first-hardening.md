# VM Webapp Managed-First Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Endurecer o `vm_webapp` para operacao managed-first com configuracao segura, dependencia externa resiliente, observabilidade operacional e readiness para deploy continuo.

**Architecture:** O hardening preserva o desenho atual (FastAPI + runtime event-driven + tooling/RAG) e adiciona camadas de operabilidade: config validada por ambiente, engine de banco parametrica, fila externa opcional para worker, probes de saude, metricas padronizadas, logs estruturados e runbooks de deploy. O foco e reduzir risco de incidente em producao sem quebrar fluxo local de desenvolvimento.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy, pytest, Redis, PostgreSQL/SQLite, uv, GitHub Actions.

---

Execution discipline: `@test-driven-development`, `@verification-before-completion`, `@requesting-code-review`.

### Task 1: Expandir settings para modo managed-first

**Files:**
- Create: `09-tools/tests/test_vm_webapp_settings_managed.py`
- Modify: `09-tools/vm_webapp/settings.py`
- Modify: `.env.example`
- Test: `09-tools/tests/test_vm_webapp_settings_managed.py`

**Step 1: Write the failing test**

```python
def test_settings_supports_db_url_redis_url_and_env_validation(monkeypatch) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_settings_managed.py::test_settings_supports_db_url_redis_url_and_env_validation -v`  
Expected: FAIL porque campos de configuracao ainda nao existem.

**Step 3: Write minimal implementation**

```python
class Settings(BaseSettings):
    app_env: str = "local"
    vm_db_url: str | None = None
    vm_redis_url: str | None = None
    vm_enable_managed_mode: bool = False
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_settings_managed.py::test_settings_supports_db_url_redis_url_and_env_validation -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/settings.py .env.example 09-tools/tests/test_vm_webapp_settings_managed.py
git commit -m "feat(vm-webapp): add managed-first settings contract"
```

### Task 2: Tornar engine de banco compativel com SQLite e PostgreSQL

**Files:**
- Create: `09-tools/tests/test_vm_webapp_db_engine.py`
- Modify: `09-tools/vm_webapp/db.py`
- Modify: `09-tools/vm_webapp/app.py`
- Test: `09-tools/tests/test_vm_webapp_db_engine.py`

**Step 1: Write the failing test**

```python
def test_build_engine_accepts_sqlite_path_and_postgres_url(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_db_engine.py::test_build_engine_accepts_sqlite_path_and_postgres_url -v`  
Expected: FAIL porque `build_engine` suporta apenas path sqlite.

**Step 3: Write minimal implementation**

```python
def build_engine(*, db_path: Path | None = None, db_url: str | None = None) -> Engine:
    # usa db_url quando presente, com pool_pre_ping e connect args apropriados
    ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_db_engine.py::test_build_engine_accepts_sqlite_path_and_postgres_url -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/db.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_db_engine.py
git commit -m "feat(vm-webapp): support sqlite and postgres engines for managed mode"
```

### Task 3: Introduzir validacao de startup para dependencias criticas

**Files:**
- Create: `09-tools/tests/test_vm_webapp_startup_validation.py`
- Create: `09-tools/vm_webapp/startup_checks.py`
- Modify: `09-tools/vm_webapp/app.py`
- Test: `09-tools/tests/test_vm_webapp_startup_validation.py`

**Step 1: Write the failing test**

```python
def test_managed_mode_requires_db_and_redis_when_enabled(monkeypatch) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_startup_validation.py::test_managed_mode_requires_db_and_redis_when_enabled -v`  
Expected: FAIL porque nao ha fail-fast de startup.

**Step 3: Write minimal implementation**

```python
def validate_startup_contract(settings: Settings) -> None:
    if settings.vm_enable_managed_mode and not settings.vm_redis_url:
        raise ValueError("managed mode requires vm_redis_url")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_startup_validation.py::test_managed_mode_requires_db_and_redis_when_enabled -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/startup_checks.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_startup_validation.py
git commit -m "feat(vm-webapp): add startup contract validation for managed mode"
```

### Task 4: Criar probes de saude operacional (liveness/readiness/dependencies)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_health_probes.py`
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/app.py`
- Test: `09-tools/tests/test_vm_webapp_health_probes.py`

**Step 1: Write the failing test**

```python
def test_readiness_reports_db_and_worker_dependency_state(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_health_probes.py::test_readiness_reports_db_and_worker_dependency_state -v`  
Expected: FAIL porque endpoint readiness nao existe.

**Step 3: Write minimal implementation**

```python
@router.get("/v2/health/live")
def health_live() -> dict[str, str]: ...

@router.get("/v2/health/ready")
def health_ready(request: Request) -> dict[str, object]: ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_health_probes.py::test_readiness_reports_db_and_worker_dependency_state -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_health_probes.py
git commit -m "feat(vm-webapp): add managed-ready live and readiness probes"
```

### Task 5: Extrair worker para modo externo opcional (sem quebrar dev local)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_worker_mode.py`
- Modify: `09-tools/vm_webapp/event_worker.py`
- Modify: `09-tools/vm_webapp/__main__.py`
- Modify: `09-tools/vm_webapp/app.py`
- Test: `09-tools/tests/test_vm_webapp_worker_mode.py`

**Step 1: Write the failing test**

```python
def test_cli_supports_worker_command_and_does_not_mount_http_app() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_worker_mode.py::test_cli_supports_worker_command_and_does_not_mount_http_app -v`  
Expected: FAIL porque comando `worker` nao existe.

**Step 3: Write minimal implementation**

```python
worker = subparsers.add_parser("worker", help="Run background event worker")
worker.add_argument("--poll-interval-ms", type=int, default=500)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_worker_mode.py::test_cli_supports_worker_command_and_does_not_mount_http_app -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/__main__.py 09-tools/vm_webapp/event_worker.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_worker_mode.py
git commit -m "feat(vm-webapp): add standalone worker mode for managed deployments"
```

### Task 6: Endurecer observabilidade (metricas runtime + HTTP + endpoint Prometheus)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_metrics_prometheus.py`
- Modify: `09-tools/vm_webapp/observability.py`
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Test: `09-tools/tests/test_vm_webapp_metrics_prometheus.py`

**Step 1: Write the failing test**

```python
def test_prometheus_metrics_endpoint_exposes_runtime_counters(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py::test_prometheus_metrics_endpoint_exposes_runtime_counters -v`  
Expected: FAIL porque endpoint texto prometheus nao existe.

**Step 3: Write minimal implementation**

```python
@router.get("/v2/metrics/prometheus")
def metrics_prometheus(request: Request) -> PlainTextResponse:
    return PlainTextResponse(render_prometheus(app.state.workflow_runtime.metrics.snapshot()))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py::test_prometheus_metrics_endpoint_exposes_runtime_counters -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/observability.py 09-tools/vm_webapp/api.py 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/tests/test_vm_webapp_metrics_prometheus.py
git commit -m "feat(vm-webapp): expose prometheus compatible runtime metrics"
```

### Task 7: Adicionar logging estruturado com request_id e correlation_id

**Files:**
- Create: `09-tools/tests/test_vm_webapp_structured_logging.py`
- Create: `09-tools/vm_webapp/logging_config.py`
- Modify: `09-tools/vm_webapp/app.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_structured_logging.py`

**Step 1: Write the failing test**

```python
def test_http_request_logs_include_request_id_and_path(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_structured_logging.py::test_http_request_logs_include_request_id_and_path -v`  
Expected: FAIL porque middleware de request id/log estruturado nao existe.

**Step 3: Write minimal implementation**

```python
app.middleware("http")(request_id_middleware)
configure_structured_logging(level=settings.log_level)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_structured_logging.py::test_http_request_logs_include_request_id_and_path -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/logging_config.py 09-tools/vm_webapp/app.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_structured_logging.py
git commit -m "feat(vm-webapp): add structured logging with request correlation ids"
```

### Task 8: Criar contrato de deploy managed-first e runbook operacional

**Files:**
- Create: `deploy/render/vm-webapp-render.yaml`
- Create: `docs/runbooks/vm-webapp-managed-first.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_readme_mentions_managed_first_runbook_and_worker_command() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k managed -v`  
Expected: FAIL porque docs de managed-first ainda nao existem.

**Step 3: Write minimal implementation**

```yaml
services:
  - type: web
  - type: worker
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k managed -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add deploy/render/vm-webapp-render.yaml docs/runbooks/vm-webapp-managed-first.md README.md ARCHITECTURE.md
git commit -m "docs(vm-webapp): add managed-first deployment and operations runbook"
```

### Task 9: Adicionar testes de resiliencia operacional de dependencia externa

**Files:**
- Create: `09-tools/tests/test_vm_webapp_managed_resilience_e2e.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/event_worker.py`
- Test: `09-tools/tests/test_vm_webapp_managed_resilience_e2e.py`

**Step 1: Write the failing test**

```python
def test_runtime_remains_available_when_dependency_is_temporarily_unreachable(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_managed_resilience_e2e.py::test_runtime_remains_available_when_dependency_is_temporarily_unreachable -v`  
Expected: FAIL por falta de tratamento robusto de dependencia indisponivel.

**Step 3: Write minimal implementation**

```python
try:
    worker.pump(max_events=30)
except Exception:
    metrics.record_count("dependency_failures")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_managed_resilience_e2e.py::test_runtime_remains_available_when_dependency_is_temporarily_unreachable -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/event_worker.py 09-tools/tests/test_vm_webapp_managed_resilience_e2e.py
git commit -m "test+feat(vm-webapp): harden runtime behavior under dependency outages"
```

### Task 10: Gate final de verificacao e pacote de release hardening

**Files:**
- Create: `docs/plans/2026-02-25-vm-webapp-managed-first-hardening-release-checklist.md`
- Modify: `docs/plans/2026-02-25-vm-webapp-managed-first-hardening.md`
- Test: `09-tools/tests/test_vm_webapp_managed_resilience_e2e.py`

**Step 1: Write the failing test**

```python
def test_hardening_release_checklist_exists_and_mentions_migrations_secrets_and_probes() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k checklist -v`  
Expected: FAIL por falta do checklist hardening.

**Step 3: Write minimal implementation**

```markdown
- [ ] DB migration plan reviewed
- [ ] Redis/worker liveness validated
- [ ] Readiness probe validated in staging
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k checklist -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add docs/plans/2026-02-25-vm-webapp-managed-first-hardening-release-checklist.md docs/plans/2026-02-25-vm-webapp-managed-first-hardening.md
git commit -m "docs(plan): add managed-first hardening release checklist"
```

## Full Verification Gate (before merge)

Run in order:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_settings_managed.py -q
uv run pytest 09-tools/tests/test_vm_webapp_db_engine.py -q
uv run pytest 09-tools/tests/test_vm_webapp_startup_validation.py -q
uv run pytest 09-tools/tests/test_vm_webapp_health_probes.py -q
uv run pytest 09-tools/tests/test_vm_webapp_worker_mode.py -q
uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q
uv run pytest 09-tools/tests/test_vm_webapp_structured_logging.py -q
uv run pytest 09-tools/tests/test_vm_webapp_managed_resilience_e2e.py -q
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
uv run pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py -q
uv run pytest 09-tools/tests/test_vm_webapp_platform_e2e.py -q
```

Expected:
- all tests pass
- readiness/liveness and metrics endpoints stable
- worker mode and runtime remain functional in managed and local modes.

If any command fails, stop and debug with `@systematic-debugging` before continuing.

