from __future__ import annotations

from stack_loader import load_stack


def test_foundation_stack_has_manual_gates_after_research() -> None:
    stack = load_stack("06-stacks/foundation-stack/stack.yaml")
    gates = {stage["id"]: stage["approval_required"] for stage in stack["sequence"]}

    assert gates["research"] is False
    assert gates["brand-voice"] is True
    assert gates["positioning"] is True
    assert gates["keywords"] is True

