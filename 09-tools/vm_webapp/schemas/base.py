from __future__ import annotations

from datetime import datetime
from typing import Generic, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict


class VMBaseModel(BaseModel):
    """Base para todos os schemas."""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class Timestamped(VMBaseModel):
    """Mixin para modelos com timestamps."""
    created_at: datetime
    updated_at: Optional[datetime] = None


T = TypeVar('T')


class PaginatedResponse(VMBaseModel, Generic[T]):
    """Resposta paginada padrão."""
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool


class ActionResponse(VMBaseModel):
    """Resposta padrão para ações."""
    success: bool
    message: Optional[str] = None
    request_id: Optional[str] = None


class HealthResponse(VMBaseModel):
    """Resposta de health check."""
    status: str
    version: Optional[str] = None
