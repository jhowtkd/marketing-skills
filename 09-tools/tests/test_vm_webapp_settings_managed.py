from __future__ import annotations

import pytest
from pydantic import ValidationError

from vm_webapp.settings import Settings


def test_settings_supports_db_url_redis_url_and_env_validation(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("VM_DB_URL", "postgresql+psycopg://user:pass@db/vm")
    monkeypatch.setenv("VM_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("VM_ENABLE_MANAGED_MODE", "true")

    settings = Settings()

    assert settings.app_env == "staging"
    assert settings.vm_db_url == "postgresql+psycopg://user:pass@db/vm"
    assert settings.vm_redis_url == "redis://localhost:6379/0"
    assert settings.vm_enable_managed_mode is True

    monkeypatch.setenv("APP_ENV", "invalid")
    with pytest.raises(ValidationError):
        Settings()
