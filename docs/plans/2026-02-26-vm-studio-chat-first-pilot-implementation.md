# VM Studio Chat-First Pilot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar a experiência chat-first do VM Studio em `/studio` com sugestão de 3 templates e CTA primário “Refinar no chat”.

**Architecture:** Evolução incremental do frontend `09-tools/web/vm-studio` já existente. O estado passa a ser faseado (`chat_input` -> `template_suggestion` -> `generating` -> `deliverable_ready` -> `refining`) com componentes dedicados por fase e adapters para linguagem humana.

**Tech Stack:** React 18, TypeScript, Zustand, react-markdown, Vite, Tailwind.

---

## Task 0: Baseline e Segurança

**Files:** None (verification only)

**Step 1: Entrar no frontend do Studio**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-studio
```

**Step 2: Instalar dependências**

```bash
npm install --include=dev
```

**Step 3: Validar baseline**

```bash
npm run build
```

Expected: build concluído sem erro.

**Step 4: Commit vazio de baseline (opcional)**

```bash
git commit --allow-empty -m "chore(vm-studio): record chat-first baseline"
```

---

## Task 1: Expandir Tipos para Fluxo Chat-First

**Files:**
- Modify: `09-tools/web/vm-studio/src/types/index.ts`
- Test: `09-tools/web/vm-studio/src/store/storePhase.test.ts` (create)

**Step 1: Escrever teste falhando para fases do fluxo**

Criar teste para validar transição entre fases (`chat_input` -> `template_suggestion` -> `deliverable_ready`).

**Step 2: Rodar teste isolado**

```bash
npm run test -- --run src/store/storePhase.test.ts
```

Expected: FAIL inicial.

**Step 3: Implementar tipos novos**

Adicionar no `types/index.ts`:
- `StudioPhase`
- `ChatMessage`
- `SuggestedTemplate`
- estado de sessão do fluxo

**Step 4: Rodar teste novamente**

```bash
npm run test -- --run src/store/storePhase.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-studio/src/types/index.ts 09-tools/web/vm-studio/src/store/storePhase.test.ts
git commit -m "feat(vm-studio): add chat-first flow types and phase contract"
```

---

## Task 2: Evoluir Store para Estado Faseado

**Files:**
- Modify: `09-tools/web/vm-studio/src/store/index.ts`
- Test: `09-tools/web/vm-studio/src/store/storePhase.test.ts`

**Step 1: Escrever testes de transição no store**

Cobrir ações:
- enviar pedido inicial
- registrar 3 sugestões
- selecionar template
- marcar geração concluída
- entrar em refinamento

**Step 2: Rodar teste isolado**

```bash
npm run test -- --run src/store/storePhase.test.ts
```

Expected: FAIL parcial.

**Step 3: Implementar ações no store**

Adicionar ações mínimas:
- `startFromChatRequest(requestText)`
- `setTemplateSuggestions(suggestions)`
- `chooseSuggestedTemplate(templateId)`
- `setPhase(phase)`
- `appendChatMessage(message)`

**Step 4: Rodar teste novamente**

```bash
npm run test -- --run src/store/storePhase.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-studio/src/store/index.ts 09-tools/web/vm-studio/src/store/storePhase.test.ts
git commit -m "feat(vm-studio): add phased chat-first state management"
```

---

## Task 3: API Client para Sugestão de Templates (Adapter)

**Files:**
- Modify: `09-tools/web/vm-studio/src/api/client.ts`
- Test: `09-tools/web/vm-studio/src/api/client.test.ts` (create)

**Step 1: Escrever teste falhando para sugestão de 3 templates**

Validar:
- sempre retorna 3 sugestões ordenadas
- inclui justificativa curta
- fallback para seleção manual quando falhar

**Step 2: Rodar teste isolado**

```bash
npm run test -- --run src/api/client.test.ts
```

Expected: FAIL.

**Step 3: Implementar função de sugestão**

Adicionar função no client:
- `suggestTemplatesFromRequest(requestText, templates)`

Implementação mínima inicial:
- heurística local baseada em palavras-chave
- fallback determinístico para 3 templates padrão

**Step 4: Rodar teste novamente**

```bash
npm run test -- --run src/api/client.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-studio/src/api/client.ts 09-tools/web/vm-studio/src/api/client.test.ts
git commit -m "feat(vm-studio): add template suggestion adapter for chat requests"
```

---

## Task 4: Criar Views Chat-First e Sugestões

**Files:**
- Create: `09-tools/web/vm-studio/src/components/ChatHomeView.tsx`
- Create: `09-tools/web/vm-studio/src/components/TemplateSuggestionView.tsx`
- Modify: `09-tools/web/vm-studio/src/App.tsx`
- Test: `09-tools/web/vm-studio/src/components/chatFlow.test.tsx` (create)

**Step 1: Escrever teste de navegação de fase no App**

Verificar render condicional por fase.

**Step 2: Rodar teste isolado**

```bash
npm run test -- --run src/components/chatFlow.test.tsx
```

Expected: FAIL.

**Step 3: Implementar `ChatHomeView`**

Requisitos:
- input principal
- botão de envio
- exemplos rápidos

**Step 4: Implementar `TemplateSuggestionView`**

Requisitos:
- lista com 3 cards
- justificativa por template
- ação de selecionar
- fallback de “Escolher manualmente”

**Step 5: Integrar no `App.tsx`**

Trocar roteamento por `currentView` para roteamento por fase no fluxo piloto.

**Step 6: Rodar teste novamente**

```bash
npm run test -- --run src/components/chatFlow.test.tsx
```

Expected: PASS.

**Step 7: Commit**

```bash
git add 09-tools/web/vm-studio/src/components/ChatHomeView.tsx 09-tools/web/vm-studio/src/components/TemplateSuggestionView.tsx 09-tools/web/vm-studio/src/components/chatFlow.test.tsx 09-tools/web/vm-studio/src/App.tsx
git commit -m "feat(vm-studio): implement chat entry and template suggestion views"
```

---

## Task 5: Deliverable View com CTA Primário “Refinar no chat”

**Files:**
- Create: `09-tools/web/vm-studio/src/components/DeliverableView.tsx`
- Modify: `09-tools/web/vm-studio/src/components/Editor.tsx`
- Modify: `09-tools/web/vm-studio/src/components/MarkdownPreview.tsx`
- Test: `09-tools/web/vm-studio/src/components/deliverableView.test.tsx` (create)

**Step 1: Escrever teste do CTA primário**

Validar presença e prioridade visual de “Refinar no chat”.

**Step 2: Rodar teste isolado**

```bash
npm run test -- --run src/components/deliverableView.test.tsx
```

Expected: FAIL.

**Step 3: Implementar `DeliverableView`**

Requisitos:
- entregável renderizado
- próximos passos
- botão principal “Refinar no chat”
- ações secundárias (exportar/salvar)

**Step 4: Integrar no fluxo da fase `deliverable_ready`**

Atualizar `App.tsx`/`Editor.tsx` para priorizar `DeliverableView`.

**Step 5: Rodar teste novamente**

```bash
npm run test -- --run src/components/deliverableView.test.tsx
```

Expected: PASS.

**Step 6: Commit**

```bash
git add 09-tools/web/vm-studio/src/components/DeliverableView.tsx 09-tools/web/vm-studio/src/components/Editor.tsx 09-tools/web/vm-studio/src/components/MarkdownPreview.tsx 09-tools/web/vm-studio/src/components/deliverableView.test.tsx 09-tools/web/vm-studio/src/App.tsx
git commit -m "feat(vm-studio): add deliverable-first screen with refine-in-chat primary action"
```

---

## Task 6: Direção Visual Editorial Premium

**Files:**
- Modify: `09-tools/web/vm-studio/src/index.css`
- Modify: `09-tools/web/vm-studio/src/components/ui/*.tsx` (somente se necessário)
- Test: `09-tools/web/vm-studio/src/components/uiVisual.test.tsx` (create)

**Step 1: Escrever teste simples de classes-chave (smoke visual)**

Validar tokens/classes estruturais esperadas nas views principais.

**Step 2: Rodar teste isolado**

```bash
npm run test -- --run src/components/uiVisual.test.tsx
```

Expected: FAIL.

**Step 3: Ajustar tema para editorial premium**

Aplicar:
- tipografia com mais personalidade
- espaçamento consistente
- contraste e superfícies de card
- hierarquia de botões (primário/ secundário)

**Step 4: Rodar teste novamente**

```bash
npm run test -- --run src/components/uiVisual.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-studio/src/index.css 09-tools/web/vm-studio/src/components/uiVisual.test.tsx 09-tools/web/vm-studio/src/components/ui/*.tsx
git commit -m "style(vm-studio): apply editorial premium visual system"
```

---

## Task 7: Verificação Integrada

**Files:** None (verification only)

**Step 1: Rodar suíte de testes do Studio**

```bash
npm run test -- --run
```

Expected: PASS.

**Step 2: Build de produção do Studio**

```bash
npm run build
```

Expected: PASS, gerando `dist/`.

**Step 3: Verificar backend continua saudável para `/`**

```bash
cd /Users/jhonatan/Repos/marketing-skills
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_react_ui_contract -q
```

Expected: PASS.

**Step 4: Commit de verificação**

```bash
git commit --allow-empty -m "test(vm-studio): verify chat-first pilot flow and build"
```

---

## Task 8: Documentação de Uso do Piloto

**Files:**
- Modify: `09-tools/web/vm-studio/README.md`

**Step 1: Atualizar README com fluxo chat-first**

Incluir:
- fluxo oficial aprovado
- limitações conhecidas do piloto
- checklist de validação manual

**Step 2: Commit**

```bash
git add 09-tools/web/vm-studio/README.md
git commit -m "docs(vm-studio): document chat-first pilot workflow"
```

---

## Final Integration

**Step 1: Revisar commits e diff**

```bash
git log --oneline -n 12
git diff --stat origin/main...HEAD
```

**Step 2: Push**

```bash
git push origin <feature-branch>
```

**Step 3: Integrar após revisão**

- Merge com validação de smoke.
- Testar manualmente `http://127.0.0.1:8766/studio`.
