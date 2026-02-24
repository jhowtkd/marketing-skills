from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    kimi_base_url: str = "https://api.kimi.com/coding/v1"
    kimi_model: str = "kimi-for-coding"
    kimi_api_key: str = ""
    vm_workspace_root: Path = Path("runtime/vm")
    vm_db_path: Path = Path("runtime/vm/workspace.sqlite3")
    vm_workflow_profiles_path: Path | None = None
    vm_workflow_force_foundation_fallback: bool = True
    vm_workflow_foundation_mode: str = "foundation_stack"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
