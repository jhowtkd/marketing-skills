# VM Studio Quality Compare + Guided Regeneration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar comparacao de versoes (`scorecard + diff`), score hibrido de qualidade (`heuristico local + deep opcional`) e regeneracao guiada (`presets + prompt assistido`) no VM Studio sem quebrar o fluxo atual.

**Architecture:** Implementacao incremental sobre o frontend React atual (`09-tools/web/vm-ui/src`) com motor heuristico local como base e integracao opcional para deep evaluation via API v2. A comparacao e regeneracao ficam acopladas ao `WorkspacePanel` da `Versao ativa`.

**Tech Stack:** React + TypeScript + Vite + Tailwind, Vitest + Testing Library, FastAPI `api/v2` (endpoint opcional de deep eval), pytest para contrato backend.

---

### Task 1: Criar tipos e motor heuristico local de qualidade

**Files:**
- Create: `09-tools/web/vm-ui/src/features/quality/types.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/score.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/score.test.ts`

**Step 1: Write the failing test**

Criar `score.test.ts` com casos base:

```ts
import { describe, expect, it } from "vitest";
import { computeQualityScore } from "./score";

describe("computeQualityScore", () => {
  it("scores structured markdown higher than sparse text", () => {
    const structured = "# Titulo\n## Problema\nTexto\n## Solucao\nTexto\n## CTA\nAcao";
    const sparse = "texto curto sem estrutura";

    const a = computeQualityScore(structured);
    const b = computeQualityScore(sparse);

    expect(a.overall).toBeGreaterThan(b.overall);
  });

  it("returns actionable recommendations when criteria are weak", () => {
    const result = computeQualityScore("texto curto");
    expect(result.recommendations.length).toBeGreaterThan(0);
  });
});
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/score.test.ts
```

Expected: FAIL (`computeQualityScore` inexistente).

**Step 3: Write minimal implementation**

`types.ts`:

```ts
export type QualityCriteriaKey = "completude" | "estrutura" | "clareza" | "cta" | "acionabilidade";

export type QualityScore = {
  overall: number;
  criteria: Record<QualityCriteriaKey, number>;
  recommendations: string[];
  source: "heuristic" | "deep";
};
```

`score.ts`:

- implementar `computeQualityScore(markdown: string): QualityScore`
- usar heuristicas simples (headings, tamanho, CTA keywords, listas, verbos de acao)
- limitar score em `0..100`

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/score.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/quality/types.ts 09-tools/web/vm-ui/src/features/quality/score.ts 09-tools/web/vm-ui/src/features/quality/score.test.ts
git commit -m "feat(vm-ui): add local heuristic quality scoring engine"
```

---

### Task 2: Criar scorecard comparativo e algoritmo de delta

**Files:**
- Create: `09-tools/web/vm-ui/src/features/quality/compare.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/compare.test.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/QualityScoreCard.tsx`
- Create: `09-tools/web/vm-ui/src/features/quality/QualityScoreCard.test.tsx`

**Step 1: Write the failing test**

`compare.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { compareScores } from "./compare";

it("computes criteria deltas between versions", () => {
  const result = compareScores(
    { overall: 80, criteria: { completude: 90, estrutura: 80, clareza: 70, cta: 80, acionabilidade: 80 }, recommendations: [], source: "heuristic" },
    { overall: 60, criteria: { completude: 50, estrutura: 60, clareza: 60, cta: 70, acionabilidade: 60 }, recommendations: [], source: "heuristic" },
  );
  expect(result.overallDelta).toBe(20);
  expect(result.criteriaDelta.completude).toBe(40);
});
```

`QualityScoreCard.test.tsx`:

- validar render do score geral
- validar indicador de delta positivo/negativo

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/compare.test.ts src/features/quality/QualityScoreCard.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

- `compare.ts`: `compareScores(current, baseline)`
- `QualityScoreCard.tsx`: componente do scorecard lado a lado

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/compare.test.ts src/features/quality/QualityScoreCard.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/quality/compare.ts 09-tools/web/vm-ui/src/features/quality/compare.test.ts 09-tools/web/vm-ui/src/features/quality/QualityScoreCard.tsx 09-tools/web/vm-ui/src/features/quality/QualityScoreCard.test.tsx
git commit -m "feat(vm-ui): add quality scorecard with version delta comparison"
```

---

### Task 3: Criar diff textual amigavel para versoes

**Files:**
- Create: `09-tools/web/vm-ui/src/features/quality/diff.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/diff.test.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/VersionDiffPanel.tsx`
- Create: `09-tools/web/vm-ui/src/features/quality/VersionDiffPanel.test.tsx`

**Step 1: Write the failing test**

`diff.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { computeLineDiff } from "./diff";

it("marks added and removed lines", () => {
  const out = computeLineDiff("linha A\nlinha B", "linha A\nlinha C");
  expect(out.some((l) => l.type === "removed" && l.text.includes("linha B"))).toBe(true);
  expect(out.some((l) => l.type === "added" && l.text.includes("linha C"))).toBe(true);
});
```

`VersionDiffPanel.test.tsx`:

- validar render de blocos `added` e `removed`

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/diff.test.ts src/features/quality/VersionDiffPanel.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

- implementar `computeLineDiff` em `diff.ts`
- implementar painel visual em `VersionDiffPanel.tsx`

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/diff.test.ts src/features/quality/VersionDiffPanel.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/quality/diff.ts 09-tools/web/vm-ui/src/features/quality/diff.test.ts 09-tools/web/vm-ui/src/features/quality/VersionDiffPanel.tsx 09-tools/web/vm-ui/src/features/quality/VersionDiffPanel.test.tsx
git commit -m "feat(vm-ui): add textual version diff panel"
```

---

### Task 4: Criar modal de regeneracao guiada (presets + assistido)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/quality/guidedRegenerate.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/guidedRegenerate.test.ts`
- Create: `09-tools/web/vm-ui/src/features/quality/GuidedRegenerateModal.tsx`
- Create: `09-tools/web/vm-ui/src/features/quality/GuidedRegenerateModal.test.tsx`

**Step 1: Write the failing test**

`guidedRegenerate.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildGuidedRequest } from "./guidedRegenerate";

it("builds request text using presets and user guidance", () => {
  const text = buildGuidedRequest({
    baseRequest: "Plano de lancamento",
    presets: ["mais_profundo", "mais_persuasivo"],
    userGuidance: "focar em ICP B2B",
    weakPoints: ["CTA fraco"],
  });
  expect(text).toContain("Plano de lancamento");
  expect(text).toContain("ICP B2B");
  expect(text).toContain("CTA fraco");
});
```

`GuidedRegenerateModal.test.tsx`:

- validar selecao de presets
- validar submit com payload consolidado

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/guidedRegenerate.test.ts src/features/quality/GuidedRegenerateModal.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

- implementar `buildGuidedRequest` em `guidedRegenerate.ts`
- implementar modal em `GuidedRegenerateModal.tsx`

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/guidedRegenerate.test.ts src/features/quality/GuidedRegenerateModal.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/quality/guidedRegenerate.ts 09-tools/web/vm-ui/src/features/quality/guidedRegenerate.test.ts 09-tools/web/vm-ui/src/features/quality/GuidedRegenerateModal.tsx 09-tools/web/vm-ui/src/features/quality/GuidedRegenerateModal.test.tsx
git commit -m "feat(vm-ui): add guided regeneration modal with presets and assisted prompt"
```

---

### Task 5: Integrar score/comparacao/regeneracao ao WorkspacePanel

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Modify: `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts`
- Modify: `09-tools/web/vm-ui/src/features/workspace/presentation.ts`
- Create: `09-tools/web/vm-ui/src/features/workspace/WorkspaceQualityFlow.test.tsx`

**Step 1: Write the failing test**

Criar `WorkspaceQualityFlow.test.tsx` cobrindo:

- render de scorecard na versao ativa
- comparacao com versao anterior
- abertura do modal de regeneracao guiada

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/WorkspaceQualityFlow.test.tsx
```

Expected: FAIL.

**Step 3: Write minimal implementation**

- calcular score heuristico do artefato ativo
- selecionar baseline (versao anterior por default)
- render `QualityScoreCard` + `VersionDiffPanel`
- acionar `GuidedRegenerateModal` e chamar `startRun` com payload guiado

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/WorkspaceQualityFlow.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts 09-tools/web/vm-ui/src/features/workspace/presentation.ts 09-tools/web/vm-ui/src/features/workspace/WorkspaceQualityFlow.test.tsx
git commit -m "feat(vm-ui): integrate quality comparison and guided regeneration into workspace"
```

---

### Task 6: Endpoint opcional de avaliacao profunda no backend v2

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Create: `09-tools/vm_webapp/quality_eval.py`
- Create: `09-tools/tests/test_vm_webapp_quality_eval_api_v2.py`

**Step 1: Write the failing test**

Criar `test_vm_webapp_quality_eval_api_v2.py`:

```python
from pathlib import Path
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_quality_evaluation_endpoint_returns_structured_payload(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    response = client.post(
        "/api/v2/workflow-runs/run-missing/quality-evaluation",
        headers={"Idempotency-Key": "quality-1"},
        json={"depth": "deep", "rubric_version": "v1"},
    )

    assert response.status_code in {200, 404}
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills && PYTHONPATH=09-tools /Users/jhonatan/Repos/marketing-skills/.venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_quality_eval_api_v2.py -q
```

Expected: FAIL (endpoint inexistente).

**Step 3: Write minimal implementation**

- criar `quality_eval.py` com funcao de avaliacao profunda e fallback
- adicionar endpoint `POST /api/v2/workflow-runs/{run_id}/quality-evaluation`
- se run nao existir: `404`
- se avaliacao profunda falhar: retornar fallback heuristico em `200`

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills && PYTHONPATH=09-tools /Users/jhonatan/Repos/marketing-skills/.venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_quality_eval_api_v2.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/vm_webapp/quality_eval.py 09-tools/tests/test_vm_webapp_quality_eval_api_v2.py
git commit -m "feat(api-v2): add optional deep quality evaluation endpoint for workflow runs"
```

---

### Task 7: Integrar deep evaluation opcional no frontend

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts`
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx`
- Create: `09-tools/web/vm-ui/src/features/quality/deepEval.test.ts`

**Step 1: Write the failing test**

Criar `deepEval.test.ts` para validar:

- request para endpoint correto
- fallback para score local quando API falha

**Step 2: Run test to verify it fails**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/deepEval.test.ts
```

Expected: FAIL.

**Step 3: Write minimal implementation**

- adicionar acao `requestDeepEvaluation(runId)` em `useWorkspace`
- armazenar estado `deepEvaluation` por versao
- botao `Avaliar profundo` no `WorkspacePanel`
- fallback visual para score heuristico quando erro

**Step 4: Run test to verify it passes**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/quality/deepEval.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts 09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx 09-tools/web/vm-ui/src/features/quality/deepEval.test.ts
git commit -m "feat(vm-ui): support optional deep quality evaluation with safe fallback"
```

---

### Task 8: Verificacao final (frontend + backend + smoke)

**Files:**
- Modify: nenhuma obrigatoria

**Step 1: Run frontend tests and build**

Run:

```bash
cd 09-tools/web/vm-ui && npm run test -- --run && npm run build
```

Expected: PASS.

**Step 2: Run backend tests**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills && PYTHONPATH=09-tools /Users/jhonatan/Repos/marketing-skills/.venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_quality_eval_api_v2.py 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_react_ui_contract -q
```

Expected: PASS.

**Step 3: Manual smoke in Studio**

Validar no browser:

- score local visivel na versao ativa
- comparacao scorecard + diff entre duas versoes
- `Avaliar profundo` sem quebrar fluxo quando indisponivel
- modal de regeneracao guiada criando nova versao
- download `.md` permanecendo funcional

**Step 4: Commit final de verificacao**

```bash
git commit --allow-empty -m "test(vm-ui): verify quality compare and guided regeneration flow"
```
