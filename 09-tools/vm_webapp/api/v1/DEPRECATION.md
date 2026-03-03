# API Deprecation Strategy

## Overview

This document outlines the deprecation strategy for legacy API endpoints.

## Version History

- **v2.0.1** (2026-03-03): All missing routers registered
- **v2.0.2** (2026-03-05): Route consolidation and prefix standardization
- **v2.1.0** (2026-03-15): New v2 API structure introduced

## Deprecation Timeline

| Version | Action | Date |
|---------|--------|------|
| v2.1.0 | Mark legacy endpoints as deprecated | 2026-03-15 |
| v2.2.0 | Remove deprecated endpoints | 2026-06-15 (est.) |

## Legacy Endpoints (v1)

The following endpoints are considered legacy and will be deprecated:

- `/api/v1/*` - All v1 endpoints
- `/api/*` (without /v2/) - Legacy v2 endpoints in old structure

## Migration Guide

### From legacy to new structure:

| Legacy Endpoint | New Endpoint |
|----------------|--------------|
| `/api/brands` | `/api/v2/brands` |
| `/api/threads` | `/api/v2/threads` |
| `/api/projects` | `/api/v2/projects` |

## How to Mark Endpoints as Deprecated

Use FastAPI's deprecated parameter:

```python
@router.get("/legacy-endpoint", deprecated=True, 
            description="Use /api/v2/new-endpoint instead")
async def legacy_endpoint():
    ...
```

## Communication

- API consumers should migrate to new v2 endpoints
- Deprecated endpoints will return deprecation headers
- 6-month notice before removal
