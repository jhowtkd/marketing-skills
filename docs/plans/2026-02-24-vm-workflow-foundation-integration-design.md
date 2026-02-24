# VM Workspace v2 -> Foundation Integration Design

Date: 2026-02-24  
Status: Approved  
Branch: `codex/vm-webapp-async-workflow-pr`

## Context

The current v2 workspace flow (`Brand -> Project -> Thread -> Workflow Run`) is operational and the main v2 test suite is green, but workflow execution is still simplified in runtime v2.  
The run lifecycle, timeline, and artifacts exist, yet stage execution is not wired to the real Foundation executor stack used by Vibe Marketing agents.

This design turns v2 runs into real asynchronous Foundation-backed execution with traceability, approvals, and mode fallback.

## Decisions Confirmed

1. Integrate first with the existing Foundation executor.
2. Use service-layer integration approach (keep runtime v2 thin; add dedicated bridge service).
3. Make `plan_90d` run through real Foundation pipeline.
4. Enable automatic fallback: any mode can execute through Foundation for now.
5. Approval gate UX: granting approval auto-advances execution.

## Goals

1. Keep API write path fast (`POST` enqueues, worker executes in background).
2. Preserve run-centric history and artifacts without overwriting past runs.
3. Connect v2 runtime to real Foundation execution.
4. Keep per-run override flexibility while preserving global profile integrity.
5. Provide consistent run states and events for UI and operations.

## Non-Goals

1. No DB engine swap in this cycle (stay on SQLite).
2. No auth/RBAC in this cycle.
3. No dedicated external worker service yet (same-process worker MVP).

## Architecture

### 1) Runtime and Service Boundaries

- `WorkflowRuntimeV2` becomes a coordinator only:
  - queue/pick pending runs
  - state transitions and event emission
  - approval pause/resume orchestration
- New `FoundationRunnerService` executes real stages through existing Foundation executor internals.
- New `FoundationStateMapper` maps Foundation/internal statuses and failures into canonical v2 run/stage states.

This preserves clean separation: API and runtime do not embed Foundation execution details.

### 2) Mode/Profile/Override Contract

Run creation accepts:
- `requested_mode`
- optional per-run `override`

Resolved execution fields persisted immutably in run snapshot:
- `requested_mode`
- `effective_mode`
- `profile_version`
- `resolved_stages`

Resolution rule:
- If profile exists for requested mode, use it.
- If profile does not exist, fallback to Foundation default profile (global rule for this cycle).

Important:
- `override` is per run only and auditable.
- Global YAML profiles are never mutated by per-run override.

### 3) Asynchronous Lifecycle

Canonical run statuses:
- `queued`
- `running`
- `waiting_approval`
- `completed`
- `failed`
- `canceled`

Flow:
1. `POST /api/v2/threads/{thread_id}/workflow-runs` creates run in `queued`, stores resolved snapshot, emits `WorkflowRunQueued`, and returns quickly.
2. Same-process worker picks queued run, marks `running`, emits `WorkflowRunStarted`.
3. For each stage:
   - emit `WorkflowRunStageStarted`
   - execute via `FoundationRunnerService`
   - persist stage artifacts (`input.json`, `output.json`, `manifest.json`, `artifacts/*`)
   - emit completion/failure events
4. If stage requires approval:
   - move run to `waiting_approval`
   - emit `WorkflowRunWaitingApproval`
   - create linked `Approval` + operational `Task`
5. On `ApprovalGranted`, resume automatically and emit `WorkflowRunResumed`.
   - `POST /workflow-runs/{run_id}/resume` remains idempotent fallback control.
6. Finish with:
   - `WorkflowRunCompleted` on success
   - `WorkflowRunFailed` on terminal failure

### 4) Foundation Integration

`FoundationRunnerService` responsibilities:
- translate v2 stage context into Foundation executor inputs
- invoke executor and capture outputs
- normalize stage result into v2 contract (`stage_output`, `artifacts`, `metrics`, `error`)

`FoundationStateMapper` responsibilities:
- map internal/Foundation states into v2 canonical states
- map failure metadata:
  - `error_code`
  - `error_message`
  - `retryable`

Observability requirements:
- structured logs with `run_id`, `stage_id`, `thread_id`
- event correlation fields (for example `event_id`, `causation_id`) for timeline traceability

## API Surface

### `POST /api/v2/threads/{thread_id}/workflow-runs`

Behavior:
- resolve mode/profile/override snapshot
- enqueue run only

Response shape:
- `run_id`
- `status: "queued"`
- `requested_mode`
- `effective_mode`

### `GET /api/v2/workflow-runs/{run_id}`

Returns:
- run status
- per-stage status/history
- approvals pending
- errors and metadata
- timestamps
- artifacts references

### `POST /api/v2/workflow-runs/{run_id}/resume`

Behavior:
- idempotent resume trigger
- if already resumed/completed/failed, returns current state without error

### `GET /api/v2/workflow-profiles`

Returns:
- available profiles and versions
- mode contracts
- fallback indicator

## UI Impact

Run form:
- choose `mode`
- preview resolved stages/skills
- optional override field per run

Run list:
- live run status
- stage-by-stage progress
- explicit `waiting_approval` signal

Timeline and artifacts:
- display canonical run events
- quick-open stage outputs (`manifest.json`, `output.json`, markdown artifacts)

## Testing Strategy

### Unit

1. YAML profile parsing and validation.
2. Stage planning with and without override.
3. Run state transition rules.
4. Foundation state/error mapping to v2 contract.

### Integration

1. enqueue -> async processing -> completion path.
2. approval-required stage pauses and resumes only after `ApprovalGranted`.
3. idempotent resume endpoint behavior.
4. atomic stage artifact persistence.
5. fallback mode resolution to Foundation profile.

### E2E

1. user creates run with mode and override, monitors progress, gets artifacts.
2. re-run in same thread creates a new `run_id` and preserves history.
3. mid-pipeline failure preserves completed stage timeline/artifacts.

### Regression

Keep existing suites green:
- `api_v2`
- `event_driven_e2e`
- `workflow_runtime_v2`
- `ui_assets`

## Rollout Plan

1. Phase 1: enable Foundation real path for `plan_90d` behind flag.
2. Phase 2: activate automatic Foundation fallback for all modes without native profile.
3. Phase 3: remove simplified/legacy execution path after stability window.

## Risks and Mitigations

1. Risk: state mismatch between Foundation internals and v2 statuses.  
Mitigation: centralize mapping in `FoundationStateMapper` with unit coverage.

2. Risk: duplicate resume actions.  
Mitigation: idempotent resume semantics and transition guards.

3. Risk: artifact inconsistencies on failure.  
Mitigation: stage-level atomic write protocol and explicit failure manifests.

## Implementation Handoff

Next step after this approved design:
- create a detailed implementation plan via writing-plans skill, then execute in small verified increments.
