# Implementation plan: saneamento do repositorio pre-debug

## Objetivo
Deixar o repositorio em estado limpo e previsivel para iniciar bateria de debug sem ruido de versionamento.

## Fase 1 - Baseline
- [ ] Capturar estado atual (`git status --short --branch`).
- [ ] Capturar diff de `uv.lock`.

## Fase 2 - Saneamento de indice
- [ ] Remover do indice Git os paths historicamente versionados por engano:
  - [ ] `.venv`
  - [ ] `09-tools/.venv`
- [ ] Confirmar regras de ignore para ambientes virtuais.
- [ ] Revisar staging com `git diff --cached --name-status`.

## Fase 3 - Validacao tecnica minima
- [ ] Validar import basico com `uv run python`.
- [ ] Rodar teste curto focal para garantir integridade minima.

## Fase 4 - Fechamento
- [ ] Atualizar `tasks/todo.md` com status final.
- [ ] Preparar commit com escopo estrito de saneamento.
- [ ] Entregar resumo objetivo com riscos residuais.
