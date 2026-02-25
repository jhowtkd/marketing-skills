from __future__ import annotations

from vm_webapp.settings import Settings


def validate_startup_contract(settings: Settings) -> None:
    if not settings.vm_enable_managed_mode:
        return
    if not settings.vm_db_url:
        raise ValueError("managed mode requires vm_db_url")
    if not settings.vm_redis_url:
        raise ValueError("managed mode requires vm_redis_url")
