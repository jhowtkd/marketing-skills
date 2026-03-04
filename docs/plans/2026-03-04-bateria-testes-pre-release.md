# Bateria de Testes Pre-Release Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Criar uma bateria de testes pre-release com execução por camadas, falha rápida e geração de evidências para bloquear ou aprovar avanço do projeto.

**Architecture:** A solução será um runner único em shell com estágios explícitos (`preflight`, `gate-critico`, `backend-full`, `frontend-full`, `e2e-startup`, `evidence`) e logs por estágio em pasta timestamped. O runner terá modo `--dry-run` para validação segura e código de saída binário para decisão de release. A cobertura será protegida por testes automatizados da própria interface do runner.

**Tech Stack:** Bash (`scripts/test_battery_prerelease.sh`), Python/pytest (`09-tools/tests`), uv, Node/NPM/Vitest/Playwright.

---

### Task 1: Criar testes do runner (TDD da interface)

**Files:**
- Create: `09-tools/tests/test_test_battery_prerelease_script.py`
- Test: `09-tools/tests/test_test_battery_prerelease_script.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
import os
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "test_battery_prerelease.sh"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "09-tools"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
    )


def test_list_stages_exposes_expected_pipeline() -> None:
    completed = run_script("--list")
    assert completed.returncode == 0
    assert "preflight" in completed.stdout
    assert "gate-critico" in completed.stdout
    assert "backend-full" in completed.stdout
    assert "frontend-full" in completed.stdout
    assert "e2e-startup" in completed.stdout
    assert "evidence" in completed.stdout


def test_dry_run_outputs_commands_without_execution() -> None:
    completed = run_script("--dry-run", "--stage", "gate-critico")
    assert completed.returncode == 0
    assert "DRY-RUN" in completed.stdout
    assert "test_vm_webapp_health_probes.py" in completed.stdout


def test_invalid_stage_fails_fast() -> None:
    completed = run_script("--stage", "nao-existe")
    assert completed.returncode != 0
    assert "Unknown stage" in (completed.stderr + completed.stdout)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py`  
Expected: FAIL porque o script ainda não existe.

**Step 3: Write minimal implementation**

Criar `scripts/test_battery_prerelease.sh` com parser mínimo para `--list`, `--dry-run` e `--stage`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_test_battery_prerelease_script.py scripts/test_battery_prerelease.sh
git commit -m "test: add prerelease battery runner contract tests"
```

### Task 2: Implementar runner com estágios e falha rápida

**Files:**
- Modify: `scripts/test_battery_prerelease.sh`
- Test: `09-tools/tests/test_test_battery_prerelease_script.py`

**Step 1: Write the failing test**

Adicionar teste cobrindo ordem de execução e short-circuit quando `gate-critico` falha:

```python
def test_pipeline_stops_on_gate_failure() -> None:
    completed = run_script("--dry-run", "--from", "preflight", "--to", "e2e-startup")
    assert completed.returncode == 0
    assert "preflight" in completed.stdout
    assert "gate-critico" in completed.stdout
    assert "e2e-startup" in completed.stdout
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py::test_pipeline_stops_on_gate_failure`  
Expected: FAIL se `--from/--to` não estiver implementado.

**Step 3: Write minimal implementation**

Implementar no script:
- matriz de estágios na ordem correta;
- seleção por `--from`/`--to`/`--stage`;
- execução sequencial;
- interrupção imediata no primeiro erro.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py`  
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/test_battery_prerelease.sh 09-tools/tests/test_test_battery_prerelease_script.py
git commit -m "feat: implement staged prerelease battery runner"
```

### Task 3: Implementar evidências e resumo final

**Files:**
- Modify: `scripts/test_battery_prerelease.sh`
- Test: `09-tools/tests/test_test_battery_prerelease_script.py`

**Step 1: Write the failing test**

Adicionar teste para garantir criação de artefatos:

```python
def test_dry_run_writes_summary_file(tmp_path: Path) -> None:
    completed = run_script("--dry-run", "--artifacts-dir", str(tmp_path))
    assert completed.returncode == 0
    assert (tmp_path / "summary.txt").exists()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py::test_dry_run_writes_summary_file`  
Expected: FAIL sem geração de summary.

**Step 3: Write minimal implementation**

Adicionar no script:
- diretório `artifacts/test-battery/<timestamp>/` por padrão;
- opção `--artifacts-dir`;
- logs por estágio (`<stage>.log`);
- `summary.txt` com status, duração e etapa de falha.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py`  
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/test_battery_prerelease.sh 09-tools/tests/test_test_battery_prerelease_script.py
git commit -m "feat: add artifacts and summary for prerelease battery"
```

### Task 4: Validar bateria real ponta a ponta (sem dry-run)

**Files:**
- Modify: `tasks/todo.md`
- Test: `scripts/test_battery_prerelease.sh` (execução real)

**Step 1: Write the failing test**

Executar gate real mínimo para provar comportamento no repositório atual.

**Step 2: Run test to verify it fails**

Run: `bash scripts/test_battery_prerelease.sh --stage gate-critico`  
Expected: Pode falhar inicialmente por ajuste de path/env.

**Step 3: Write minimal implementation**

Ajustar script para resolver:
- `cwd` em root do repositório;
- export `PYTHONPATH=09-tools`;
- chamadas de frontend dentro de `09-tools/web/vm-ui`.

**Step 4: Run test to verify it passes**

Run:
- `bash scripts/test_battery_prerelease.sh --stage gate-critico`
- `bash scripts/test_battery_prerelease.sh --stage backend-full`
- `bash scripts/test_battery_prerelease.sh --stage frontend-full`

Expected: PASS nos três estágios no ambiente local.

**Step 5: Commit**

```bash
git add scripts/test_battery_prerelease.sh tasks/todo.md
git commit -m "chore: validate prerelease battery stages locally"
```

### Task 5: Documentar uso operacional

**Files:**
- Modify: `README.md`
- Modify: `tasks/todo.md`

**Step 1: Write the failing test**

Critério manual: sem seção clara para bateria pre-release no README.

**Step 2: Run test to verify it fails**

Run: `rg -n "Bateria pre-release|test_battery_prerelease" README.md`  
Expected: sem seção dedicada.

**Step 3: Write minimal implementation**

Adicionar seção com:
- comando completo;
- execução por estágio;
- interpretação de `summary.txt`;
- regra de aprovação (`exit 0`) e bloqueio (`exit 1`).

**Step 4: Run test to verify it passes**

Run: `rg -n "Bateria pre-release|test_battery_prerelease|summary.txt" README.md`  
Expected: linhas encontradas.

**Step 5: Commit**

```bash
git add README.md tasks/todo.md
git commit -m "docs: add prerelease battery execution guide"
```

### Task 6: Verificação final antes de merge

**Files:**
- Modify: `tasks/todo.md`
- Test: `09-tools/tests/test_test_battery_prerelease_script.py`

**Step 1: Write the failing test**

Definir checklist final de validação no `tasks/todo.md`.

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_test_battery_prerelease_script.py`  
Expected: deve estar verde; se vermelho, corrigir antes de concluir.

**Step 3: Write minimal implementation**

Executar bateria completa e preencher review final com:
- duração total;
- estágios aprovados;
- caminho de artefatos gerados;
- riscos residuais.

**Step 4: Run test to verify it passes**

Run: `bash scripts/test_battery_prerelease.sh`  
Expected: exit code `0` para aprovado, `1` para bloqueado com causa explícita.

**Step 5: Commit**

```bash
git add tasks/todo.md
git commit -m "chore: finalize prerelease battery verification evidence"
```

