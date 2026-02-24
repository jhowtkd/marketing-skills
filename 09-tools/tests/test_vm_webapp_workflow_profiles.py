from pathlib import Path

import pytest

from vm_webapp.workflow_profiles import (
    DEFAULT_PROFILES_PATH,
    load_workflow_profiles,
    resolve_workflow_plan,
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
