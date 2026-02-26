# VM Studio Deliverable-First Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformar o frontend atual do VM Studio em uma experiencia `deliverable-first`, com preview da `Versao ativa` no centro, `Pendencias desta versao` na direita e navegacao reduzida, sem alterar o backend `api/v2`.

**Architecture:** Refatoracao de apresentacao sobre o frontend React existente em `09-tools/web/vm-ui/src`, preservando `useWorkspace` e `useInbox` como base de dados. O trabalho sera dividido entre novo shell visual, reorganizacao de navegacao, canvas do entregavel e action rail operacional.

**Tech Stack:** React + TypeScript + Vite + Tailwind, Vitest + Testing Library, backend FastAPI `api/v2`.

---

### Task 1: Criar testes de layout do shell deliverable-first

**Files:**
- Create: `09-tools/web/vm-ui/src/App.layout.test.tsx`
- Test: `09-tools/web/vm-ui/src/test/setup.ts`

**Step 1: Write the failing test**

Criar `09-tools/web/vm-ui/src/App.layout.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

vi.mock("./features/navigation/NavigationPanel", () => ({
  default: () => <div>Navigation Panel</div>,
}));

vi.mock("./features/workspace/WorkspacePanel", () => ({
  default: () => <div>Workspace Panel</div>,
}));

vi.mock("./features/inbox/InboxPanel", () => ({
  default: () => <div>Inbox Panel</div>,
}));

describe("App shell", () => {
  it("renders top context shell and three main regions", () => {
    render(<App />);
    expect(screen.getByText("VM Studio")).toBeInTheDocument();
    expect(screen.getByText("Navigation Panel")).toBeInTheDocument();
    expect(screen.getByText("Workspace Panel")).toBeInTheDocument();
    expect(screen.getByText("Inbox Panel")).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/App.layout.test.tsx
```

Expected: FAIL if shell changes required labels/regions are absent.

**Step 3: Commit checkpoint**

```bash
git add 09-tools/web/vm-ui/src/App.layout.test.tsx
git commit -m "test(vm-ui): add shell layout coverage for deliverable-first redesign"
```

---

### Task 2: Refatorar `App.tsx` para o novo shell editorial

**Files:**
- Modify: `09-tools/web/vm-ui/src/App.tsx`
- Modify: `09-tools/web/vm-ui/src/styles/tailwind.css`
- Test: `09-tools/web/vm-ui/src/App.layout.test.tsx`

**Step 1: Write minimal implementation**

Atualizar [App.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/App.tsx) para:

- criar `top context bar` mais forte
- mover contexto de selecao para o topo
- trocar grid atual por shell `sidebar / canvas / action rail`
- manter `Dev mode` secundario

Adicionar tokens visuais em [tailwind.css](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/styles/tailwind.css):

```css
:root {
  color-scheme: light;
  --vm-bg: #f3f1eb;
  --vm-surface: rgba(255, 252, 247, 0.88);
  --vm-ink: #162033;
  --vm-muted: #64748b;
  --vm-line: rgba(22, 32, 51, 0.1);
  --vm-primary: #0f4c81;
  --vm-primary-strong: #0a3a63;
  --vm-warm: #f6efe4;
}

body {
  background:
    radial-gradient(circle at top left, rgba(15, 76, 129, 0.1), transparent 32%),
    radial-gradient(circle at bottom right, rgba(219, 174, 88, 0.12), transparent 30%),
    var(--vm-bg);
  color: var(--vm-ink);
}
```

**Step 2: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/App.layout.test.tsx
```

Expected: PASS.

**Step 3: Run build**

Run:

```bash
cd 09-tools/web/vm-ui && npm run build
```

Expected: PASS.

**Step 4: Commit**

```bash
git add 09-tools/web/vm-ui/src/App.tsx 09-tools/web/vm-ui/src/styles/tailwind.css 09-tools/web/vm-ui/src/App.layout.test.tsx
git commit -m "feat(vm-ui): introduce editorial shell for deliverable-first studio"
```

---

### Task 3: Reduzir a navegacao e mover o contexto principal para o topo

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/navigation/NavigationPanel.tsx`
- Create: `09-tools/web/vm-ui/src/features/navigation/NavigationPanel.test.tsx`

**Step 1: Write the failing test**

Criar `NavigationPanel.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import NavigationPanel from "./NavigationPanel";

describe("NavigationPanel", () => {
  it("renders reduced context sections for mode, versions and job context", () => {
    render(
      <NavigationPanel
        activeBrandId={null}
        activeProjectId={null}
        activeThreadId={null}
        devMode={false}
        onSelectBrand={() => {}}
        onSelectProject={() => {}}
        onSelectThread={() => {}}
      />
    );
    expect(screen.getByText(/marcas|cliente/i)).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/navigation/NavigationPanel.test.tsx
```

Expected: FAIL if reduced navigation structure is not yet represented.

**Step 3: Write minimal implementation**

Refatorar `NavigationPanel.tsx` para:

- reduzir peso visual das secoes de cadastro
- manter criacao/edicao, mas recolhida e secundaria
- destacar:
  - `Modo`
  - `Versoes`
  - `Contexto do Job`
- remover cara de admin CRUD da coluna

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/navigation/NavigationPanel.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/navigation/NavigationPanel.tsx 09-tools/web/vm-ui/src/features/navigation/NavigationPanel.test.tsx
git commit -m "feat(vm-ui): reduce navigation rail for deliverable-first flow"
```

---

### Task 4: Transformar o `WorkspacePanel` em `DeliverableCanvas`

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Modify: `09-tools/web/vm-ui/src/features/workspace/presentation.ts`
- Create: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.test.tsx`

**Step 1: Write the failing test**

Criar `WorkspacePanel.test.tsx` cobrindo:

- header da `Versao ativa`
- `Objetivo do pedido`
- acoes `Gerar nova versao`, `Baixar .md`, `Regenerar`
- preview como elemento dominante

Exemplo:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import WorkspacePanel from "./WorkspacePanel";

vi.mock("./useWorkspace", () => ({
  useWorkspace: () => ({
    profiles: [{ mode: "content_calendar", description: "Calendar" }],
    runs: [{ run_id: "run-1", status: "completed", requested_mode: "content_calendar", request_text: "Lancamento 2026", created_at: "2026-02-26T12:00:00Z" }],
    runDetail: { status: "completed" },
    timeline: [],
    primaryArtifact: { stageDir: "final", artifactPath: "deliverable.md", content: "# Entregavel" },
    loadingPrimaryArtifact: false,
    startRun: vi.fn(),
    resumeRun: vi.fn(),
    refreshRuns: vi.fn(),
    refreshTimeline: vi.fn(),
    refreshPrimaryArtifact: vi.fn(),
  }),
}));

describe("WorkspacePanel", () => {
  it("prioritizes the active deliverable", () => {
    render(<WorkspacePanel activeThreadId="t1" activeRunId="run-1" onSelectRun={() => {}} devMode={false} />);
    expect(screen.getByText(/entregavel principal/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /baixar \\.md/i })).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/WorkspacePanel.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

Refatorar `WorkspacePanel.tsx` para:

- transformar a coluna central em canvas dominante
- mover cabecalho da versao para o topo do preview
- destacar o pedido e o status
- manter timeline secundaria
- expor `Baixar .md` e `Regenerar` ao lado do CTA principal

Em `presentation.ts`, adicionar helpers visuais se necessario:

- labels mais editoriais
- resumo curto do pedido
- estado vazio humano

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/WorkspacePanel.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/features/workspace/presentation.ts 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.test.tsx
git commit -m "feat(vm-ui): redesign workspace as deliverable-first canvas"
```

---

### Task 5: Reposicionar `InboxPanel` como action rail da versao ativa

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx`
- Modify: `09-tools/web/vm-ui/src/features/inbox/presentation.ts`
- Create: `09-tools/web/vm-ui/src/features/inbox/InboxPanel.test.tsx`

**Step 1: Write the failing test**

Criar `InboxPanel.test.tsx` cobrindo:

- titulo `Pendencias desta versao`
- aprovacoes antes de historico
- CTA claros de `Aprovar`, `Concluir`, `Comentar`

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/InboxPanel.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

Refatorar `InboxPanel.tsx` para:

- trocar linguagem de `Inbox` por action rail contextual
- mostrar primeiro o que bloqueia a versao ativa
- recolher historico
- deixar artifacts secundarios abaixo das pendencias, nao no topo da leitura

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/InboxPanel.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx 09-tools/web/vm-ui/src/features/inbox/presentation.ts 09-tools/web/vm-ui/src/features/inbox/InboxPanel.test.tsx
git commit -m "feat(vm-ui): turn inbox into action rail for active deliverable"
```

---

### Task 6: Hardening visual e estados vazios

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Modify: `09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx`
- Modify: `09-tools/web/vm-ui/src/features/navigation/NavigationPanel.tsx`

**Step 1: Implement empty states and polish**

Adicionar:

- estado vazio forte sem `Job`
- estado vazio sem `Versao`
- skeleton ou loading humano para preview
- transicoes leves e feedback visual de selecao

**Step 2: Run full frontend tests**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run
```

Expected: PASS.

**Step 3: Run build**

Run:

```bash
cd 09-tools/web/vm-ui && npm run build
```

Expected: PASS.

**Step 4: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx 09-tools/web/vm-ui/src/features/navigation/NavigationPanel.tsx
git commit -m "feat(vm-ui): polish empty states and visual hierarchy for studio"
```

---

### Task 7: Verificacao final com frontend + backend real

**Files:**
- Modify: nenhuma obrigatoria

**Step 1: Run backend UI contract test**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills && uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_react_ui_contract -q
```

Expected: PASS.

**Step 2: Run frontend suite and build**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run && npm run build
```

Expected: PASS.

**Step 3: Manual smoke with running server**

Validar:

- seletor de contexto no topo
- preview dominante da versao ativa
- painel direito com pendencias
- download `.md`
- `Dev mode` escondendo IDs por padrao

**Step 4: Commit**

```bash
git commit --allow-empty -m "test(vm-ui): verify deliverable-first redesign with real backend"
```
