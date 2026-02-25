# VM Webapp Managed-First Hardening Release Checklist

- [ ] DB migration plan reviewed and rollback steps documented.
- [ ] Production secrets validated (`VM_DB_URL`, `VM_REDIS_URL`, API keys).
- [ ] Worker liveness verified in staging with managed queue dependencies.
- [ ] Readiness and liveness probes validated (`/api/v2/health/ready`, `/api/v2/health/live`).
- [ ] Prometheus scraping validated for `/api/v2/metrics/prometheus`.
- [ ] Structured logging checked for `request_id` and `correlation_id` propagation.
