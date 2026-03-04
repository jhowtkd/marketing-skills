# Design: bateria de testes pre-release

## Contexto
O projeto possui alto volume de testes e múltiplos workflows de CI.
A necessidade desta frente é ter uma bateria pre-release confiável para bloquear regressões antes de avançar com mudanças maiores.

## Decisões aprovadas
- Escopo validado: backend + frontend + E2E + smoke de inicialização.
- Orçamento de execução: sem limite fixo de tempo; priorizar cobertura máxima.
- Estratégia escolhida: execução por camadas com gates (em vez de monolítica ou matriz complexa).

## Objetivo
Definir uma bateria pre-release reproduzível, com falha rápida para regressões críticas, validação ampla do produto e evidências claras para decisão de avanço.

## Arquitetura da bateria
1. `preflight`: valida ambiente e dependências mínimas.
2. `gate-critico`: verifica contratos básicos e smoke essencial.
3. `backend-full`: executa suíte Python completa.
4. `frontend-full`: executa suíte Vitest completa.
5. `e2e+startup`: valida fluxos ponta a ponta e inicialização.
6. `evidence`: consolida artefatos e status final.

## Componentes e comandos
### 1) preflight
- `python --version` (exigir `3.12.x`)
- `uv --version`
- `node --version`
- `npm --version`
- `PYTHONPATH=09-tools uv run python -c "import vm_webapp"`
- `cd 09-tools/web/vm-ui && npm run build`

### 2) gate-critico
- `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_vm_webapp_startup_validation.py`
- `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_vm_webapp_route_wiring.py`
- `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_vm_webapp_health_probes.py`
- `cd 09-tools/web/vm-ui && npm run test -- --run src/test/smoke.test.ts`

### 3) backend-full
- `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests`

### 4) frontend-full
- `cd 09-tools/web/vm-ui && npm run test -- --run src/`

### 5) e2e+startup
- `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_vm_webapp_event_driven_e2e.py`
- `PYTHONPATH=09-tools uv run pytest -q 09-tools/tests/test_vm_webapp_platform_e2e.py`
- `cd 09-tools/web/vm-ui && npm run test:e2e`

### 6) evidence
- Persistir logs de cada etapa em `artifacts/test-battery/<timestamp>/`.
- Gerar resumo único com total de testes, duração e etapa de falha.

## Fluxo e política de bloqueio
1. Pipeline linear por gates: cada etapa depende do sucesso da anterior.
2. Falha em `preflight` ou `gate-critico`: abortar imediatamente.
3. Falha em `backend-full` ou `frontend-full`: bloquear execução E2E.
4. Falha em `e2e+startup`: release bloqueado mesmo com unit tests verdes.
5. Exit code final padronizado: `0` aprovado, `1` bloqueado.

## Riscos e mitigação
- Duração alta da bateria completa: reduzir retrabalho com falha rápida nas primeiras camadas.
- Diagnóstico difícil em execução única: separar por etapas com logs dedicados.
- Inconsistência de ambiente local: reforçar `preflight` com validações explícitas.

## Critérios de aceite
- Todas as camadas obrigatórias executadas e verdes.
- Sem regressão nos testes críticos de startup e contrato API v2.
- Artefatos gerados com evidência reproduzível de sucesso/falha.
- Resultado final binário para decisão de avanço (`aprovado`/`bloqueado`).

