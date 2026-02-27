# VM Studio — Governança Editorial v10 (Control Center)

## Escopo
Entrega do Studio Control Center para governança editorial com:
- painel de SLO editorial
- detecção de drift
- auto-remediation (toggle + execução manual + histórico)
- nova view `control` no Workspace

## Backend/Contrato consumido pelo UI
- SLO por brand (fetch/update)
- drift analysis por thread
- trigger de auto-remediation
- histórico de execuções de auto-remediation

## Frontend
- Hook atualizado:
  - `editorialSLO`, `loadingSLO`, `refreshEditorialSLO`, `updateEditorialSLO`
  - `editorialDrift`, `loadingDrift`, `refreshEditorialDrift`
  - `autoRemediationHistory`, `loadingAutoHistory`, `refreshAutoRemediationHistory`, `triggerAutoRemediation`
- WorkspacePanel:
  - nova aba `Control`
  - painel de Drift (score, severidade, flags, driver, ações)
  - painel de Auto-remediação (kill switch, trigger manual, histórico)
  - painel de thresholds SLO
- `viewState` com suporte ao modo `control`

## Testes
- suíte workspace passando com cobertura do Control Center
- build frontend de produção passando

## Resultado
Control Center operacional no Studio, com governança observável e acionável.
