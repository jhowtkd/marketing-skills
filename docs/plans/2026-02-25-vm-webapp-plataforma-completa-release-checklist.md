# Release Checklist: VM Webapp Plataforma Completa

## 1) Core Domain (Wave 1/2)
- [x] Brand/Campaign/Task hierarchy in models and projectors.
- [x] Context versions and hierarchical resolver with override policy.
- [x] v2 API endpoints for all domain entities.
- [x] Idempotency headers enforced in all mutation endpoints.

## 2) Tooling & Runtime (Wave 1/2)
- [x] Tool Registry and contracts.
- [x] Governance (permissions, rate-limit, credentials).
- [x] Runtime integration with Tool Executor and audit trail.
- [x] Resilience policies (Retry, Fallback, Circuit Breaker).

## 3) RAG & Learning (Wave 1/2)
- [x] Chunker, Indexer and Retriever modules.
- [x] Brand-aware and campaign-boosted retrieval.
- [x] Automatic ingestion of artifacts after run completion.

## 4) Verification & QA
- [x] All 107+ unit/integration tests passing.
- [x] E2E flow: Brand -> Campaign -> Task -> Run -> Review -> Learning.
- [x] No regressions in legacy event-driven flows.
- [x] README and ARCHITECTURE documentation updated.

## 5) Deployment & Operation
- [ ] Database migrations reviewed (if applicable).
- [ ] Secret refs (env vars) configured for Tooling.
- [ ] Redis/Persistence check for parallel workers.

**Release Status:** Ready for final merge and deployment.
