# VM Webapp Plataforma Completa Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Entregar a plataforma completa da Agencia Virtual evoluindo o `09-tools/vm_webapp` atual com dominio hierarquico, orquestracao resiliente, Tool Layer, RAG e operacao managed-first.

**Architecture:** A implementacao segue fatias verticais sobre o runtime atual, preservando compatibilidade enquanto adiciona novos modulos por contrato. O nucleo continua event-driven, com snapshots imutaveis por run e projecoes para leitura. Recursos avancados (tools, RAG, observabilidade) entram como modulos composiveis no mesmo pacote antes de extracao para servicos separados.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy, pytest, Redis queue/cache, PostgreSQL/SQLite (dev), vector store adapter, object storage adapter.

---

Execution discipline: `@test-driven-development`, `@verification-before-completion`, `@requesting-code-review`.

### Task 1: Introduzir modelo hierarquico Campaign/Task no dominio de leitura

**Files:**
- Create: `09-tools/tests/test_vm_webapp_domain_hierarchy.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_domain_hierarchy.py`

**Step 1: Write the failing test**

```python
def test_projector_creates_campaign_and_task_views(tmp_path: Path) -> None:
    # assert que CampaignCreated/TaskCreated projetam corretamente
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_domain_hierarchy.py::test_projector_creates_campaign_and_task_views -v`  
Expected: FAIL com tabela/view inexistente.

**Step 3: Write minimal implementation**

```python
class CampaignView(Base):
    __tablename__ = "campaigns_view"
    campaign_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_domain_hierarchy.py::test_projector_creates_campaign_and_task_views -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_domain_hierarchy.py
git commit -m "feat(vm-webapp): add campaign and task hierarchy read models"
```

### Task 2: Implementar versionamento append-only de contexto (Brand/Campaign/Task)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_context_versions.py`
- Create: `09-tools/vm_webapp/context_versions.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_context_versions.py`

**Step 1: Write the failing test**

```python
def test_context_versions_are_append_only(tmp_path: Path) -> None:
    # cria 2 versoes e valida que a primeira nao e alterada
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_context_versions.py::test_context_versions_are_append_only -v`  
Expected: FAIL por tabela/servico ausente.

**Step 3: Write minimal implementation**

```python
def append_context_version(session: Session, *, scope: str, scope_id: str, payload: dict[str, Any]) -> str:
    version_id = f"ctxv-{uuid4().hex[:12]}"
    ...
    return version_id
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_context_versions.py::test_context_versions_are_append_only -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/context_versions.py 09-tools/tests/test_vm_webapp_context_versions.py
git commit -m "feat(vm-webapp): add append-only context versioning"
```

### Task 3: Adicionar regras de sobrescrita controlada e resolvedor de contexto

**Files:**
- Create: `09-tools/tests/test_vm_webapp_context_resolver.py`
- Create: `09-tools/vm_webapp/context_resolver.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_context_resolver.py`

**Step 1: Write the failing test**

```python
def test_context_resolver_applies_allowed_overrides_only(tmp_path: Path) -> None:
    # override permitido passa; override proibido gera erro
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_context_resolver.py::test_context_resolver_applies_allowed_overrides_only -v`  
Expected: FAIL por resolver ausente.

**Step 3: Write minimal implementation**

```python
class ContextPolicyError(ValueError):
    pass

def resolve_hierarchical_context(...)-> dict[str, Any]:
    # merge Brand -> Campaign -> Task com allowlist de paths
    ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_context_resolver.py::test_context_resolver_applies_allowed_overrides_only -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/context_resolver.py 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_context_resolver.py
git commit -m "feat(vm-webapp): enforce hierarchical context override policy"
```

### Task 4: Injetar contexto resolvido e snapshot imutavel em `WorkflowRuntimeV2`

**Files:**
- Create: `09-tools/tests/test_vm_webapp_workflow_context_snapshot.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Test: `09-tools/tests/test_vm_webapp_workflow_context_snapshot.py`

**Step 1: Write the failing test**

```python
def test_run_stores_context_snapshot_and_uses_it_in_stage_prompt(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_context_snapshot.py::test_run_stores_context_snapshot_and_uses_it_in_stage_prompt -v`  
Expected: FAIL porque runtime nao persiste snapshot.

**Step 3: Write minimal implementation**

```python
run_context = resolve_hierarchical_context(...)
self._write_run_context_snapshot(run_id=run_id, context=run_context)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_context_snapshot.py::test_run_stores_context_snapshot_and_uses_it_in_stage_prompt -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/commands_v2.py 09-tools/tests/test_vm_webapp_workflow_context_snapshot.py
git commit -m "feat(vm-webapp): snapshot resolved context per workflow run"
```

### Task 5: Fortalecer resiliencia por stage (retry/backoff/fallback/circuit breaker)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_resilience_policy.py`
- Create: `09-tools/vm_webapp/resilience.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/workflow_profiles.py`
- Test: `09-tools/tests/test_vm_webapp_resilience_policy.py`

**Step 1: Write the failing test**

```python
def test_retry_policy_and_fallback_chain_transition_correctly(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_resilience_policy.py::test_retry_policy_and_fallback_chain_transition_correctly -v`  
Expected: FAIL por politica ausente.

**Step 3: Write minimal implementation**

```python
decision = resilience_policy.next_action(stage_attempts=2, max_attempts=3, retryable=True)
if decision == "fallback":
    provider = fallback_chain.next_provider(current_provider)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_resilience_policy.py::test_retry_policy_and_fallback_chain_transition_correctly -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/resilience.py 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/workflow_profiles.py 09-tools/tests/test_vm_webapp_resilience_policy.py
git commit -m "feat(vm-webapp): add stage retry fallback and circuit breaker policies"
```

### Task 6: Criar Tool Registry e contrato de plugin

**Files:**
- Create: `09-tools/tests/test_vm_webapp_tool_registry.py`
- Create: `09-tools/vm_webapp/tooling/contracts.py`
- Create: `09-tools/vm_webapp/tooling/registry.py`
- Test: `09-tools/tests/test_vm_webapp_tool_registry.py`

**Step 1: Write the failing test**

```python
def test_registry_registers_searches_and_lists_tools() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_tool_registry.py::test_registry_registers_searches_and_lists_tools -v`  
Expected: FAIL por modulo inexistente.

**Step 3: Write minimal implementation**

```python
class ToolRegistry:
    def register(self, tool: ToolContract) -> None: ...
    def search(self, query: str) -> list[ToolContract]: ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_tool_registry.py::test_registry_registers_searches_and_lists_tools -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/tooling/contracts.py 09-tools/vm_webapp/tooling/registry.py 09-tools/tests/test_vm_webapp_tool_registry.py
git commit -m "feat(vm-webapp): add tool registry and plugin contracts"
```

### Task 7: Adicionar autorizacao/rate-limit de tool e refs de credenciais

**Files:**
- Create: `09-tools/tests/test_vm_webapp_tool_governance.py`
- Create: `09-tools/vm_webapp/tooling/governance.py`
- Modify: `09-tools/vm_webapp/models.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_tool_governance.py`

**Step 1: Write the failing test**

```python
def test_tool_execution_requires_permission_and_respects_rate_limit(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_tool_governance.py::test_tool_execution_requires_permission_and_respects_rate_limit -v`  
Expected: FAIL por tabelas/politicas ausentes.

**Step 3: Write minimal implementation**

```python
def authorize_tool_call(...)-> None:
    if not has_permission(...):
        raise PermissionError("tool action not allowed")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_tool_governance.py::test_tool_execution_requires_permission_and_respects_rate_limit -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/vm_webapp/repo.py 09-tools/vm_webapp/tooling/governance.py 09-tools/tests/test_vm_webapp_tool_governance.py
git commit -m "feat(vm-webapp): enforce tool permissions rate limits and credential refs"
```

### Task 8: Integrar Tool Executor ao runtime com auditoria por chamada

**Files:**
- Create: `09-tools/tests/test_vm_webapp_tool_executor_runtime.py`
- Create: `09-tools/vm_webapp/tooling/executor.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Test: `09-tools/tests/test_vm_webapp_tool_executor_runtime.py`

**Step 1: Write the failing test**

```python
def test_runtime_executes_stage_via_tool_executor_and_logs_audit(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_tool_executor_runtime.py::test_runtime_executes_stage_via_tool_executor_and_logs_audit -v`  
Expected: FAIL porque runtime ainda usa caminho legado sem executor.

**Step 3: Write minimal implementation**

```python
result = self.tool_executor.execute(stage_key=stage.stage_id, context=run_context)
self._append_audit_event(event_type="ToolInvoked", payload=result.audit_payload)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_tool_executor_runtime.py::test_runtime_executes_stage_via_tool_executor_and_logs_audit -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/tooling/executor.py 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/projectors_v2.py 09-tools/tests/test_vm_webapp_tool_executor_runtime.py
git commit -m "feat(vm-webapp): wire tool executor into workflow runtime with audit trail"
```

### Task 9: Implementar modulo RAG (ingestao + retrieval hierarquico)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_rag_pipeline.py`
- Create: `09-tools/vm_webapp/rag/chunker.py`
- Create: `09-tools/vm_webapp/rag/indexer.py`
- Create: `09-tools/vm_webapp/rag/retriever.py`
- Modify: `09-tools/vm_webapp/memory.py`
- Test: `09-tools/tests/test_vm_webapp_rag_pipeline.py`

**Step 1: Write the failing test**

```python
def test_rag_retrieval_prefers_same_brand_and_campaign(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_rag_pipeline.py::test_rag_retrieval_prefers_same_brand_and_campaign -v`  
Expected: FAIL por pipeline RAG inexistente.

**Step 3: Write minimal implementation**

```python
def retrieve(query: str, *, brand_id: str, campaign_id: str | None) -> list[ChunkHit]:
    # filtro brand + boost campaign
    ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_rag_pipeline.py::test_rag_retrieval_prefers_same_brand_and_campaign -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/rag/chunker.py 09-tools/vm_webapp/rag/indexer.py 09-tools/vm_webapp/rag/retriever.py 09-tools/vm_webapp/memory.py 09-tools/tests/test_vm_webapp_rag_pipeline.py
git commit -m "feat(vm-webapp): add hierarchical rag ingestion and retrieval pipeline"
```

### Task 10: Conectar aprendizado automatico na conclusao de run

**Files:**
- Create: `09-tools/tests/test_vm_webapp_learning_ingestion.py`
- Create: `09-tools/vm_webapp/learning.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/artifacts.py`
- Test: `09-tools/tests/test_vm_webapp_learning_ingestion.py`

**Step 1: Write the failing test**

```python
def test_completed_run_indexes_artifacts_as_learning(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_learning_ingestion.py::test_completed_run_indexes_artifacts_as_learning -v`  
Expected: FAIL porque run completed nao indexa learning.

**Step 3: Write minimal implementation**

```python
if run_completed:
    self.learning_ingestor.ingest_run(run_id=run_id, quality_score=score)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_learning_ingestion.py::test_completed_run_indexes_artifacts_as_learning -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/learning.py 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/artifacts.py 09-tools/tests/test_vm_webapp_learning_ingestion.py
git commit -m "feat(vm-webapp): ingest completed run artifacts into learning store"
```

### Task 11: Expor APIs v2 para Campaign/Task/Rules/Tools

**Files:**
- Create: `09-tools/tests/test_vm_webapp_api_v2_domain_extensions.py`
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Modify: `09-tools/vm_webapp/projectors_v2.py`
- Modify: `09-tools/vm_webapp/repo.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2_domain_extensions.py`

**Step 1: Write the failing test**

```python
def test_v2_can_create_campaign_task_and_brand_rule_with_idempotency(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2_domain_extensions.py::test_v2_can_create_campaign_task_and_brand_rule_with_idempotency -v`  
Expected: FAIL com endpoints inexistentes.

**Step 3: Write minimal implementation**

```python
@router.post("/v2/campaigns")
def create_campaign_v2(...): ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2_domain_extensions.py::test_v2_can_create_campaign_task_and_brand_rule_with_idempotency -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/commands_v2.py 09-tools/vm_webapp/projectors_v2.py 09-tools/vm_webapp/repo.py 09-tools/tests/test_vm_webapp_api_v2_domain_extensions.py
git commit -m "feat(vm-webapp): expose v2 endpoints for campaign task rules and tools"
```

### Task 12: Adicionar observabilidade minima (metricas + health operacional + custo)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_observability.py`
- Create: `09-tools/vm_webapp/observability.py`
- Modify: `09-tools/vm_webapp/api.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Test: `09-tools/tests/test_vm_webapp_observability.py`

**Step 1: Write the failing test**

```python
def test_metrics_endpoint_reports_run_stage_cost_and_latency(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_observability.py::test_metrics_endpoint_reports_run_stage_cost_and_latency -v`  
Expected: FAIL por endpoint/collector ausente.

**Step 3: Write minimal implementation**

```python
@router.get("/v2/metrics")
def metrics_v2(request: Request) -> dict[str, object]:
    return request.app.state.metrics.snapshot()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_observability.py::test_metrics_endpoint_reports_run_stage_cost_and_latency -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/observability.py 09-tools/vm_webapp/api.py 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/tests/test_vm_webapp_observability.py
git commit -m "feat(vm-webapp): add runtime metrics health and cost visibility"
```

### Task 13: Validacao integrada da fatia completa (E2E)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_platform_e2e.py`
- Modify: `09-tools/tests/conftest.py`
- Test: `09-tools/tests/test_vm_webapp_platform_e2e.py`

**Step 1: Write the failing test**

```python
def test_full_platform_flow_brand_campaign_task_run_review_learning(tmp_path: Path) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_platform_e2e.py::test_full_platform_flow_brand_campaign_task_run_review_learning -v`  
Expected: FAIL por pipeline incompleto.

**Step 3: Write minimal implementation**

```python
# Ajustes de fixtures para subir app com runtime + tool executor + rag em modo teste
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_platform_e2e.py::test_full_platform_flow_brand_campaign_task_run_review_learning -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/conftest.py 09-tools/tests/test_vm_webapp_platform_e2e.py
git commit -m "test(vm-webapp): add end-to-end platform flow validation"
```

### Task 14: Fechamento de release tecnica e verificacao final

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Create: `docs/plans/2026-02-25-vm-webapp-plataforma-completa-release-checklist.md`
- Test: `09-tools/tests/test_vm_webapp_platform_e2e.py`

**Step 1: Write the failing test**

```python
def test_readme_and_architecture_document_new_platform_contracts() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k readme -v`  
Expected: FAIL por docs incompletas.

**Step 3: Write minimal implementation**

```markdown
## Plataforma Completa
- Dominio hierarquico
- Tool Layer governada
- RAG de aprendizado continuo
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k readme -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md docs/plans/2026-02-25-vm-webapp-plataforma-completa-release-checklist.md
git commit -m "docs(vm-webapp): publish full-platform architecture and release checklist"
```

## Full Verification Gate (before merge)

Run in order:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_*.py -q
uv run pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py -q
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
uv run pytest 09-tools/tests/test_vm_webapp_platform_e2e.py -q
```

Expected:
- all tests pass
- no stage marked as flaky
- e2e validates run lifecycle, gates, tool audit and learning ingestion.

If any command fails, stop and debug using `@systematic-debugging` before continuing.

