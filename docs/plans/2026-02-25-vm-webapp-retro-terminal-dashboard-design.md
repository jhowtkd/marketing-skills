# VM Webapp Retro Terminal Dashboard Design

## Contexto

O workspace atual do VM webapp ja possui estrutura funcional e contratos estaveis com `app.js` + `/api/v2/*`.
O Stitch forneceu a referencia visual "Retro Terminal Workspace Dashboard", com assets baixados em:

- `tmp/stitch-4698476232767236312/36217e413d3c4fdc999dd3e89105c3b3/retro-terminal-workspace-dashboard.html`
- `tmp/stitch-4698476232767236312/36217e413d3c4fdc999dd3e89105c3b3/retro-terminal-workspace-dashboard-full.png`

## Objetivo

Substituir o layout atual do VM Web App por um layout retro terminal com fidelidade visual alta (quase pixel-perfect ao Stitch), mantendo toda a logica e todos os IDs/anchors existentes para evitar regressao funcional.

## Decisoes aprovadas

1. Substituir o layout atual (nao criar rota paralela).
2. Aplicar fidelidade visual alta ao Stitch.
3. Manter todos os blocos funcionais atuais:
`Studio toolbar/wizard`, `Threads`, `Workflow I/O`, `Tasks`, `Approvals`, `Artifacts`.
4. Abordagem tecnica: re-skin estrutural do `index.html`, preservando contratos de DOM com `app.js`.

## Arquitetura

### Camadas

1. `09-tools/web/vm/index.html`
- Reorganizacao para shell retro em 3 colunas (`vm-shell-left`, `vm-shell-main`, `vm-shell-right`) com header terminal.
- Preservar todos os IDs consumidos por `app.js`.

2. `09-tools/web/vm/styles.css`
- Tokens visuais retro centralizados (paleta monocromatica, bordas sharp, scanline, tipografia mono, scrollbar terminal).
- Classes utilitarias de painel e estados visuais.

3. `09-tools/web/vm/app.js`
- Sem mudanca de contratos de API/estado.
- Apenas ajustes de apresentacao quando necessario para suportar estrutura visual retro.

### Regra de compatibilidade

"Visual troca, contrato permanece": endpoint, polling, selecao ativa e acoes existentes continuam identicos.

## Mapeamento de componentes

### Coluna esquerda

- Brands: `brand-create-form`, `brand-name-input`, `brands-list`
- Projects: `project-create-form`, `project-name-input`, `project-objective-input`, `project-channels-input`, `project-due-date-input`, `projects-list`
- Threads compactos: `thread-title-input`, `thread-create-button`, `threads-list`

### Coluna central

- Header terminal principal
- Studio: `studio-status-text`, `studio-create-plan-button`, `studio-devmode-toggle`
- Preview: `studio-artifact-preview`
- Progress: `studio-stage-progress`
- Operacao principal: `thread-mode-form`, `thread-mode-input`, `mode-help`, `thread-modes-list`, `workflow-run-form`, `workflow-request-input`, `workflow-mode-input`, `workflow-overrides-input`, `workflow-profile-preview-list`, `workflow-runs-list`, `workflow-run-detail-list`, `timeline-list`
- Erros nao bloqueantes: `ui-error-banner`

### Coluna direita

- Tasks: `tasks-list`
- Approvals: `approvals-list`
- Artifacts: `workflow-artifacts-list`, `workflow-artifact-preview`

### Modal wizard

- `studio-wizard` e campos associados mantidos e reestilizados.

## Fluxo de dados

1. Manter state machine atual no `app.js` (`activeBrandId`, `activeProjectId`, `activeThreadId`, `activeWorkflowRunId`).
2. Manter endpoints `/api/v2/*` e payloads sem alteracao.
3. Manter cadeia de refresh apos acoes (`Grant`, `Resume`, `Complete`, criacao/edicao).
4. Manter polling (`restartWorkflowPolling`) com mesma semantica.

## Tratamento de erro

1. `fetchJson` segue como fronteira principal de erro.
2. `ui-error-banner` continua como superficie nao bloqueante.
3. Erros transientes nao devem limpar selecoes e listas validas.

## Testes

### Automatizados

1. Atualizar/manter `09-tools/tests/test_vm_webapp_ui_assets.py` para garantir:
- IDs obrigatorios intactos;
- shell retro e distribuicao por colunas;
- anchors de Studio, dev mode e wizard;
- contratos de endpoint e hooks de UI relevantes.

2. Rodar suite de testes de UI assets e testes de servico relacionados ao webapp.

### Validacao manual

1. Criar/editar/selecionar brand.
2. Criar/editar/selecionar project.
3. Criar thread e gerenciar modes.
4. Rodar workflow e inspecionar run detail.
5. Grant/resume approvals.
6. Comment/complete tasks.
7. Abrir previews de artifacts.
8. Validar comportamento em desktop e mobile.

## Criterio de pronto

1. UI retro terminal aplicada com alta fidelidade.
2. Todos os fluxos atuais seguem funcionais sem regressao.
3. Contratos de DOM e API preservados.
4. Testes relevantes passando.
