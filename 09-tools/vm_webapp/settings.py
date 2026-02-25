from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    _ALLOWED_APP_ENVS: ClassVar[set[str]] = {"local", "staging", "production", "prod"}

    app_env: str = "local"
    kimi_base_url: str = "https://api.kimi.com/coding/v1"
    kimi_model: str = "kimi-for-coding"
    kimi_api_key: str = ""
    vm_workspace_root: Path = Path("runtime/vm")
    vm_db_path: Path = Path("runtime/vm/workspace.sqlite3")
    vm_db_url: str | None = None
    vm_redis_url: str | None = None
    vm_enable_managed_mode: bool = False
    vm_workflow_profiles_path: Path | None = None
    vm_workflow_force_foundation_fallback: bool = True
    vm_workflow_foundation_mode: str = "foundation_stack"

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        if value not in cls._ALLOWED_APP_ENVS:
            allowed = ", ".join(sorted(cls._ALLOWED_APP_ENVS))
            raise ValueError(f"app_env must be one of: {allowed}")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
