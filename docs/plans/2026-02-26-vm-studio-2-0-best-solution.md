# VM Studio 2.0 — Critica e Solucao Consolidada

## Objetivo
Consolidar a melhor direcao entre:
- `docs/plans/2026-02-26-vm-studio-2-0-design.md`
- `docs/plans/2026-02-26-vm-studio-2-0-implementation.md`
- Decisoes aprovadas no brainstorming desta thread

Foco do release: **Balanced v1** (clareza + entrega de valor + confiabilidade operacional).

---

## Achados Criticos (Critica)

### P0 - Contrato de API quebrado no frontend atual (causa timeline/inbox "vazios")
- Frontend espera `events/tasks/approvals`:
  - `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts` (linhas 84-85)
  - `09-tools/web/vm-ui/src/features/inbox/useInbox.ts` (linhas 41-42 e 54-55)
- Backend retorna `items`:
  - `09-tools/vm_webapp/api.py` (linhas 792-805, 815-826, 837-848)
- Impacto: exatamente os sintomas reportados pelo usuario (timeline sem evento, inbox pouco util).

### P0 - Plano de implementacao proposto gera conteudo fake e ignora runtime real
- `docs/plans/2026-02-26-vm-studio-2-0-implementation.md` define placeholder local:
  - API fake em linhas 570-579
  - geracao fake em linhas 587-743
- Impacto: "parece funcionar", mas nao usa workflow real, approvals, artifacts, historico e auditoria.

### P1 - Design remove capacidades que o produto precisa para operar
- Remocao de timeline/tasks/approvals/dev mode:
  - `docs/plans/2026-02-26-vm-studio-2-0-design.md` linhas 146-154, 271-275, 439-446
- Impacto: quebra governanca operacional e depuracao; piora confiabilidade em fluxos com gate.

### P1 - Terminologia e fluxo nao batem com decisoes do produto
- Documento usa "Projeto + Template + Editor", mas decisoes aprovadas foram:
  - `Cliente / Campanha / Job / Versao`
  - experiencia **hibrida** `Chat + Studio`
  - abertura por "ultima tela usada"
- Impacto: desalinhamento de linguagem e UX com objetivo real da agencia.

### P1 - Escopo tecnico aumenta sem necessidade no v1
- Novos endpoints propostos (`/templates`, `/quick-generate`) em:
  - `docs/plans/2026-02-26-vm-studio-2-0-design.md` linhas 266-267
- Impacto: maior risco e prazo; nao necessario para corrigir usabilidade agora.

### P2 - Plano nao esta realmente orientado a TDD e verificacao
- Testes sao majoritariamente checklist manual:
  - `docs/plans/2026-02-26-vm-studio-2-0-implementation.md` linhas 1831-1895
- Impacto: chance alta de regressao na integracao com API v2.

---

## Solucao Consolidada (Best-of-Both)

## 1) Direcao de Produto (aprovada)
- Modelo de experiencia: **Hibrido**
  - `Chat` para fluxo linear diario.
  - `Studio` para operacao/controle.
- Tela inicial do Job: **ultima tela usada**.
- Linguagem oficial da UI:
  - `Cliente` (brand)
  - `Campanha` (project)
  - `Job` (thread)
  - `Versao` (workflow run)
- Inbox: manter com 2 abas
  - `Pendentes`
  - `Historico`

## 2) Regras de UX do Balanced v1
- Esconder IDs e JSON por padrao; mostrar apenas em `Dev mode`.
- CTA principal: `Gerar nova versao` (nao "rodar workflow").
- Modal de execucao obrigatorio:
  - `Objetivo do pedido` (request_text)
  - `Profile` selecionado
- Nome humano da versao:
  - `Versao N · <pedido curto> · <HH:mm>`
- Timeline util com eventos traduzidos:
  - versao criada, etapa iniciou/concluiu, aguardando revisao, aprovada, concluida/falhou.
- Artefato central:
  - preview Markdown renderizado
  - download `.md`
  - acao de regenerar quando qualidade estiver baixa.

## 3) Direcao tecnica (sem "big bang" arriscado)
- **Nao** criar um segundo frontend paralelo com geracao fake.
- Evoluir o frontend React atual em `09-tools/web/vm-ui/src/*`.
- Preservar backend e contratos `api/v2` existentes no Phase 1.
- Adicionar apenas camada de adaptacao de payload no frontend.

---

## Arquitetura Recomendada

## Camada A - Contract Adapters (obrigatoria no inicio)
- Criar adaptadores tipados para normalizar:
  - timeline: `{items}` -> array de `TimelineEventUI`
  - tasks/approvals: `{items}` -> `InboxItemUI`
  - statuses tecnicos -> labels humanas
- Corrigir imediatamente os bugs de parse atuais (P0).

## Camada B - UX Hibrida
- Workspace central com tabs:
  - `Chat`
  - `Studio`
- Persistir ultima aba por `job_id` (localStorage).
- Header humano (Cliente/Campanha/Job/Versao ativa).

## Camada C - Execucao e Historico
- Botao `Gerar nova versao` abre modal com request real.
- Polling orientado a estado:
  - ativo enquanto versao em `queued/running/waiting_approval`
  - reduz frequencia quando `completed/failed`.
- Inbox pendentes/historico sincronizada com tasks/approvals.

## Camada D - Entregavel
- Markdown renderer seguro para artifacts.
- Download `.md` do artefato principal.
- Indicador de qualidade minima:
  - sinalizar artefato curto/malformado
  - CTA: `Regenerar com mais profundidade`.

## Camada E - Dev Mode
- Toggle mantido (default off).
- Exibe IDs, payload bruto, traces de run, detalhes de erro.

---

## Plano de Implementacao Consolidado

## Fase 1 - Confiabilidade de dados (P0)
1. Ajustar `useWorkspace` para timeline consumir `items`.
2. Ajustar `useInbox` para tasks/approvals consumirem `items`.
3. Adicionar testes de contrato frontend para shape de resposta v2.
4. Validar manualmente com run real + timeline preenchendo.

## Fase 2 - Linguagem e navegacao de agencia
1. Aplicar renomeacao visual para `Cliente/Campanha/Job/Versao`.
2. Esconder IDs por padrao.
3. Adicionar explicacoes curtas de conceitos (tooltip/help).
4. Implementar tabs `Chat/Studio` + persistencia de ultima tela.

## Fase 3 - Fluxo de versao
1. Substituir botao tecnico por `Gerar nova versao`.
2. Modal com `objetivo do pedido` + `profile`.
3. Nomenclatura humana de versao (`Versao N · pedido curto · hora`).
4. Humanizar status e eventos da timeline.

## Fase 4 - Entregavel e inbox util
1. Destacar artefato principal no centro.
2. Render Markdown + download `.md`.
3. Inbox em duas abas (`Pendentes`, `Historico`).
4. CTA claro para approvals/tarefas e transicao automatica para historico.

## Fase 5 - Hardening e qualidade
1. Testes E2E do fluxo: criar job -> gerar versao -> aprovar -> artefato -> download.
2. Testes de regressao para timeline/inbox.
3. Telemetria basica: tempo ate primeira versao pronta, taxa de falha, taxa de regen.

---

## Critérios de Sucesso do Release
- Usuario entende `Cliente/Campanha/Job/Versao` sem ajuda externa.
- Consegue gerar versao em fluxo linear.
- Ve timeline viva e Inbox acionavel.
- Recebe artefato legivel e baixa `.md`.
- Nao precisa de IDs/JSON para operar.

---

## Decisao Final Recomendada
Seguir com esta solucao consolidada e **descartar** o caminho de:
- geracao fake local,
- remocao de timeline/inbox/approvals,
- replatform paralelo sem integracao real.

Essa consolidacao entrega ganho de usabilidade sem perder a arquitetura event-driven que ja existe.
