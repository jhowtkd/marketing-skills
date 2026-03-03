from fastapi import APIRouter

# Core
from .core import brands_router

v2_router = APIRouter(prefix="/api/v2")

# Core
v2_router.include_router(brands_router)

__all__ = ["v2_router"]
