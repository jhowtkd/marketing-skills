# VM Web App Approve Button Guard Design

## Context

O VM Web App já foi entregue com painel de runs em tempo real, SSE e ação de `Approve`.
Durante uso manual, foi observado que cliques repetidos no botão `Approve` podem gerar múltiplos `POST /approve` seguidos para o mesmo `run_id`.

## Goal

Eliminar aprovações duplicadas acidentais no frontend com uma proteção simples e de baixo risco, mantendo escopo mínimo.

## Decisions

- Estratégia: PR mínimo focado no bug.
- Escopo de arquivos do fix:
  - `09-tools/web/vm/app.js`
  - `09-tools/tests/test_vm_webapp_ui_assets.py`
- Artefatos locais (`09-tools/marketing_skills.egg-info/`, `uv.lock`): ignorar por enquanto.

## Approach

1. Desabilitar o botão `Approve` no momento do clique.
2. Reabilitar o botão no `finally` da requisição.
3. Adicionar guarda em memória por `run_id` para bloquear requisições concorrentes.
4. Cobrir com teste de asset que valida os marcadores de disable/enable no JS.

## Verification

- `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_disables_approve_button_while_request_in_flight -v`
- `pytest 09-tools/tests/test_vm_webapp_ui_assets.py -q`

## Risks & Mitigations

- Risco: botão ficar travado após erro.
  - Mitigação: reabilitar sempre no `finally`.
- Risco: múltiplos gatilhos para o mesmo run.
  - Mitigação: `Set` de `run_id` em andamento para bloqueio de concorrência.

## Done Criteria

- PR aberto com diff apenas nos 2 arquivos do fix.
- Testes focados passando.
- Mensagem de PR explicando a prevenção de cliques duplicados em `Approve`.
