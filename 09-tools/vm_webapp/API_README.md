# Marketing Skills API - Technical Documentation

> **Version:** 2.0.0  
> **Last Updated:** 2026-03-04  
> **Maintainer:** DevOps Team

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Structure](#api-structure)
- [Adding New Endpoints](#adding-new-endpoints)
- [Naming Conventions](#naming-conventions)
- [Examples](#examples)
- [Request Flow](#request-flow)
- [Observability](#observability)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Marketing Skills API is a FastAPI-based RESTful service that powers marketing workflow automation, brand management, and AI-assisted content creation. The API follows an event-sourced architecture with CQRS (Command Query Responsibility Segregation) patterns.

### Key Features

- **Brand & Project Management**: Organize marketing activities hierarchically
- **Workflow Orchestration**: Execute complex multi-stage workflows
- **AI Copilot**: Context-aware suggestions and optimizations
- **Editorial Controls**: Quality gates and approval workflows
- **Real-time Metrics**: Prometheus-compatible observability

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│              (Web UI, CLI, External Services)               │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │   Routers   │ │  Middleware  │ │  Request Validation │  │
│  └─────────────┘ └──────────────┘ └─────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Service Layer                             │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │  Commands   │ │   Queries    │ │   Event Handlers    │  │
│  └─────────────┘ └──────────────┘ └─────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Data Layer                                │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │ PostgreSQL  │ │ Event Store  │ │   Read Models       │  │
│  │  (Primary)  │ │   (Events)   │ │   (Projections)     │  │
│  └─────────────┘ └──────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Event Sourcing**: All state changes are captured as immutable events
2. **CQRS**: Separate read and write models for performance
3. **Idempotency**: All mutation endpoints support idempotency keys
4. **Consistency**: Strong consistency for writes, eventual consistency for reads

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)

### Local Development

```bash
# Install dependencies
cd 09-tools/vm_webapp
pip install -e .

# Set up database
export DATABASE_URL="postgresql://user:pass@localhost/marketing_skills"

# Run migrations
alembic upgrade head

# Start development server
python -m vm_webapp --port 8766 --reload
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) | INFO |
| `METRICS_ENABLED` | Enable Prometheus metrics | true |
| `REQUEST_TIMEOUT` | Request timeout in seconds | 30 |

---

## API Structure

### Versioning

The API uses URL-based versioning:
- `/api/v1/*` - Legacy endpoints (deprecated)
- `/api/v2/*` - Current stable endpoints

### Base URL

```
Development: http://localhost:8766
Production:  https://api.marketing-skills.com
```

### Endpoint Organization

```
/api/v2/
├── brands              # Brand management
├── projects            # Project management
├── campaigns           # Campaign management
├── threads             # Conversation contexts
├── workflow/
│   └── runs            # Workflow execution
├── copilot/
│   └── suggestions     # AI-powered suggestions
├── editorial/
│   └── decisions       # Editorial decisions
├── optimizer           # Optimization queue
└── insights/
    ├── health          # Health checks
    └── metrics         # Prometheus metrics
```

---

## Adding New Endpoints

### 1. Define Schema

Create or update schema in `schemas/`:

```python
# schemas/custom.py
from pydantic import BaseModel

class MyRequest(BaseModel):
    name: str
    description: str | None = None

class MyResponse(BaseModel):
    id: str
    name: str
    status: str
```

### 2. Create Router

Create router in appropriate module:

```python
# api/v2/custom/module.py
from fastapi import APIRouter, Request, status
from vm_webapp.schemas.custom import MyRequest, MyResponse

router = APIRouter(prefix="/custom", tags=["custom"])

@router.post(
    "",
    response_model=MyResponse,
    summary="Create custom resource",
    description="Detailed description of what this does.",
    status_code=status.HTTP_201_CREATED,
)
async def create_custom(
    data: MyRequest,
    request: Request,
) -> MyResponse:
    """Create a new custom resource.
    
    Args:
        data: Creation parameters
        
    Returns:
        The created resource
    """
    # Implementation
    pass
```

### 3. Register Router

Add to `api/v2/__init__.py`:

```python
from .custom import custom_router

v2_router.include_router(custom_router)
```

### 4. Add Tests

Create tests in `tests/api/v2/test_custom.py`:

```python
def test_create_custom(client):
    response = client.post("/api/v2/custom", json={
        "name": "Test",
        "description": "Test description"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

---

## Naming Conventions

### Endpoints

| Pattern | Example | Usage |
|---------|---------|-------|
| `GET /resources` | `GET /brands` | List all (with filters) |
| `GET /resources/{id}` | `GET /brands/{brand_id}` | Get single |
| `POST /resources` | `POST /brands` | Create new |
| `PATCH /resources/{id}` | `PATCH /brands/{brand_id}` | Partial update |
| `DELETE /resources/{id}` | `DELETE /brands/{brand_id}` | Delete |
| `POST /resources/{id}/actions` | `POST /runs/{id}/resume` | Custom actions |

### Parameters

- **Path**: Use `{resource}_{id}` format (e.g., `{brand_id}`, `{thread_id}`)
- **Query**: Use snake_case (e.g., `?brand_id=xxx&include_archived=true`)
- **Body**: Use snake_case in JSON

### Response Fields

```python
{
    "id": "brand-abc123",           # Resource ID with prefix
    "created_at": "2026-03-04T...", # ISO 8601 timestamp
    "status": "active",              # Enum as lowercase string
    "metadata": {...}                # Optional additional data
}
```

---

## Examples

### Creating a Brand

```bash
curl -X POST http://localhost:8766/api/v2/brands \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-key-123" \
  -d '{
    "name": "Acme Corporation",
    "description": "Leading widget manufacturer"
  }'
```

Response:
```json
{
  "brand_id": "brand-a1b2c3d4e5",
  "name": "Acme Corporation",
  "description": "Leading widget manufacturer",
  "status": "active",
  "created_at": "2026-03-04T10:30:00Z",
  "updated_at": null
}
```

### Starting a Workflow

```bash
curl -X POST http://localhost:8766/api/v2/workflow/runs \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread-xxx",
    "profile_mode": "standard",
    "input_payload": {
      "request_text": "Create social media campaign"
    }
  }'
```

### Getting Health Status

```bash
curl http://localhost:8766/api/v2/health/ready
```

Response:
```json
{
  "status": "ready",
  "checks": {
    "database": {"status": "ok"},
    "memory": {"status": "ok", "usage_percent": 45},
    "disk": {"status": "ok", "free_gb": 120}
  }
}
```

---

## Request Flow

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Request   │────▶│  Middleware  │────▶│    Router     │
│   Enters    │     │              │     │               │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                       ┌─────────────────────────┘
                       ▼
              ┌─────────────────┐
              │  Extract IDs    │
              │  Validate Auth  │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   Command/Query │
              │   Execution     │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Event Store    │
              │  (Write)        │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Read Model     │
              │  Projection     │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   Response      │
              │   Serialization │
              └─────────────────┘
```

---

## Observability

### Metrics

Prometheus metrics available at `/api/v2/metrics/prometheus`:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `http_request_size_bytes` | Histogram | Request body size |
| `http_response_size_bytes` | Histogram | Response body size |
| `active_connections` | Gauge | Current active connections |

### Logging

Structured JSON logging with request tracking:

```json
{
  "timestamp": "2026-03-04T10:00:00Z",
  "level": "INFO",
  "request_id": "req-abc123",
  "correlation_id": "corr-xyz789",
  "method": "POST",
  "path": "/api/v2/brands",
  "status_code": 201,
  "duration_ms": 45,
  "user_agent": "Mozilla/5.0..."
}
```

### Health Checks

- `/api/v2/health/live` - Liveness probe
- `/api/v2/health/ready` - Readiness probe with dependency checks

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 409 Conflict | Idempotency key reuse | Use unique idempotency keys |
| 404 Not Found | Resource doesn't exist | Verify IDs are correct |
| 500 Error | Database connection | Check DATABASE_URL and connectivity |
| Slow responses | Missing indexes | Check query performance |

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m vm_webapp
```

### Database Inspection

```bash
# Connect to database
psql $DATABASE_URL

# Check recent events
SELECT * FROM event_log ORDER BY occurred_at DESC LIMIT 10;

# Check read models
SELECT * FROM brand_view LIMIT 10;
```

---

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for:
- Setting up development environment
- Running tests
- Code style guidelines
- PR process

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Models](https://docs.pydantic.dev/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Prometheus Metrics](https://prometheus.io/docs/)
