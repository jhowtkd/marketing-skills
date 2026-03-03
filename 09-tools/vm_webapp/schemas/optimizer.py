from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from .base import VMBaseModel


class OptimizerQueueItem(VMBaseModel):
    request_id: str
    run_id: Optional[str] = None
    thread_id: str
    brand_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    priority: int = 5
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request_type: str = "workflow"


class OptimizerQueueListResponse(VMBaseModel):
    items: list[OptimizerQueueItem]
    total_count: int
    processing_count: int
    queued_count: int


class OptimizerRequest(VMBaseModel):
    thread_id: str
    brand_id: str
    request_type: str = "workflow"
    priority: int = 5
    payload: dict = {}


class OptimizerRequestResponse(VMBaseModel):
    request_id: str
    status: Literal["queued", "processing"]
    estimated_wait_seconds: int = 0
    queue_position: int = 0
