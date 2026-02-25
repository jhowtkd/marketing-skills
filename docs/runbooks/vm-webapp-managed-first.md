# VM Webapp Managed-First Runbook

## Goal

Operate VM Webapp in managed-first mode with a split API + worker topology, isolated stateful dependencies, and explicit health checks.

## Deployment Contract

- Render blueprint: `deploy/render/vm-webapp-render.yaml`
- API process: `uv run python -m vm_webapp serve --host 0.0.0.0 --port $PORT`
- Worker process: `uv run python -m vm_webapp worker --poll-interval-ms 500`
- Managed-first guard: `VM_ENABLE_MANAGED_MODE=true`
- Required dependencies:
  - `VM_DB_URL` (PostgreSQL)
  - `VM_REDIS_URL` (Redis)

## Environment Variables

Set the following values for both web and worker services:

- `APP_ENV=production`
- `VM_ENABLE_MANAGED_MODE=true`
- `VM_DB_URL=<postgres connection string>`
- `VM_REDIS_URL=<redis connection string>`
- `VM_WORKSPACE_ROOT=/var/data/vm`
- `KIMI_MODEL=kimi-for-coding`
- `KIMI_BASE_URL=https://api.kimi.com/coding/v1`
- `KIMI_API_KEY=<secret>`

## Startup Validation

Managed mode performs fail-fast checks during app startup:

- If `VM_ENABLE_MANAGED_MODE=true` and `VM_DB_URL` is missing, startup fails.
- If `VM_ENABLE_MANAGED_MODE=true` and `VM_REDIS_URL` is missing, startup fails.

## Health Checks

Use the service base URL for probes:

- Liveness: `GET /api/v2/health/live` -> expects `{"status":"live"}`
- Readiness: `GET /api/v2/health/ready` -> expects `status=ready` and dependencies `database.status=ok`, `worker.status=ok`
- Dependency check in CI/CD: fail rollout if readiness reports `not_ready`

## Smoke Procedure (Post-Deploy)

1. Verify web service is responding:
   - `curl -sS "$BASE_URL/api/v2/health/live"`
2. Verify dependency readiness:
   - `curl -sS "$BASE_URL/api/v2/health/ready"`
3. Create a test run from UI or API and confirm worker drains queued events.

## Incident Response

### Symptoms

- Readiness returns `not_ready`
- Runs remain in `queued` state with no progress
- Worker process repeatedly restarting

### Checks

1. Confirm API and worker share the same `VM_DB_URL`.
2. Confirm `VM_REDIS_URL` is configured and reachable.
3. Inspect worker logs for polling loop errors.
4. Validate latest migration/DDL compatibility with current code.

## Rollback

1. Roll back both `vm-webapp-api` and `vm-webapp-worker` to the last healthy deploy.
2. Re-run probes:
   - `GET /api/v2/health/live`
   - `GET /api/v2/health/ready`
3. Confirm event processing resumed and queued workload is draining.
4. If DB schema drift caused the issue, apply rollback migration before resuming deploys.
