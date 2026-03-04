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
- [ ] Escolher modo de execucao do plano (subagentes nesta sessao vs sessao paralela com executing-plans).

## Review
- Design aprovado com escopo completo: backend + frontend + E2E + smoke de inicializacao.
- Decisao de cobertura: sem limite de tempo, priorizando confiabilidade pre-release.
- Arquitetura definida em 6 camadas: `preflight`, `gate-critico`, `backend-full`, `frontend-full`, `e2e+startup`, `evidence`.
- Politica de bloqueio definida: falha critica interrompe pipeline e bloqueia avancos.
- `docs/kimi/` removido do workspace a pedido do usuario antes de seguir com versionamento.
