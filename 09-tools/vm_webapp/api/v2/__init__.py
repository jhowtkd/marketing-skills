from fastapi import APIRouter

# Copilot
from .copilot import copilot_router

# Core
from .core import (
    brands_router,
    campaigns_router,
    projects_router,
    threads_router,
)

# Editorial
from .editorial import editorial_decisions_router

# Insights
from .insights import health_router

# Optimizer
from .optimizer import optimizer_router

# Workflow
from .workflow import workflow_runs_router

v2_router = APIRouter(prefix="/api/v2")

# Copilot
v2_router.include_router(copilot_router)

# Core
v2_router.include_router(brands_router)
v2_router.include_router(campaigns_router)
v2_router.include_router(projects_router)
v2_router.include_router(threads_router)

# Editorial
v2_router.include_router(editorial_decisions_router)

# Insights
v2_router.include_router(health_router)

# Optimizer
v2_router.include_router(optimizer_router)

# Workflow
v2_router.include_router(workflow_runs_router)

__all__ = ["v2_router"]
