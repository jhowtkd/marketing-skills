# Todo - saneamento do repositorio antes da bateria de debug

## Checklist
- [x] Definir estrategia de saneamento com o usuario (opcao 1).
- [x] Documentar design aprovado em `docs/plans`.
- [x] Capturar baseline e executar limpeza de indice para `.venv` e `09-tools/.venv`.
- [x] Validar `uv.lock` + smoke checks.
- [x] Preparar commit de higiene.
- [ ] Iniciar bateria de debug com repo limpo.

## Review
- Limpeza de index aplicada com `git rm --cached` para `.venv` e `09-tools/.venv`.
- `.gitignore` reforcado com `09-tools/.venv/`.
- Validacao tecnica minima executada com Python 3.12:
  - `uv run --python 3.12 python -c "import vm_webapp"`
  - `uv run --python 3.12 pytest -q 09-tools/tests/test_vm_webapp_startup_validation.py` (1 passed)
