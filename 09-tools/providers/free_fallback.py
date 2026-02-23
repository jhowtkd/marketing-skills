from __future__ import annotations

from collections.abc import Callable


def run_research_with_fallback(
    premium_runner: Callable[[], dict],
    free_runner: Callable[[], dict],
) -> dict:
    try:
        payload = premium_runner()
        payload["fallback_used"] = False
        return payload
    except Exception as exc:
        payload = free_runner()
        payload["fallback_used"] = True
        payload["premium_error"] = str(exc)
        return payload
