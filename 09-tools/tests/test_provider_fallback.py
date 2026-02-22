from __future__ import annotations

from providers.free_fallback import run_research_with_fallback


def test_fallback_runs_when_premium_raises() -> None:
    def premium() -> dict:
        raise RuntimeError("premium down")

    def free() -> dict:
        return {"provider": "free", "items": [1, 2]}

    data = run_research_with_fallback(premium_runner=premium, free_runner=free)

    assert data["provider"] == "free"
    assert data["fallback_used"] is True

