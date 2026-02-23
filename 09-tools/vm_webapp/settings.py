from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    kimi_base_url: str = "https://api.kimi.com/coding/v1"
    kimi_model: str = "kimi-for-coding"
    kimi_api_key: str = ""
    vm_workspace_root: Path = Path("runtime/vm")
    vm_db_path: Path = Path("runtime/vm/workspace.sqlite3")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
