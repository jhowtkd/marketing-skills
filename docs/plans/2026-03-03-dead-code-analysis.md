# Dead Code Analysis Report

**Date:** 2026-03-03

**Task:** Task 4.1 - Identify endpoints that exist in backend but are not used by frontend

## Summary

- Total backend endpoints: 192
- Total frontend endpoints: 191
- Potentially unused endpoints: 48
- Used endpoints: 144

> **Note:** These are candidates for deprecation. Manual verification is required before removal.

## Top 20 Candidates for Deprecation

1. `/brands`
2. `/chat`
3. `/events`
4. `/freeze`
5. `/health`
6. `/metrics`
7. `/products`
8. `/proposals`
9. `/proposals/{proposal_id}/apply`
10. `/proposals/{proposal_id}/reject`
11. `/rollback`
12. `/run`
13. `/runs`
14. `/runs/foundation`
15. `/runs/{run_id}/approve`
16. `/runs/{run_id}/events`
17. `/state`
18. `/status`
19. `/templates`
20. `/templates/recommended`

## All Potentially Unused Endpoints

```
/brands
/chat
/events
/freeze
/health
/metrics
/products
/proposals
/proposals/{proposal_id}/apply
/proposals/{proposal_id}/reject
/rollback
/run
/runs
/runs/foundation
/runs/{run_id}/approve
/runs/{run_id}/events
/state
/status
/templates
/templates/recommended
/templates/{template_id}
/threads
/threads/{thread_id}/close
/threads/{thread_id}/messages
/v2/escalation/approvals
/v2/escalation/metrics
/v2/escalation/profiles/{approver_id}
/v2/escalation/timeouts
/v2/escalation/windows
/v2/optimizer/proposals/{proposal_id}
/v2/optimizer/proposals/{proposal_id}/apply
/v2/optimizer/proposals/{proposal_id}/freeze
/v2/optimizer/proposals/{proposal_id}/reject
/v2/optimizer/proposals/{proposal_id}/rollback
/v2/optimizer/proposals/{proposal_id}/snapshot
/v2/optimizer/run
/v2/optimizer/runs/{run_id}/proposals
/v2/optimizer/status
/v2/safety-tuning/audit
/v2/safety-tuning/gates/{gate_name}/freeze
/v2/safety-tuning/gates/{gate_name}/unfreeze
/v2/safety-tuning/run
/v2/safety-tuning/status
/v2/safety-tuning/{proposal_id}/apply
/v2/safety-tuning/{proposal_id}/revert
/v2/threads/{thread_id}/copilot/feedback
/v2/threads/{thread_id}/copilot/segment-status
/v2/threads/{thread_id}/copilot/suggestions
```
