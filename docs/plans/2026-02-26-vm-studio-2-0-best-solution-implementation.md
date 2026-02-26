# VM Studio 2.0 Best Solution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Entregar o Balanced v1 com UX de agencia (`Cliente/Campanha/Job/Versao`), fluxo hibrido (Chat + Studio), timeline/inbox funcionais e artefato Markdown baixavel sem quebrar o backend `api/v2`.

**Architecture:** Evolucao incremental do frontend React atual (`09-tools/web/vm-ui/src`) com camada de adaptacao de contratos, normalizacao de estados de run/timeline/inbox, e melhorias de UX orientadas ao fluxo real de workflow-runs. Sem gerar conteudo fake e sem substituir backend.

**Tech Stack:** React + TypeScript + Vite + Tailwind, FastAPI `api/v2`, pytest (backend/UI assets), Vitest + Testing Library (frontend unit tests).

---

### Task 1: Base de testes frontend (Vitest) para prevenir regressao de contrato

**Files:**
- Modify: `09-tools/web/vm-ui/package.json`
- Create: `09-tools/web/vm-ui/vitest.config.ts`
- Create: `09-tools/web/vm-ui/src/test/setup.ts`

**Step 1: Write the failing test**

Create `09-tools/web/vm-ui/src/test/smoke.test.ts`:

```ts
import { describe, expect, it } from "vitest";

describe("frontend test harness", () => {
  it("runs vitest", () => {
    expect(true).toBe(true);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run`
Expected: FAIL (script `test` not found).

**Step 3: Write minimal implementation**

Update `package.json`:

```json
{
  "scripts": {
    "test": "vitest"
  },
  "devDependencies": {
    "vitest": "^2.1.8",
    "jsdom": "^25.0.1",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3"
  }
}
```

Create `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
```

Create `src/test/setup.ts`:

```ts
import "@testing-library/jest-dom";
```

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm install && npm run test -- --run`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/package.json 09-tools/web/vm-ui/package-lock.json 09-tools/web/vm-ui/vitest.config.ts 09-tools/web/vm-ui/src/test/setup.ts 09-tools/web/vm-ui/src/test/smoke.test.ts
git commit -m "test(vm-ui): add vitest harness for frontend contract tests"
```

---

### Task 2: Corrigir adapters de timeline (shape `{items}`) e eliminar timeline vazia

**Files:**
- Create: `09-tools/web/vm-ui/src/features/workspace/adapters.ts`
- Modify: `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts`
- Test: `09-tools/web/vm-ui/src/features/workspace/adapters.test.ts`

**Step 1: Write the failing test**

Create `adapters.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { mapTimelineResponse } from "./adapters";

describe("mapTimelineResponse", () => {
  it("maps API v2 items into timeline events", () => {
    const payload = {
      items: [
        {
          event_id: "evt-1",
          event_type: "WorkflowRunStarted",
          occurred_at: "2026-02-26T10:00:00Z",
          payload: { run_id: "run-1" },
        },
      ],
    };
    const events = mapTimelineResponse(payload);
    expect(events).toHaveLength(1);
    expect(events[0].created_at).toBe("2026-02-26T10:00:00Z");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/adapters.test.ts`
Expected: FAIL (`mapTimelineResponse` not found).

**Step 3: Write minimal implementation**

Create `adapters.ts`:

```ts
export type TimelineEvent = {
  event_id: string;
  event_type: string;
  created_at: string;
  payload: unknown;
};

export function mapTimelineResponse(input: unknown): TimelineEvent[] {
  const items = Array.isArray((input as any)?.items) ? (input as any).items : [];
  return items.map((item: any) => ({
    event_id: String(item.event_id ?? ""),
    event_type: String(item.event_type ?? "UnknownEvent"),
    created_at: String(item.occurred_at ?? item.created_at ?? ""),
    payload: item.payload ?? {},
  }));
}
```

Update `useWorkspace.ts` timeline fetch:

```ts
const data = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/timeline`);
setTimeline(mapTimelineResponse(data));
```

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/adapters.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/adapters.ts 09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts 09-tools/web/vm-ui/src/features/workspace/adapters.test.ts
git commit -m "fix(vm-ui): map timeline from api v2 items payload"
```

---

### Task 3: Corrigir adapters de tasks/approvals (shape `{items}`) e tornar inbox confiavel

**Files:**
- Create: `09-tools/web/vm-ui/src/features/inbox/adapters.ts`
- Modify: `09-tools/web/vm-ui/src/features/inbox/useInbox.ts`
- Test: `09-tools/web/vm-ui/src/features/inbox/adapters.test.ts`

**Step 1: Write the failing test**

Create `adapters.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { mapTasksResponse, mapApprovalsResponse } from "./adapters";

describe("inbox adapters", () => {
  it("maps tasks from items", () => {
    const tasks = mapTasksResponse({ items: [{ task_id: "t1", status: "pending", title: "Revisar" }] });
    expect(tasks[0].task_id).toBe("t1");
  });

  it("maps approvals from items", () => {
    const approvals = mapApprovalsResponse({ items: [{ approval_id: "a1", status: "pending", reason: "gate" }] });
    expect(approvals[0].approval_id).toBe("a1");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/adapters.test.ts`
Expected: FAIL (`mapTasksResponse` not found).

**Step 3: Write minimal implementation**

Create `adapters.ts` with `mapTasksResponse` and `mapApprovalsResponse` reading `items`.

Update `useInbox.ts`:

```ts
const tasksPayload = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/tasks`);
setTasks(mapTasksResponse(tasksPayload));

const approvalsPayload = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/approvals`);
setApprovals(mapApprovalsResponse(approvalsPayload));
```

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/adapters.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/inbox/adapters.ts 09-tools/web/vm-ui/src/features/inbox/useInbox.ts 09-tools/web/vm-ui/src/features/inbox/adapters.test.ts
git commit -m "fix(vm-ui): map tasks and approvals from api v2 items payload"
```

---

### Task 4: Terminologia de agencia + nomes humanos de versao

**Files:**
- Create: `09-tools/web/vm-ui/src/features/workspace/presentation.ts`
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Modify: `09-tools/web/vm-ui/src/App.tsx`
- Test: `09-tools/web/vm-ui/src/features/workspace/presentation.test.ts`

**Step 1: Write the failing test**

Create `presentation.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { toHumanRunName, toHumanStatus } from "./presentation";

describe("run presentation", () => {
  it("builds human run names", () => {
    const name = toHumanRunName({
      index: 2,
      requestText: "conteudo redes sociais",
      createdAt: "2026-02-26T14:20:00Z",
    });
    expect(name).toContain("Versao 2");
  });

  it("maps run status", () => {
    expect(toHumanStatus("waiting_approval")).toBe("Aguardando revisao");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/presentation.test.ts`
Expected: FAIL (`toHumanRunName` not found).

**Step 3: Write minimal implementation**

Create `presentation.ts`:

```ts
export function toHumanStatus(status: string): string {
  const map: Record<string, string> = {
    queued: "Em fila",
    running: "Gerando",
    waiting_approval: "Aguardando revisao",
    completed: "Pronto",
    failed: "Falhou",
  };
  return map[status] ?? status;
}

export function toHumanRunName(input: { index: number; requestText: string; createdAt?: string }): string {
  const short = input.requestText.trim().slice(0, 36) || "sem pedido";
  const hhmm = input.createdAt ? new Date(input.createdAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "--:--";
  return `Versao ${input.index} · ${short} · ${hhmm}`;
}
```

Update UI labels to `Cliente/Campanha/Job/Versao` in `App.tsx` and run cards in `WorkspacePanel.tsx`.

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/presentation.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/presentation.ts 09-tools/web/vm-ui/src/features/workspace/presentation.test.ts 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/App.tsx
git commit -m "feat(vm-ui): adopt agency terminology and human run naming"
```

---

### Task 5: Fluxo real de "Gerar nova versao" com request_text e profile

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts`
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Test: `09-tools/web/vm-ui/src/features/workspace/startRunPayload.test.ts`

**Step 1: Write the failing test**

Create `startRunPayload.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildStartRunPayload } from "./useWorkspace";

describe("buildStartRunPayload", () => {
  it("keeps user request_text instead of hardcoded text", () => {
    const payload = buildStartRunPayload({ mode: "content_calendar", requestText: "campanha lancamento 2026" });
    expect(payload.request_text).toBe("campanha lancamento 2026");
    expect(payload.mode).toBe("content_calendar");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/startRunPayload.test.ts`
Expected: FAIL (helper missing / hardcoded request).

**Step 3: Write minimal implementation**

In `useWorkspace.ts`:

```ts
export function buildStartRunPayload(input: { mode: string; requestText: string }) {
  return { mode: input.mode, request_text: input.requestText.trim() };
}
```

Change `startRun(mode)` to `startRun({ mode, requestText })`.

In `WorkspacePanel.tsx`:
- Replace current one-click run with modal/form:
  - campo `Objetivo do pedido`
  - select de `Profile`
  - CTA `Gerar nova versao`.

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/startRunPayload.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/features/workspace/startRunPayload.test.ts
git commit -m "feat(vm-ui): add real start-run flow with request text and profile"
```

---

### Task 6: Inbox em Pendentes/Historico + CTA operacional claro

**Files:**
- Create: `09-tools/web/vm-ui/src/features/inbox/presentation.ts`
- Modify: `09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx`
- Test: `09-tools/web/vm-ui/src/features/inbox/presentation.test.ts`

**Step 1: Write the failing test**

Create `presentation.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { splitInboxByStatus } from "./presentation";

describe("splitInboxByStatus", () => {
  it("moves completed approvals/tasks to history", () => {
    const result = splitInboxByStatus({
      tasks: [{ task_id: "t1", status: "completed", assigned_to: "", details: {} }],
      approvals: [{ approval_id: "a1", status: "pending", reason: "", required_role: "" }],
    });
    expect(result.pendingApprovals).toHaveLength(1);
    expect(result.historyTasks).toHaveLength(1);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/presentation.test.ts`
Expected: FAIL (`splitInboxByStatus` not found).

**Step 3: Write minimal implementation**

Create `presentation.ts` with `splitInboxByStatus`.

Update `InboxPanel.tsx`:
- add tabs `Pendentes` / `Historico`
- show approvals/tasks in pending with CTAs
- completed/granted items in historico.

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/presentation.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/inbox/presentation.ts 09-tools/web/vm-ui/src/features/inbox/presentation.test.ts 09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx
git commit -m "feat(vm-ui): add inbox pending/history split with clear actions"
```

---

### Task 7: Preview Markdown + download .md no artefato principal

**Files:**
- Modify: `09-tools/web/vm-ui/package.json`
- Create: `09-tools/web/vm-ui/src/features/inbox/ArtifactPreview.tsx`
- Modify: `09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx`
- Test: `09-tools/web/vm-ui/src/features/inbox/artifactDownload.test.ts`

**Step 1: Write the failing test**

Create `artifactDownload.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildMarkdownFilename } from "./ArtifactPreview";

describe("buildMarkdownFilename", () => {
  it("generates markdown filename", () => {
    expect(buildMarkdownFilename("Versao 3")).toBe("versao-3.md");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run src/features/inbox/artifactDownload.test.ts`
Expected: FAIL (`ArtifactPreview` helper missing).

**Step 3: Write minimal implementation**

Add deps in `package.json`:

```json
{
  "dependencies": {
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0"
  }
}
```

Create `ArtifactPreview.tsx` with:
- markdown renderer
- helper `buildMarkdownFilename`
- helper `downloadMarkdown`.

Wire `InboxPanel.tsx` to render main artifact in `ArtifactPreview`.

**Step 4: Run test to verify it passes**

Run: `cd 09-tools/web/vm-ui && npm install && npm run test -- --run src/features/inbox/artifactDownload.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/package.json 09-tools/web/vm-ui/package-lock.json 09-tools/web/vm-ui/src/features/inbox/ArtifactPreview.tsx 09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx 09-tools/web/vm-ui/src/features/inbox/artifactDownload.test.ts
git commit -m "feat(vm-ui): render markdown artifacts and add .md download action"
```

---

### Task 8: Verificacao final (frontend + backend tests + build)

**Files:**
- Modify (if needed): `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify (if needed): `09-tools/tests/test_vm_webapp_ui_shell.py`

**Step 1: Run focused frontend tests**

Run: `cd 09-tools/web/vm-ui && npm run test -- --run`
Expected: PASS.

**Step 2: Build UI dist**

Run: `cd 09-tools/web/vm-ui && npm run build`
Expected: PASS and updated `dist/`.

**Step 3: Run backend/ui asset tests**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/tests/test_vm_webapp_ui_shell.py -v`
Expected: PASS.

**Step 4: Run one API v2 regression test**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_api_v2_workflow_run_cycle_includes_approvals_and_artifacts -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/dist 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/tests/test_vm_webapp_ui_shell.py
git commit -m "test(vm-ui): verify balanced v1 flow with real api v2 contracts"
```

---

Plan complete and saved to `docs/plans/2026-02-26-vm-studio-2-0-best-solution-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
