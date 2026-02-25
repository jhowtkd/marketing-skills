# VM Webapp Stitch Hybrid Dashboard Design

## Context

The current VM web UI is functional but visually utilitarian. We already have a Stitch-generated dashboard reference for the same product flow (`Brand -> Project -> Thread`) and need to implement that frontend direction without breaking the current event-driven behavior and API contracts.

Current UI/runtime anchors:
- `09-tools/web/vm/index.html`
- `09-tools/web/vm/app.js`
- `09-tools/web/vm/styles.css`

Stitch reference assets:
- `08-output/stitch/17545300329362275848/efc2a1c17c924fe7a0f20787bd536adf.html`
- `08-output/stitch/17545300329362275848/efc2a1c17c924fe7a0f20787bd536adf.png`

## Goal

Implement the Stitch-inspired frontend for VM Workspace while preserving existing JS logic and `/api/v2/*` behavior, starting with a complete three-column production-ready Phase 1.

## Approved Product/Scope Decisions

1. Implementation strategy: **Hybrid** (reuse existing app logic, apply Stitch visual/layout direction).
2. Delivery strategy: **Phased**.
3. Phase 1 completion bar: **Complete** (all current blocks functional inside new 3-column layout).
4. Styling base in Phase 1: **Tailwind via CDN + Material Icons via CDN**.
5. Recommended technical approach accepted: **Restructure HTML in-place while preserving existing DOM IDs used by `app.js`**.

## Architecture (Frontend)

Keep a static SPA structure served from `09-tools/web/vm/`, with `app.js` as the interaction/controller layer.

New shell layout:
1. Left Sidebar
- Brands list and create/edit actions
- Projects list and create/edit actions
- Lightweight profile/footer block

2. Center Workspace
- Top header (workflow context + CTA)
- Threads and modes controls
- Workflow input/profile preview/runs
- Timeline and run detail

3. Right Sidebar
- Tasks actions
- Approvals actions
- Artifacts list + preview

Non-negotiable compatibility rule:
- All IDs currently queried by `app.js` must remain present and unique (`brand-create-form`, `projects-list`, `thread-create-button`, `thread-modes-list`, `timeline-list`, `tasks-list`, `approvals-list`, `workflow-run-form`, `workflow-runs-list`, `workflow-run-detail-list`, `workflow-artifacts-list`, `workflow-artifact-preview`, etc.).

## Component Mapping

Left Sidebar (navigation/selection):
- `brand-create-form`, `brand-name-input`, `brands-list`
- `project-create-form`, `project-name-input`, `project-objective-input`, `project-channels-input`, `project-due-date-input`, `projects-list`

Center (primary workflow):
- `thread-title-input`, `thread-create-button`, `thread-mode-form`, `thread-mode-input`, `threads-list`, `thread-modes-list`, `mode-help`
- `workflow-run-form`, `workflow-request-input`, `workflow-mode-input`, `workflow-overrides-input`, `workflow-profile-preview-list`, `workflow-runs-list`, `workflow-run-detail-list`
- `timeline-list`

Right Sidebar (operations):
- `tasks-list`, `approvals-list`, `workflow-artifacts-list`, `workflow-artifact-preview`

## Data Flow and Runtime Behavior

No backend contract changes in this design:
- Keep all `/api/v2/*` calls unchanged.
- Keep idempotency headers unchanged.
- Keep state ownership in `app.js` (`activeBrandId`, `activeProjectId`, `activeThreadId`, `activeWorkflowRunId`, and in-memory list states).
- Keep polling lifecycle (`restartWorkflowPolling`) unchanged in semantics.

Required UI behavior guarantees:
1. Selection continuity across rerenders.
2. Action flows (`Grant`, `Resume`, `Complete`, mode edits/removals) keep triggering existing refresh chain.
3. Empty states still render safely.

## Error Handling and Resilience

1. Keep `fetchJson` as central request error boundary.
2. Maintain current functional fallback behavior (do not clear all state on transient failures).
3. Add minimal visible error surface in UI shell (non-blocking banner/toast in center area) to reduce reliance on alerts for key failures.
4. Preserve idempotent write behavior through `Idempotency-Key` on POST/PATCH.

## Responsive Rules

1. Desktop: fixed 3-column layout.
2. Tablet/mobile: stack columns into one flow (left -> center -> right).
3. No loss of functionality between breakpoints.

## Testing Strategy

Manual acceptance flow (Phase 1):
1. Create/edit/select brand.
2. Create/edit/select project.
3. Create/edit thread.
4. Add/remove thread modes.
5. Run workflow and inspect details.
6. Grant/resume approvals.
7. Comment/complete tasks.
8. Open artifact previews.

Automated validation:
1. Keep and expand `09-tools/tests/test_vm_webapp_ui_assets.py` checks for required IDs and key JS endpoint bindings.
2. Add assertions for new shell anchors/classes that identify three-column layout and mobile stacking hooks.

## Phase 1 Done Criteria

1. Three-column Stitch-inspired shell is implemented.
2. All existing interactive blocks remain operational.
3. No regression in polling/selection logic.
4. Tailwind CDN + Material Icons integrated in `index.html`.
5. Layout remains usable on desktop and mobile.

## Out of Scope (Phase 1)

1. Backend endpoint/schema changes.
2. Replatform to framework (React/Vue/etc.).
3. New workflow business rules.
4. Pixel-perfect parity for every visual token from Stitch; priority is high-fidelity hybrid with full functional continuity.
