# Design: CI main green hardening (3-4 semanas)

## Contexto
Depois da estabilizacao da bateria pre-release, a branch `main` ainda apresenta instabilidade cronica em parte dos workflows de CI.
O objetivo agora e operacional: restaurar `main` consistentemente verde com governanca clara de gates e sem mascarar divida tecnica.

## Objetivo aprovado
- Prioridade: estabilizar CI global.
- Meta de sucesso: checks obrigatorios da `main` consistentemente verdes.
- Janela: 3-4 semanas.
- Estrategia: execucao por trilhas de falha (nao big bang).

## Abordagem escolhida
### Opcao A - Big bang
- Consolidar todos os workflows em um unico ciclo de refatoracao.
- Risco alto de regressao e rollback caro.

### Opcao B - Trilhas de falha (escolhida)
- Atacar clusters de instabilidade por ondas semanais.
- Progresso mensuravel, baixo risco operacional, rollback simples por workflow.

### Opcao C - Green main com bypass inicial
- Reduzir gates obrigatorios e recuperar legados depois.
- Rapida no curto prazo, mas com alto risco de falso verde.

## Arquitetura de execucao
### Fase A - Baseline confiavel (dias 1-3)
- Inventariar todos os workflows ativos.
- Classificar falhas em `PRE_EXISTING`, `NEW_REGRESSION`, `FLAKE`.
- Definir source of truth de checks obrigatorios da `main`.

### Fase B - Estabilizacao por ondas (semanas 1-3)
- Onda 1: `vm-webapp-smoke` (falhas cronicas e gates com maior impacto).
- Onda 2: `unit-tests`, `lint`, `type-check`, `metrics` nos gates v33-v37.
- Onda 3: flakiness residual, tempo de pipeline e padronizacao final de runtime.

### Fase C - Governanca e prevencao (semana 4)
- Owner por workflow e SLA por severidade.
- Politica explicita para deprecacao de gate legado.
- Relatorio operacional semanal com tendencia de estabilidade.

## Workstreams
1. `vm-webapp-smoke` hardening:
- Quebrar por subgates, priorizar top 20% causas que geram 80% das falhas.

2. Gates v33-v37 alignment:
- Padronizar runtime/deps/comandos entre local e CI.
- Eliminar duplicidades e divergencias de path.

3. Governanca de workflow:
- Matriz `workflow -> owner -> criticidade -> SLA -> status`.

4. Observabilidade de CI:
- Painel simples de taxa de verde, tempo medio e top causas por semana.

## Fluxo operacional semanal
1. Segunda: atualizar baseline dos runs de `main`.
2. Terca a quinta: corrigir top falhas da onda ativa.
3. Sexta: congelar mudancas em workflow, medir estabilidade semanal e publicar status.

## Riscos e mitigacao
- Risco: corrigir um gate e quebrar outro.
  - Mitigacao: PR pequeno por workflow + validacao cruzada.
- Risco: falso verde por bypass.
  - Mitigacao: auditoria de branch protection e contrato minimo por gate.
- Risco: backlog infinito de legado.
  - Mitigacao: politica de deprecacao com prazo e owner definido.

## Criterios de aceite
- `main` verde consistente em janela continua definida no kickoff.
- Zero gate critico sem owner.
- Checklist de governanca e runbook de CI atualizados.
- Regressao nova classificada e enderecada em no maximo um ciclo semanal.

