from __future__ import annotations

from typing import Mapping, Sequence

SOUL_LEVEL_BRAND = "brand"
SOUL_LEVEL_PROJECT = "project"
SOUL_LEVEL_THREAD = "thread"

SOUL_LEVELS: tuple[str, ...] = (
    SOUL_LEVEL_BRAND,
    SOUL_LEVEL_PROJECT,
    SOUL_LEVEL_THREAD,
)

_REQUIRED_SECTIONS: Mapping[str, tuple[str, ...]] = {
    SOUL_LEVEL_BRAND: (
        "Brand Overview",
        "Brand Voice",
        "Audience",
        "Guardrails",
    ),
    SOUL_LEVEL_PROJECT: (
        "Project Goal",
        "Target Outcome",
        "Scope",
        "Constraints",
    ),
    SOUL_LEVEL_THREAD: (
        "Thread Goal",
        "Current Context",
        "Action Plan",
        "Open Questions",
    ),
}

_TEMPLATES: Mapping[str, str] = {
    SOUL_LEVEL_BRAND: """# Brand Soul

## Brand Overview
Describe what the brand stands for and why it exists.

## Brand Voice
Document tone, style and communication principles.

## Audience
List the primary audience segments and needs.

## Guardrails
Capture non-negotiables, boundaries and forbidden claims.
""",
    SOUL_LEVEL_PROJECT: """# Project Soul

## Project Goal
Summarize the objective for this project.

## Target Outcome
Describe the concrete outcomes that define success.

## Scope
Define what is in scope and out of scope.

## Constraints
List timeline, resources and policy constraints.
""",
    SOUL_LEVEL_THREAD: """# Thread Soul

## Thread Goal
State the immediate goal for this thread.

## Current Context
Summarize relevant context and assumptions.

## Action Plan
Describe the next concrete actions.

## Open Questions
Track unresolved questions and dependencies.
""",
}


def _validate_level(level: str) -> str:
    if level not in SOUL_LEVELS:
        allowed = ", ".join(SOUL_LEVELS)
        raise ValueError(f"Unsupported soul level '{level}'. Expected one of: {allowed}")
    return level


def required_sections(level: str) -> list[str]:
    checked_level = _validate_level(level)
    return list(_REQUIRED_SECTIONS[checked_level])


def template_for(level: str) -> str:
    checked_level = _validate_level(level)
    return _TEMPLATES[checked_level]


def template_map() -> Mapping[str, str]:
    return _TEMPLATES


def required_sections_map() -> Mapping[str, Sequence[str]]:
    return _REQUIRED_SECTIONS
