# Todo - saneamento do repositorio antes da bateria de debug

## Checklist
- [x] Definir estrategia de saneamento com o usuario (opcao 1).
- [x] Documentar design aprovado em `docs/plans`.
- [x] Capturar baseline e executar limpeza de indice para `.venv` e `09-tools/.venv`.
- [x] Validar `uv.lock` + smoke checks.
- [x] Preparar commit de higiene.
- [x] Iniciar bateria de debug com repo limpo.

## Review
- Limpeza de index aplicada com `git rm --cached` para `.venv` e `09-tools/.venv`.
- `.gitignore` reforcado com `09-tools/.venv/`.
- Validacao tecnica minima executada com Python 3.12:
  - `uv run --python 3.12 python -c "import vm_webapp"`
  - `uv run --python 3.12 pytest -q 09-tools/tests/test_vm_webapp_startup_validation.py` (1 passed)
- Bateria completa de debug executada com sucesso:
  - `uv run --python 3.12 pytest -q 09-tools/tests` (1462 passed, 61 warnings)

---

# Todo - bateria de testes pre-release (design + plano)

## Checklist
- [x] Explorar contexto do projeto (docs, suites de teste, workflows e commits recentes).
- [x] Refinar objetivo com o usuario (escopo e prioridade da bateria).
- [x] Avaliar abordagens e aprovar estrategia de execucao por camadas com gates.
- [x] Validar desenho em seções (arquitetura, componentes/comandos, fluxo e bloqueio).
- [x] Documentar design aprovado em `docs/plans/2026-03-04-bateria-testes-pre-release-design.md`.
- [x] Gerar plano de implementacao detalhado via `writing-plans` em `docs/plans/2026-03-04-bateria-testes-pre-release.md`.
- [x] Escolher modo de execucao do plano (subagentes nesta sessao vs sessao paralela com executing-plans).

## Progresso - Bateria de Testes Pre-Release

### Task 1: Testes do runner (TDD da interface) ✓
- [x] Criar testes para `--list`, `--dry-run`, `--stage`
- [x] Implementar script mínimo para passar nos testes
- [x] Commit: `test: add prerelease battery runner contract tests`

### Task 2: Runner com estágios e falha rápida ✓
- [x] Adicionar teste para `--from`/`--to` com pipeline
- [x] Implementar execução sequencial e short-circuit
- [x] Commit: `feat: implement staged prerelease battery runner`

### Task 3: Evidências e resumo final ✓
- [x] Adicionar teste para `--artifacts-dir` e `summary.txt`
- [x] Implementar geração de logs por estágio
- [x] Commit: `feat: add artifacts and summary for prerelease battery`

### Task 4: Validação real ponta a ponta ✓
- [x] Executar gate-critico real (1 passed)
- [x] Executar backend-full real (1467 passed, 69 warnings)
- [x] Executar frontend-full real (736 passed, 2 failed - falhas conhecidas)
- [x] Commit: `chore: validate prerelease battery stages locally`

### Task 5: Documentação operacional [IN_PROGRESS]
- [ ] Adicionar seção no README
- [ ] Commitar documentação

### Task 3: Evidências e resumo final
- [ ] Adicionar teste para `--artifacts-dir` e `summary.txt`
- [ ] Implementar geração de logs por estágio
- [ ] Validar e commitar

### Task 4: Validação real ponta a ponta
- [ ] Executar gate-critico real
- [ ] Executar backend-full real
- [ ] Executar frontend-full real
- [ ] Commitar ajustes

### Task 5: Documentação operacional
- [ ] Adicionar seção no README
- [ ] Commitar documentação

### Task 6: Verificação final
- [ ] Executar bateria completa
- [ ] Preencher review final
- [ ] Commitar evidências

## Review
- Design aprovado com escopo completo: backend + frontend + E2E + smoke de inicializacao.
- Decisao de cobertura: sem limite de tempo, priorizando confiabilidade pre-release.
- Arquitetura definida em 6 camadas: `preflight`, `gate-critico`, `backend-full`, `frontend-full`, `e2e+startup`, `evidence`.
- Politica de bloqueio definida: falha critica interrompe pipeline e bloqueia avancos.
- `docs/kimi/` removido do workspace a pedido do usuario antes de seguir com versionamento.
