# VM Web App - Workflow Approval Orchestration (Design)

Date: 2026-02-25  
Status: Approved  
Branch: `feature/llm-foundation-workflow`

## Context

The current workflow gate flow requires two separate actions in many UI paths:
1. `POST /api/v2/approvals/{approval_id}/grant`
2. `POST /api/v2/workflow-runs/{run_id}/resume`

This creates UX friction and state inconsistencies when users cannot clearly find where to grant approval, or when approval and resume are executed out of sync.

## Goal

Deliver a single, backend-orchestrated approval action that:
1. Grants approval.
2. Resumes the run when applicable (`waiting_approval`).
3. Provides explicit response metadata to drive UI state without fragile client inference.

## Scope Decisions (Approved)

1. Show all pending approvals in a fixed top panel in the thread workspace.
2. Keep strong run-level highlight when a run is `waiting_approval`.
3. Auto-open run detail focused on waiting approvals.
4. Remove old two-step write endpoints and migrate to a single endpoint.

## Backend Design

### New endpoint (single action)

`POST /api/v2/approvals/{approval_id}/grant-and-resume`

- Requires `Idempotency-Key`.
- No request body required.
- Command is orchestrated server-side.

### Command behavior

1. Resolve `approval_id` from `approvals_view`.
2. Parse `run_id` and `stage_key` from `reason` format: `workflow_gate:{run_id}:{stage_key}`.
3. If approval is pending, append `ApprovalGranted`.
4. If run status is `waiting_approval`, append `WorkflowRunResumed` in the same command path.
5. If run is already `running`, `queued`, or terminal, keep run status and return `resume_applied=false`.
6. Persist a single dedup response for the command key with all effect metadata.

### Response contract

```json
{
  "approval_id": "apr-...",
  "run_id": "run-...",
  "approval_status": "granted",
  "run_status": "running",
  "resume_applied": true,
  "event_ids": ["evt-...", "evt-..."]
}
```

Notes:
- `approval_status` can be `granted` or `already_granted`.
- `run_status` reflects effective status after command application.

### Migration (breaking by design)

Remove:
- `POST /api/v2/approvals/{approval_id}/grant`
- `POST /api/v2/workflow-runs/{run_id}/resume`

All clients must use `grant-and-resume`.

## Frontend Design

### A. Fixed pending-approvals panel

In thread workspace, render a dedicated top section:
- Title: `Aprovações pendentes`.
- List every pending approval item.
- Each row shows: `stage_key`, `run_id`, `status`, and one `Grant` button.
- Button calls only `grant-and-resume`.

### B. Run card highlight

When run status is `waiting_approval`:
- Add high-contrast badge and blocking message.
- Provide one `Grant` CTA linked to current pending approval(s).
- Do not show `Resume` anywhere.

### C. Auto-focus run detail

When any run is `waiting_approval`:
- Auto-select this run in run list.
- Keep pending approvals visible in run detail.
- Every approval action is a single `Grant` call.

### D. Post-action refresh

After any grant action:
1. Refresh approvals list.
2. Refresh run list/detail.
3. Refresh timeline/tasks as needed.
4. Show concise feedback message with `resume_applied` state.

## Error Handling

1. `404`: approval not found.
2. `409`: approval is not a valid workflow gate link to a run.
3. `200` idempotent replay with stored response when command key repeats.
4. `200` with `resume_applied=false` when run is not `waiting_approval`.

## Testing Plan

### Backend

1. Happy path: pending approval + waiting run emits both events.
2. Idempotency replay returns same response.
3. Already granted approval returns `already_granted`.
4. Run not waiting returns `resume_applied=false`.
5. Invalid `reason` format returns `409`.

### API

1. Endpoint contract and status codes for `grant-and-resume`.
2. Legacy endpoints removed from router.
3. Thread/workflow read endpoints still expose pending approvals correctly.

### UI

1. Fixed panel renders all pending approvals.
2. No `Resume` button remains in assets.
3. Single `Grant` action wired in panel, run card, and run detail.
4. Waiting run auto-focus behavior.

## Risks and Mitigations

1. Breaking existing external clients.
Mitigation: document breaking change in README and PR notes.

2. Approval-to-run mapping relies on `reason` convention.
Mitigation: strict parser with explicit `409` and tests.

3. Duplicate click race scenarios.
Mitigation: idempotency key enforcement and command dedup persistence.

## Done Criteria

1. Users can approve and continue workflow with one click.
2. UI always surfaces pending approvals in a visible fixed panel.
3. Backend contract exposes deterministic action outcome.
4. Legacy two-step write flow is fully removed.
