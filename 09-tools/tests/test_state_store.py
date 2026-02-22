from __future__ import annotations

from pathlib import Path

from state_store import load_state, save_state


def test_save_and_load_state_roundtrip(tmp_path: Path) -> None:
    state = {"project_id": "acme", "thread_id": "th-001", "status": "running"}

    save_state(tmp_path, "acme", "th-001", state)
    loaded = load_state(tmp_path, "acme", "th-001")

    assert loaded["project_id"] == "acme"
    assert loaded["thread_id"] == "th-001"

