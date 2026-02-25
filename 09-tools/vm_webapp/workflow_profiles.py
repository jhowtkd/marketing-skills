from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_PROFILES_PATH = Path(__file__).with_name("workflow_profiles.yaml")
FOUNDATION_MODE_DEFAULT = "foundation_stack"
PROFILES_VERSION_DEFAULT = "v1"


@dataclass(slots=True, frozen=True)
class WorkflowStageProfile:
    key: str
    skills: list[str]
    approval_required: bool
    retry_policy: dict[str, int]
    timeout_seconds: int
    fallback_providers: list[str]


@dataclass(slots=True, frozen=True)
class WorkflowModeProfile:
    mode: str
    description: str
    stages: list[WorkflowStageProfile]


def _require_str(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"workflow profile field `{field}` must be a non-empty string")
    return value.strip()


def _require_skills(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("skills")
    if not isinstance(raw, list) or not raw:
        raise ValueError("workflow profile stage `skills` must be a non-empty list")
    skills: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("workflow profile stage skills must be non-empty strings")
        skills.append(item.strip())
    return skills


def _require_fallback_providers(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("fallback_providers", [])
    if not isinstance(raw, list):
        raise ValueError("workflow profile stage `fallback_providers` must be a list")
    providers: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("workflow profile stage fallback_providers must be non-empty strings")
        providers.append(item.strip())
    return providers


def _require_retry_policy(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("retry_policy", {})
    if not isinstance(raw, dict):
        raise ValueError("workflow profile `retry_policy` must be a mapping")
    max_attempts = raw.get("max_attempts", 1)
    backoff_seconds = raw.get("backoff_seconds", 0)
    if not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("workflow profile retry_policy.max_attempts must be >= 1")
    if not isinstance(backoff_seconds, int) or backoff_seconds < 0:
        raise ValueError("workflow profile retry_policy.backoff_seconds must be >= 0")
    return {"max_attempts": max_attempts, "backoff_seconds": backoff_seconds}


def _parse_stage(payload: Any) -> WorkflowStageProfile:
    if not isinstance(payload, dict):
        raise ValueError("workflow profile stages must be objects")
    timeout = payload.get("timeout_seconds", 120)
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("workflow profile stage timeout_seconds must be > 0")
    return WorkflowStageProfile(
        key=_require_str(payload, "key"),
        skills=_require_skills(payload),
        approval_required=bool(payload.get("approval_required", False)),
        retry_policy=_require_retry_policy(payload),
        timeout_seconds=timeout,
        fallback_providers=_require_fallback_providers(payload),
    )


def load_workflow_profiles(path: Path | None = None) -> dict[str, WorkflowModeProfile]:
    profile_path = path or DEFAULT_PROFILES_PATH
    payload = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    rows = payload.get("profiles")
    if not isinstance(rows, list) or not rows:
        raise ValueError("workflow profile file must contain a non-empty `profiles` list")

    modes: dict[str, WorkflowModeProfile] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("workflow profiles must be objects")
        mode = _require_str(row, "mode")
        if mode in modes:
            raise ValueError(f"duplicated workflow mode: {mode}")
        stages_raw = row.get("stages")
        if not isinstance(stages_raw, list) or not stages_raw:
            raise ValueError(f"workflow mode `{mode}` must define non-empty stages")
        stages = [_parse_stage(item) for item in stages_raw]
        modes[mode] = WorkflowModeProfile(
            mode=mode,
            description=str(row.get("description", "")).strip(),
            stages=stages,
        )
    return modes


def resolve_workflow_plan(
    profiles: dict[str, WorkflowModeProfile],
    *,
    mode: str,
    skill_overrides: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    profile = profiles.get(mode)
    if profile is None:
        allowed = ", ".join(sorted(profiles))
        raise ValueError(f"unknown workflow mode: {mode}. available: {allowed}")

    overrides = skill_overrides or {}
    stages: list[dict[str, Any]] = []
    known_stage_keys = {stage.key for stage in profile.stages}
    for stage_key in overrides:
        if stage_key not in known_stage_keys:
            raise ValueError(f"unknown stage override key: {stage_key}")

    for stage in profile.stages:
        resolved_skills = stage.skills
        if stage.key in overrides:
            replacement = overrides[stage.key]
            if not isinstance(replacement, list) or not replacement:
                raise ValueError(f"stage override `{stage.key}` must be a non-empty list")
            normalized: list[str] = []
            for item in replacement:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(f"stage override `{stage.key}` contains invalid skill")
                normalized.append(item.strip())
            resolved_skills = normalized
        stages.append(
            {
                "key": stage.key,
                "skills": resolved_skills,
                "approval_required": stage.approval_required,
                "retry_policy": dict(stage.retry_policy),
                "timeout_seconds": stage.timeout_seconds,
                "fallback_providers": list(stage.fallback_providers),
            }
        )

    return {
        "mode": profile.mode,
        "description": profile.description,
        "stages": stages,
    }


def resolve_workflow_plan_with_contract(
    profiles: dict[str, WorkflowModeProfile],
    *,
    requested_mode: str,
    skill_overrides: dict[str, list[str]] | None,
    force_foundation_fallback: bool,
    foundation_mode: str = FOUNDATION_MODE_DEFAULT,
) -> dict[str, Any]:
    effective_mode = foundation_mode if force_foundation_fallback else requested_mode
    if not force_foundation_fallback and effective_mode not in profiles:
        effective_mode = foundation_mode

    plan = resolve_workflow_plan(
        profiles,
        mode=effective_mode,
        skill_overrides=skill_overrides or {},
    )
    return {
        **plan,
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "fallback_applied": requested_mode != effective_mode,
        "profile_version": PROFILES_VERSION_DEFAULT,
    }
