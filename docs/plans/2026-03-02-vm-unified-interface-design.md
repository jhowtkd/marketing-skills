# VM Unified Interface Design

> Unificação das interfaces VM-UI e VM-Studio com estética Raycast-style.
> Hybrid Edition — Layout 3 colunas com toggle Guided/Dev mode.

---

## 1. Overview

### 1.1 Problema
- Duas interfaces separadas (vm-ui e vm-studio) com experiências desconexas
- Usuários precisam "aprender" dois modos de operação
- Manutenção de duas codebases duplica esforço

### 1.2 Solução
Interface única com:
- **Layout persistente:** 3 colunas (Navigation | Workspace | Command Rail)
- **Modo toggle:** Guided mode (chat-first) ↔ Dev mode (technical) na coluna central
- **Estética Raycast:** Dark mode default, command palette, atalhos de teclado, transições refinadas

### 1.3 Sucesso
- Usuário alterna entre modos sem perder contexto
- Mesma codebase, comportamento unificado
- Experiência "premium" alinhada com referências modernas

---

## 2. Arquitetura Visual

### 2.1 Paleta de Cores

```css
/* Tokens CSS --vm-* */

/* Fundos */
--vm-bg: #0F0F0F;
--vm-surface: #1A1A1A;
--vm-surface-elevated: #242424;
--vm-border: #2A2A2A;

/* Texto */
--vm-ink: #F5F5F5;
--vm-ink-muted: #8A8A8A;
--vm-ink-subtle: #5A5A5A;

/* Acentos */
--vm-primary: #FF6B35;
--vm-primary-dim: rgba(255, 107, 53, 0.12);
--vm-success: #4ADE80;
--vm-warning: #FBBF24;
--vm-error: #F87171;

/* Estados */
--vm-hover: rgba(255, 255, 255, 0.06);
--vm-active: rgba(255, 255, 255, 0.1);
```

### 2.2 Tipografia

- **Fonte principal:** Inter, system-ui, sans-serif
- **Fonte mono:** JetBrains Mono (dev mode, IDs, logs)
- **Escala:**
  - `xs`: 11px / 16px line-height
  - `sm`: 13px / 20px
  - `base`: 14px / 22px
  - `lg`: 16px / 24px
  - `xl`: 20px / 28px
  - `2xl`: 24px / 32px

### 2.3 Dimensões & Sombras

```css
--radius-sm: 6px;
--radius-md: 10px;
--radius-lg: 14px;
--radius-xl: 20px;

--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
--shadow-glow: 0 0 20px rgba(255, 107, 53, 0.15);
```

### 2.4 Layout Grid

```
┌─────────────────────────────────────────────────────────────────┐
│ Header (56px)                                                   │
├──────────────┬──────────────────────────────┬───────────────────┤
│              │                              │                   │
│ Navigation   │       Workspace              │   Command Rail    │
│  (260px)     │       (flex: 1)              │   (300px)         │
│              │                              │                   │
│  min-w-64    │       min-w-0                │   min-w-72        │
│              │                              │                   │
└──────────────┴──────────────────────────────┴───────────────────┘
              ↑                              ↑
        Resizable (drag)               Resizable (drag)
```

---

## 3. Componentes

### 3.1 Header

```tsx
<header className="h-14 border-b border-[var(--vm-border)] bg-[var(--vm-bg)] flex items-center px-4">
  {/* Logo */}
  <div className="flex items-center gap-2">
    <div className="w-6 h-6 rounded-md bg-[var(--vm-primary)] flex items-center justify-center">
      <span className="text-white font-bold text-xs">VM</span>
    </div>
    <span className="font-semibold text-[var(--vm-ink)]">Vibe Marketing</span>
  </div>

  {/* Breadcrumb Context */}
  <nav className="ml-8 flex items-center gap-1 text-sm">
    <span className="text-[var(--vm-ink)]">Acme Corp</span>
    <ChevronRight className="w-4 h-4 text-[var(--vm-ink-subtle)]" />
    <span className="text-[var(--vm-ink)]">Q1 Launch</span>
    <ChevronRight className="w-4 h-4 text-[var(--vm-ink-subtle)]" />
    <span className="text-[var(--vm-primary)]">Landing Page</span>
  </nav>

  {/* Right Actions */}
  <div className="ml-auto flex items-center gap-2">
    <button className="p-2 rounded-md hover:bg-[var(--vm-hover)]">
      <Search className="w-4 h-4 text-[var(--vm-ink-muted)]" />
    </button>
    <ModeToggle /> {/* Guided ↔ Dev */}
    <UserMenu />
  </div>
</header>
```

### 3.2 Navigation Panel (Esquerda)

Collapsible tree com hierarquia Brand → Project → Thread.

```tsx
// Estrutura
<div className="h-full overflow-y-auto p-3 space-y-1">
  {/* Section Header */}
  <div className="px-2 py-1.5 text-xs font-medium text-[var(--vm-ink-subtle)] uppercase tracking-wider">
    Brands
  </div>

  {/* Brand Item */}
  <div className="group">
    <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--vm-hover)]">
      <ChevronDown className="w-3.5 h-3.5 text-[var(--vm-ink-muted)]" />
      <span className="text-sm font-medium text-[var(--vm-ink)]">Acme Corp</span>
      <button className="ml-auto opacity-0 group-hover:opacity-100 p-1 hover:bg-[var(--vm-hover)] rounded">
        <MoreHorizontal className="w-3.5 h-3.5" />
      </button>
    </button>

    {/* Children */}
    <div className="ml-4 mt-0.5 space-y-0.5 border-l border-[var(--vm-border)] pl-2">
      {/* Project */}
      <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--vm-hover)]">
        <ChevronRight className="w-3.5 h-3.5 text-[var(--vm-ink-subtle)]" />
        <span className="text-sm text-[var(--vm-ink-muted)]">Q1 Launch</span>
      </button>

      {/* Threads */}
      <div className="ml-4 space-y-0.5">
        <button className="w-full text-left px-2 py-1.5 rounded-md text-sm bg-[var(--vm-primary-dim)] text-[var(--vm-primary)]">
          Landing Page v2
        </button>
        <button className="w-full text-left px-2 py-1.5 rounded-md text-sm text-[var(--vm-ink-muted)] hover:bg-[var(--vm-hover)]">
          Email Sequence
        </button>
      </div>
    </div>
  </div>

  {/* New Button */}
  <button className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-dashed border-[var(--vm-border)] text-sm text-[var(--vm-ink-muted)] hover:border-[var(--vm-primary)] hover:text-[var(--vm-primary)] transition-colors">
    <Plus className="w-4 h-4" />
    New Brand
  </button>
</div>
```

### 3.3 Workspace (Central) — Modo Toggle

**Guided Mode:**
```tsx
<div className="h-full flex flex-col">
  {/* Chat Input (estado inicial) */}
  <div className="flex-1 flex flex-col items-center justify-center p-8">
    <h1 className="text-2xl font-semibold text-[var(--vm-ink)] mb-2">
      What do you want to create?
    </h1>
    <p className="text-[var(--vm-ink-muted)] mb-8">
      Describe your goal and I'll suggest the best templates.
    </p>

    {/* Input Container */}
    <div className="w-full max-w-2xl">
      <div className="relative">
        <textarea
          className="w-full h-32 p-4 rounded-xl bg-[var(--vm-surface)] border border-[var(--vm-border)] text-[var(--vm-ink)] placeholder:text-[var(--vm-ink-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--vm-primary)]/20 resize-none"
          placeholder="e.g., Landing page for B2B consulting leads..."
        />
        <button className="absolute bottom-3 right-3 px-4 py-1.5 rounded-lg bg-[var(--vm-primary)] text-white text-sm font-medium hover:opacity-90">
          Generate
        </button>
      </div>

      {/* Quick Suggestions */}
      <div className="mt-4 flex flex-wrap gap-2">
        {examples.map((ex) => (
          <button
            key={ex}
            className="px-3 py-1.5 rounded-full border border-[var(--vm-border)] text-sm text-[var(--vm-ink-muted)] hover:border-[var(--vm-primary)] hover:text-[var(--vm-primary)] transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  </div>
</div>
```

**Dev Mode:**
```tsx
<div className="h-full flex flex-col p-4">
  {/* Context Cards */}
  <div className="grid grid-cols-3 gap-3 mb-4">
    <ContextCard label="Brand" value="Acme Corp" />
    <ContextCard label="Project" value="Q1 Launch" />
    <ContextCard label="Thread" value="Landing Page v2" />
  </div>

  {/* DAG Visualization */}
  <div className="flex-1 rounded-xl bg-[var(--vm-surface)] border border-[var(--vm-border)] p-4 overflow-auto">
    <DAGViewer stages={stages} currentStage={currentStage} />
  </div>

  {/* Log Panel (collapsible) */}
  <div className="mt-4 h-48 rounded-xl bg-[var(--vm-surface)] border border-[var(--vm-border)]">
    <LogViewer logs={logs} />
  </div>
</div>
```

### 3.4 Command Rail (Direita)

```tsx
<div className="h-full flex flex-col bg-[var(--vm-surface)] border-l border-[var(--vm-border)]">
  {/* Command Input */}
  <div className="p-3 border-b border-[var(--vm-border)]">
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--vm-bg)] border border-[var(--vm-border)]">
      <Command className="w-4 h-4 text-[var(--vm-ink-muted)]" />
      <input
        type="text"
        placeholder="Type a command..."
        className="flex-1 bg-transparent text-sm text-[var(--vm-ink)] placeholder:text-[var(--vm-ink-subtle)] outline-none"
      />
      <kbd className="px-1.5 py-0.5 rounded bg-[var(--vm-surface-elevated)] text-xs text-[var(--vm-ink-muted)]">
        ⌘K
      </kbd>
    </div>
  </div>

  {/* Contextual Actions */}
  <div className="flex-1 overflow-y-auto p-2">
    {/* Run Actions */}
    <div className="mb-4">
      <div className="px-2 py-1.5 text-xs font-medium text-[var(--vm-ink-subtle)] uppercase tracking-wider">
        Run Actions
      </div>
      <div className="mt-1 space-y-0.5">
        <CommandItem
          icon={Play}
          label="Resume Workflow"
          shortcut="⌘R"
          onClick={resumeRun}
        />
        <CommandItem
          icon={CheckCircle}
          label="Approve Stage"
          shortcut="⌘A"
          onClick={approveStage}
        />
        <CommandItem
          icon={RotateCcw}
          label="Retry Stage"
          onClick={retryStage}
        />
      </div>
    </div>

    {/* Stage Status */}
    <div className="mb-4">
      <div className="px-2 py-1.5 text-xs font-medium text-[var(--vm-ink-subtle)] uppercase tracking-wider">
        Stage Status
      </div>
      <div className="mt-1 space-y-0.5">
        {stages.map((stage) => (
          <StageStatusItem
            key={stage.key}
            name={stage.name}
            status={stage.status}
          />
        ))}
      </div>
    </div>

    {/* Artifacts */}
    <div className="mb-4">
      <div className="px-2 py-1.5 text-xs font-medium text-[var(--vm-ink-subtle)] uppercase tracking-wider">
        Artifacts
      </div>
      <div className="mt-1 space-y-0.5">
        {artifacts.map((artifact) => (
          <ArtifactItem
            key={artifact.path}
            name={artifact.name}
            type={artifact.type}
            onClick={() => previewArtifact(artifact)}
          />
        ))}
      </div>
    </div>

    {/* Dev Tools */}
    <div>
      <div className="px-2 py-1.5 text-xs font-medium text-[var(--vm-ink-subtle)] uppercase tracking-wider">
        Dev Tools
      </div>
      <div className="mt-1 space-y-0.5">
        <CommandItem
          icon={FileJson}
          label="View Raw JSON"
          onClick={viewRawJson}
        />
        <CommandItem
          icon={Copy}
          label="Copy Thread ID"
          onClick={copyThreadId}
        />
        <CommandItem
          icon={ScrollText}
          label="Open Logs"
          onClick={openLogs}
        />
      </div>
    </div>
  </div>

  {/* Footer Status */}
  <div className="p-3 border-t border-[var(--vm-border)] text-xs text-[var(--vm-ink-subtle)]">
    <div className="flex justify-between">
      <span>Run ID</span>
      <span className="font-mono text-[var(--vm-ink)]">run_abc123</span>
    </div>
    <div className="flex justify-between mt-1">
      <span>Status</span>
      <span className="text-[var(--vm-success)]">Running</span>
    </div>
  </div>
</div>
```

---

## 4. Interações

### 4.1 Transições

| Ação | Duração | Easing | Efeito |
|------|---------|--------|--------|
| Mode toggle | 200ms | ease-in-out | Crossfade opacity |
| Panel expand | 300ms | cubic-bezier(0.16, 1, 0.3, 1) | Width animation |
| Item hover | 150ms | ease | Background color |
| Card select | 200ms | cubic-bezier(0.34, 1.56, 0.64, 1) | Scale + elevation |
| Command palette | 150ms | ease-out | Slide down + fade |

### 4.2 Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `⌘K` | Focus command input |
| `⌘D` | Toggle Guided/Dev mode |
| `⌘1` | Focus Navigation panel |
| `⌘2` | Focus Workspace panel |
| `⌘3` | Focus Command Rail |
| `⌘N` | New (context-aware: Brand/Project/Thread) |
| `⌘R` | Resume current run |
| `⌘A` | Approve current stage |
| `⌘Shift+R` | Retry current stage |
| `Esc` | Clear selection / Close modal / Blur focus |
| `?` | Show keyboard shortcuts help |

### 4.3 Estados Vazios

**No Brand:**
- Central CTA: "Create your first brand"
- Subtext: "Start by defining your brand voice and positioning"
- Action: Button primary "Create Brand"

**No Run Active:**
- Command Rail mostra "No active run"
- Sugestões: "Start from chat" ou "Create new thread"

**No Artifacts:**
- Stage Status mostra placeholders
- Artifacts section: "Run workflow to generate artifacts"

---

## 5. Estrutura de Arquivos

```
09-tools/web/vm-unified/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── studio/
│   │       ├── layout.tsx
│   │       └── page.tsx
│   │
│   ├── components/
│   │   ├── ui/
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── kbd.tsx
│   │   │   ├── select.tsx
│   │   │   ├── textarea.tsx
│   │   │   └── tooltip.tsx
│   │   │
│   │   ├── layout/
│   │   │   ├── header.tsx
│   │   │   ├── mode-toggle.tsx
│   │   │   ├── navigation-panel.tsx
│   │   │   ├── command-rail.tsx
│   │   │   ├── workspace.tsx
│   │   │   └── resizable-panel.tsx
│   │   │
│   │   ├── guided/
│   │   │   ├── chat-input.tsx
│   │   │   ├── template-card.tsx
│   │   │   ├── template-grid.tsx
│   │   │   ├── generating-state.tsx
│   │   │   ├── deliverable-view.tsx
│   │   │   └── refine-chat.tsx
│   │   │
│   │   └── dev/
│   │       ├── context-cards.tsx
│   │       ├── dag-viewer.tsx
│   │       ├── stage-node.tsx
│   │       ├── log-viewer.tsx
│   │       ├── artifact-preview.tsx
│   │       └── json-viewer.tsx
│   │
│   ├── hooks/
│   │   ├── use-keyboard.ts
│   │   ├── use-mode-toggle.ts
│   │   ├── use-navigation.ts
│   │   ├── use-command-palette.ts
│   │   └── use-store.ts
│   │
│   ├── lib/
│   │   ├── utils.ts
│   │   ├── theme.ts
│   │   ├── commands.ts
│   │   └── api-client.ts
│   │
│   ├── styles/
│   │   └── globals.css
│   │
│   └── types/
│       └── index.ts
│
├── public/
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── vite.config.ts (ou next.config.js)
```

---

## 6. Migração de Dados

### 6.1 Store Unificado

Migrar estado de:
- `vm-studio/src/store/index.ts`
- `vm-ui/src/features/navigation/useNavigation.ts`
- `vm-ui/src/features/workspace/useWorkspace.ts`
- `vm-ui/src/features/inbox/useInbox.ts`

Para store Zustand único em `vm-unified/src/hooks/use-store.ts`.

### 6.2 API Client

Reaproveitar cliente API de:
- `vm-studio/src/api/client.ts`
- `vm-ui/src/lib/api.ts` (se existir)

### 6.3 Assets Estáticos

Mover assets compartilhados para `vm-unified/public/`.

---

## 7. Decisões

### 7.1 Decidido
- Dark mode default, light mode opcional
- Layout 3 colunas persistente
- Toggle Guided/Dev na coluna central
- Command Rail fixo à direita
- Raycast-style estética e interações
- Resizable panels (drag para redimensionar)

### 7.2 Aberto (para implementação)
- Framework: Next.js vs Vite + React Router
- State management: Zustand vs Redux Toolkit
- Styling: Tailwind + CSS variables (confirmado)
- Animações: Framer Motion vs CSS transitions
- Monorepo: manter vm-ui e vm-studio durante migração

---

## 8. Referências

- Raycast: raycast.com (estética, command palette, atalhos)
- Linear: linear.app (empty states, transições)
- Vercel: vercel.com/dashboard (layout, cards)
- Notion: notion.so (navegação em árvore)

---

## 9. Notas de Implementação

1. **Performance:** Virtualizar lista de threads se > 100 items
2. **Acessibilidade:** ARIA labels em todos os comandos, foco visível
3. **Mobile:** Layout responsivo (empilhar colunas em < 1024px)
4. **SSR:** Considerar hydration para estado inicial do store
5. **Testes:** E2E para fluxos críticos (create → run → approve)

---

*Design aprovado em: 2026-03-02*
*Próximo passo: Plano de implementação*
