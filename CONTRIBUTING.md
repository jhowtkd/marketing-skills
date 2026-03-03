# Contributing to Marketing Skills

Thank you for your interest in contributing to Marketing Skills! This document provides guidelines and instructions for setting up your development environment, running tests, and submitting pull requests.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Review Process](#review-process)
- [Deployment](#deployment)
- [Questions?](#questions)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to:

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Accept responsibility and apologize when mistakes happen

## Getting Started

### Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher
- **Git**: For version control
- **Node.js**: 18+ (for frontend development)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/jhowtkd/marketing-skills.git
cd marketing-skills

# Create and activate virtual environment
cd 09-tools/vm_webapp
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run database migrations
alembic upgrade head

# Start development server
python -m vm_webapp --port 8766 --reload
```

## Development Setup

### Environment Variables

Create a `.env` file in `09-tools/vm_webapp/`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/marketing_skills_dev

# API Keys (optional for basic development)
KIMI_API_KEY=your_api_key_here
KIMI_BASE_URL=https://api.kimi.com

# Application Settings
LOG_LEVEL=DEBUG
METRICS_ENABLED=true
WORKSPACE_ROOT=./workspace

# Testing
TEST_DATABASE_URL=postgresql://user:password@localhost/marketing_skills_test
```

### Database Setup

```bash
# Create development database
createdb marketing_skills_dev

# Create test database
createdb marketing_skills_test

# Run migrations
alembic upgrade head

# Seed with test data (optional)
python -m scripts.seed_data
```

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
marketing-skills/
├── 09-tools/
│   └── vm_webapp/              # Main Python application
│       ├── api/                # API routers
│       │   ├── v1/             # Legacy API
│       │   └── v2/             # Current API
│       │       ├── core/       # Core entities (brands, projects, threads)
│       │       ├── workflow/   # Workflow execution
│       │       ├── copilot/    # AI suggestions
│       │       ├── editorial/  # Editorial decisions
│       │       ├── optimizer/  # Queue management
│       │       └── insights/   # Health & metrics
│       ├── schemas/            # Pydantic models
│       ├── models.py           # SQLAlchemy models
│       ├── commands_v2.py      # Command handlers
│       ├── repo.py             # Repository pattern
│       ├── db.py               # Database utilities
│       ├── logging_config.py   # Structured logging
│       ├── middleware_metrics.py # Prometheus metrics
│       └── app.py              # FastAPI application factory
├── tests/                      # Test suite
│   ├── api/                    # API tests
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── docs/                       # Documentation
│   └── plans/                  # Implementation plans
└── web/                        # Frontend applications
    ├── vm-ui/                  # Main UI
    └── vm-studio/              # Studio UI
```

## Code Style Guidelines

### Python

We follow [PEP 8](https://pep8.org/) with these additions:

#### Imports

```python
# 1. Standard library imports
from __future__ import annotations
import json
from datetime import datetime
from typing import Any

# 2. Third-party imports
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

# 3. Local application imports
from vm_webapp.schemas.core import BrandCreate
from vm_webapp.db import session_scope
```

#### Type Hints

Use type hints everywhere:

```python
def process_brand(
    brand_id: str,
    data: BrandCreate,
    *,
    validate: bool = True,
) -> BrandResponse:
    ...
```

#### Docstrings

Use Google-style docstrings:

```python
async def create_brand(
    data: BrandCreate,
    request: Request,
) -> BrandResponse:
    """Create a new brand.
    
    Args:
        data: Brand creation data including name and description
        request: FastAPI request object for accessing app state
        
    Returns:
        The newly created brand with generated ID
        
    Raises:
        HTTPException: If brand creation fails
        ValueError: If validation fails
    """
    ...
```

#### Endpoint Documentation

All endpoints must include OpenAPI documentation:

```python
@router.post(
    "",
    response_model=BrandResponse,
    summary="Create a new brand",
    description="Creates a new brand with specified name and description.",
    responses={
        status.HTTP_201_CREATED: {"description": "Brand created"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid data"},
        status.HTTP_409_CONFLICT: {"description": "Duplicate brand"},
    },
    status_code=status.HTTP_201_CREATED,
)
```

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or fixing tests
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat(api): add campaign creation endpoint
fix(db): resolve connection pool exhaustion
docs(readme): update installation instructions
test(v2): add tests for brand router
```

## Testing

### Running Tests

```bash
# Run all tests
cd 09-tools
pytest

# Run specific test file
pytest tests/api/v2/test_brands.py

# Run with coverage
pytest --cov=vm_webapp --cov-report=html

# Run in watch mode
pytest -f

# Run only fast tests
pytest -m "not slow"
```

### Writing Tests

Test structure:

```python
import pytest

@pytest.fixture
def sample_brand(client):
    """Create a test brand."""
    response = client.post("/api/v2/brands", json={
        "name": "Test Brand",
    })
    return response.json()


def test_create_brand_success(client):
    """Test successful brand creation."""
    response = client.post("/api/v2/brands", json={
        "name": "Acme Corp",
        "description": "Test description",
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert data["brand_id"].startswith("brand-")


def test_create_brand_duplicate(client, sample_brand):
    """Test that duplicate brands are rejected."""
    response = client.post("/api/v2/brands", json={
        "name": sample_brand["name"],
    })
    
    assert response.status_code == 409
```

### Test Categories

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test API endpoints with database
- **E2E tests**: Test complete workflows

## Pull Request Process

### Before Creating a PR

1. **Sync with main**:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-branch
   git rebase main
   ```

2. **Run tests**:
   ```bash
   pytest
   ```

3. **Check code style**:
   ```bash
   ruff check .
   ruff format --check .
   mypy vm_webapp/
   ```

4. **Update documentation** if needed

### Creating a PR

1. **Push your branch**:
   ```bash
   git push origin your-branch
   ```

2. **Create PR on GitHub**:
   - Use a clear title following conventional commits
   - Fill out the PR template
   - Link related issues

3. **PR Template**:
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update

   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests pass
   - [ ] Manual testing performed

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] No new warnings
   ```

### PR Requirements

- All CI checks must pass
- Code review approval required
- Tests must cover new code
- Documentation must be updated

## Review Process

### As a Reviewer

- Be constructive and respectful
- Focus on the code, not the person
- Suggest improvements, don't just point out problems
- Approve when ready, don't delay unnecessarily

### Review Checklist

- [ ] Code is readable and well-documented
- [ ] Tests cover the changes
- [ ] No security vulnerabilities introduced
- [ ] Performance implications considered
- [ ] Error handling is appropriate
- [ ] Logging is adequate

### Responding to Reviews

```python
# If you disagree, explain why:
"I chose this approach because [reason]. Happy to discuss alternatives."

# If you make changes:
"Fixed in commit abc123 - changed X to Y as suggested"

# If you need clarification:
"Could you clarify what you mean by [comment]? I'm not sure I understand."
```

## Deployment

### Staging Deployment

```bash
# Merge to staging branch
git checkout staging
git merge your-branch
git push origin staging

# Deploy to staging environment
./scripts/deploy-staging.sh
```

### Production Deployment

Production deployments are handled by the CI/CD pipeline after:
- All tests pass
- Security scan passes
- Approval from 2 maintainers

## Questions?

- **Slack**: #dev-marketing-skills
- **Email**: dev@marketing-skills.com
- **Issues**: Create a GitHub issue for bugs or feature requests

---

## Appendix

### Useful Commands

```bash
# Database
psql $DATABASE_URL                    # Connect to database
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                   # Run migrations
alembic downgrade -1                   # Rollback one migration

# Testing
pytest --tb=short                      # Short traceback
pytest -x                              # Stop on first failure
pytest --lf                            # Run last failures
pytest -k "test_brand"                 # Run tests matching pattern

# Code Quality
ruff check .                           # Lint code
ruff check --fix .                     # Fix auto-fixable issues
ruff format .                          # Format code
mypy vm_webapp/                        # Type check

# API
python -m vm_webapp --help             # CLI help
curl http://localhost:8766/api/v2/health/ready  # Health check
```

### Project Conventions

| Aspect | Convention |
|--------|------------|
| Line length | 100 characters |
| Quotes | Double quotes for strings |
| Imports | Sorted: stdlib, third-party, local |
| Types | Required on all function signatures |
| Tests | One assertion per test preferred |
| Commits | Conventional commits format |
| Branches | `feat/description`, `fix/description` |

---

Thank you for contributing! 🚀
