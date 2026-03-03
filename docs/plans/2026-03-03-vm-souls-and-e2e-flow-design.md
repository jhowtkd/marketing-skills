# VM Souls + E2E Flow Design

**Date:** 2026-03-03  
**Status:** Approved in brainstorming

## 1. Context and goals

Current pain points:
- UI quality is below expected level (responsiveness and visual identity).
- Frontend/backend integration is inconsistent for core operations.
- The "soul" concept per hierarchy level is missing in productized flow.

Delivery priorities validated with user:
1. First: implement soul documents per level.
2. Second: guarantee end-to-end operational flow (`brand -> project -> thread -> run -> artifact`).

## 2. Decisions validated

- Hierarchy for soul docs: `brand + project + thread`.
- Authoring model: fixed templates with fixed sections.
- Storage strategy: versioned files in repository (not runtime-only).
- Template strategy: different templates for each level.
- Folder convention:
  - `09-tools/data/souls/brands/<brand_id>/brand.md`
  - `09-tools/data/souls/brands/<brand_id>/projects/<project_id>/project.md`
  - `09-tools/data/souls/brands/<brand_id>/projects/<project_id>/threads/<thread_id>/thread.md`

## 3. Approaches considered

### Option A: quick patch on current legacy overlap

- Keep current mixed route/front structure and add soul files with minimal changes.
- Pros: fastest initial patch.
- Cons: preserves API overlap and increases future break risk.

### Option B: full migration first, then features

- Unify all v2 routes and fully restructure frontend before adding souls.
- Pros: cleaner architecture before feature work.
- Cons: high lead time and high short-term risk.

### Option C (selected): phased hybrid

- Phase A: ship soul domain + editor + versioned persistence.
- Phase B: close E2E operational flow and UX quality gaps without full rewrite.
- Pros: immediate value, controlled risk, clear iteration path.
- Cons: requires strict scope control per phase.

## 4. Target architecture

- Single official frontend for operations: `09-tools/web/vm-ui`.
- Operational entities remain event/read-model based (brand/project/thread/runs).
- New explicit Soul domain:
  - level-specific template provider,
  - markdown parser/validator by section,
  - filesystem store backed by versioned repo paths,
  - context composer for run-time prompt injection.

## 5. Backend components

Create modules:
- `09-tools/vm_webapp/soul_templates.py`
  - fixed templates for `brand`, `project`, `thread`.
- `09-tools/vm_webapp/soul_parser.py`
  - parse markdown sections, enforce required headers.
- `09-tools/vm_webapp/soul_store.py`
  - path resolution + read/write + bootstrap default template if missing.
- `09-tools/vm_webapp/soul_context.py`
  - combine brand/project/thread soul content for workflow context.

## 6. API contracts (v2)

Add endpoints:
- `GET /api/v2/brands/{brand_id}/soul`
- `PUT /api/v2/brands/{brand_id}/soul`
- `GET /api/v2/projects/{project_id}/soul`
- `PUT /api/v2/projects/{project_id}/soul`
- `GET /api/v2/threads/{thread_id}/soul`
- `PUT /api/v2/threads/{thread_id}/soul`

Response payload shape (uniform):
- `markdown`: full markdown content.
- `sections`: parsed section map for structured editing.
- `version_hash`: optimistic concurrency token.
- `updated_at`: server timestamp.
- `recovered` (optional): true when backend auto-regenerated a minimal template.

## 7. Frontend components (vm-ui)

- Add "Soul" panel in context rail for selected brand/project/thread.
- Form editor based on fixed sections (per level template).
- Actions:
  - Save (`PUT` with `version_hash`).
  - Restore template.
- Status indicators:
  - `Template default` vs `Personalized`.
- Conflict flow:
  - show non-blocking warning on `409` and offer refresh.

## 8. Data flow

1. User selects `brand -> project -> thread`.
2. Front requests soul content for each level via `GET`.
3. If missing, backend bootstraps with level template and returns structured payload.
4. User edits/saves via `PUT`.
5. Backend validates required sections and persists markdown in `09-tools/data/souls/...`.
6. On workflow run start, backend loads all 3 soul documents and composes run context.
7. Run snapshots include soul references (`hash` and source paths) for audit.
8. Artifacts are rendered in workspace canvas as usual.

## 9. Error handling and validation

- `400`: missing required sections / invalid markdown template contract.
- `404`: invalid brand/project/thread id.
- `409`: `version_hash` mismatch (concurrent edit).
- Missing/corrupt files:
  - backend rebuilds default template,
  - returns `recovered=true`,
  - does not block user editing.
- Run with no prior custom soul:
  - allowed, using default template content.

## 10. Testing strategy

Backend:
- Unit tests for template generation, parser, and store.
- API tests for `GET/PUT` across all 3 levels.
- Integration test ensuring run context includes all three souls.

Frontend:
- Soul panel render and responsive behavior.
- Save success/error/conflict (`409`) flows.
- Integration test for operational flow:
  - create brand/project/thread,
  - edit souls,
  - start run,
  - inspect generated artifact preview.

## 11. Acceptance criteria

- User can create/select brand, project, and thread from UI.
- User can edit and persist `brand.md`, `project.md`, and `thread.md`.
- Workflow run consumes soul context from all levels.
- Artifact output is available in UI and auditable against selected soul docs.
- Core layout remains usable on desktop and mobile widths.

## 12. Delivery plan (high level)

Phase A (priority 1 in this design): soul domain + UI editor + file persistence.  
Phase B (priority 2 in this design): complete E2E run flow and UX hardening for responsiveness/personality.
