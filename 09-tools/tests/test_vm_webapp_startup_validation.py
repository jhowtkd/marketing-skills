from __future__ import annotations

import pytest

from vm_webapp.settings import Settings
from vm_webapp.startup_checks import validate_startup_contract


def test_managed_mode_requires_db_and_redis_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("VM_ENABLE_MANAGED_MODE", "true")
    monkeypatch.delenv("VM_DB_URL", raising=False)
    monkeypatch.delenv("VM_REDIS_URL", raising=False)

    with pytest.raises(ValueError, match="managed mode requires vm_db_url"):
        validate_startup_contract(Settings())

    monkeypatch.setenv("VM_DB_URL", "postgresql://user:pass@db:5432/vm")

    with pytest.raises(ValueError, match="managed mode requires vm_redis_url"):
        validate_startup_contract(Settings())

    monkeypatch.setenv("VM_REDIS_URL", "redis://localhost:6379/0")
    validate_startup_contract(Settings())
