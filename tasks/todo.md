# Todo - CI Main Green Hardening

## Task 1: Baseline de Estabilidade ✅
- [x] Coletar dados de runs na main (50 últimos)
- [x] Documentar workflows ativos e taxa de verde
- [x] Classificar checks: PRE_EXISTING, NEW_REGRESSION, FLAKE, INCONCLUSIVE
- [x] Criar `docs/ci/2026-03-main-baseline.md`
- [x] Commit: baseline documentado

## Task 2: Estabilizar vm-webapp-smoke (Onda 1)
- [ ] Analisar YAML e identificar causas de falha
- [ ] Corrigir comandos/paths quebrados
- [ ] Validar YAML
- [ ] Testar em PR
- [ ] Commit: smoke estabilizado

## Task 3: Alinhar v33-v37 (Onda 2)
- [ ] Analisar divergências entre workflows
- [ ] Padronizar runtime Python
- [ ] Alinhar comandos de teste
- [ ] Validar todos os YAMLs
- [ ] Commit: gates alinhados

## Task 4: Governança de Gates
- [ ] Criar matriz de ownership/SLA
- [ ] Documentar política de deprecação
- [ ] Commit: governança formalizada

## Task 5: Observabilidade Semanal
- [ ] Criar script de relatório
- [ ] Testar geração de markdown
- [ ] Commit: observabilidade ativa

## Task 6: Validação Final
- [ ] Consolidar evidências
- [ ] Verificar critério de saída (80% verde)
- [ ] Documentar riscos residuais
- [ ] Commit: finalização

---

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
