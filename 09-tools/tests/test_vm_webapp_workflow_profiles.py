from pathlib import Path

import pytest

from vm_webapp.workflow_profiles import (
    DEFAULT_PROFILES_PATH,
    load_workflow_profiles,
    resolve_workflow_plan,
    resolve_workflow_plan_with_contract,
)


def test_load_default_workflow_profiles_has_expected_modes() -> None:
    profiles = load_workflow_profiles(DEFAULT_PROFILES_PATH)
    assert "plan_90d" in profiles
    assert "content_calendar" in profiles
    assert profiles["plan_90d"].stages


def test_resolve_workflow_plan_applies_skill_overrides() -> None:
    profiles = load_workflow_profiles(DEFAULT_PROFILES_PATH)
    plan = resolve_workflow_plan(
        profiles,
        mode="plan_90d",
        skill_overrides={"strategy_draft": ["04-copy/direct-response"]},
    )
    target = next(stage for stage in plan["stages"] if stage["key"] == "strategy_draft")
    assert target["skills"] == ["04-copy/direct-response"]


def test_load_workflow_profiles_rejects_invalid_shape(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("profiles:\n  - mode: bad\n    stages: [1,2,3]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_workflow_profiles(broken)


def test_resolve_workflow_plan_uses_foundation_effective_mode_when_forced() -> None:
    profiles = load_workflow_profiles(DEFAULT_PROFILES_PATH)
    resolved = resolve_workflow_plan_with_contract(
        profiles,
        requested_mode="content_calendar",
        skill_overrides={},
        force_foundation_fallback=True,
        foundation_mode="foundation_stack",
    )
    assert resolved["requested_mode"] == "content_calendar"
    assert resolved["effective_mode"] == "foundation_stack"
    assert resolved["fallback_applied"] is True
    assert resolved["profile_version"] == "v1"
