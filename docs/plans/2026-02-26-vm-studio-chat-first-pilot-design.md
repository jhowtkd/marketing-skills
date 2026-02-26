# VM Studio Chat-First Pilot — Design

## Status
Aprovado para implementação em piloto (`/studio`).

---

## 1. Objetivo

Transformar o Studio em uma experiência linear e utilizável para agência:

- Entrada principal em **chat-first**.
- Sugestão de **3 templates** após o pedido inicial.
- Entrega focada em **entregável principal + próximos passos**.
- CTA primário pós-geração: **Refinar no chat**.
- Rollout seguro em **`/studio`**, sem quebrar o fluxo atual em `/`.

---

## 2. Fluxo do Usuário

```text
Chat Input
  -> Sugestão de 3 templates
  -> Seleção de 1 template
  -> Geração do entregável
  -> Entregável pronto
  -> Refinar no chat
```

### 2.1 Tela de Entrada (Chat-First)
- Campo principal de pedido (linguagem natural).
- Exemplos de prompt para reduzir blank state.
- Lista curta de conversas/projetos recentes (lateral discreta).

### 2.2 Sugestão de Templates
- Exibir 3 opções com:
  - nome humano
  - resumo curto
  - justificativa da sugestão
- Usuário escolhe 1 template e segue para geração.

### 2.3 Entregável
- Foco na peça principal formatada (Markdown renderizado).
- Área de “próximos passos” acionáveis.
- Ações secundárias: exportar, salvar, voltar ao projeto.
- Ação primária: **Refinar no chat**.

---

## 3. Arquitetura de Experiência

### 3.1 Princípios
- Um objetivo por tela.
- Terminologia humana; sem IDs técnicos fora de debug.
- Feedback visível de progresso e estados.
- Zero bloqueio: fallback manual se sugestão falhar.

### 3.2 Fases de Estado
- `chat_input`
- `template_suggestion`
- `generating`
- `deliverable_ready`
- `refining`

### 3.3 Componentes Principais
- `ChatHomeView`
- `TemplateSuggestionView`
- `DeliverableView`
- `ProjectRail` (compacto)
- `InboxLight` (pendências acionáveis)

---

## 4. Contratos e Integração

- Reutilizar APIs v2 já existentes; sem migração de backend neste passo.
- Manter adapter de frontend para traduzir payload técnico em linguagem de produto.
- Endpoint de entrada permanece no backend atual; nova UX servida em `/studio`.

### 4.1 Fallbacks
- Falha na sugestão de templates -> abre seleção manual.
- Falha de geração -> preservar contexto e permitir retry com 1 clique.

---

## 5. Direção Visual

Direção aprovada: **Editorial premium**.

- Tipografia com presença e hierarquia clara.
- Layout limpo, densidade moderada, foco no conteúdo.
- Contraste e espaçamento consistentes.
- Menos aparência de painel técnico, mais sensação de estúdio.

---

## 6. Rollout

### Fase 1
- Piloto interno em `/studio`.
- Coleta de feedback qualitativo + métricas básicas.

### Fase 2
- Ajustes de UX e linguagem com base em uso real.

### Fase 3
- Decisão: manter `/studio` como fluxo premium ou promover para `/`.

---

## 7. Métricas de Sucesso

- Tempo até primeiro entregável.
- Taxa de conclusão do fluxo completo.
- Taxa de clique em “Refinar no chat”.
- Redução de dúvidas operacionais (suporte interno).

---

## 8. Critérios de Aceite

1. Usuário cria um entregável sem ver termos técnicos internos.
2. Fluxo completo funciona sem travar: pedido -> sugestão -> entrega -> refinamento.
3. Ação “Refinar no chat” é claramente primária.
4. `/` continua estável; `/studio` opera em piloto independente.
