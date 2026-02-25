from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel

class ToolResult(BaseModel):
    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    audit_payload: Optional[dict[str, Any]] = None

class ToolContract(ABC):
    @property
    @abstractmethod
    def tool_id(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        pass
