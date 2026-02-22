from __future__ import annotations

import json
from pathlib import Path


def _state_path(runtime_root: Path, project_id: str, thread_id: str) -> Path:
    return runtime_root / "projects" / project_id / "threads" / thread_id / "state.json"


def save_state(runtime_root: Path, project_id: str, thread_id: str, state: dict) -> Path:
    path = _state_path(runtime_root, project_id, thread_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_state(runtime_root: Path, project_id: str, thread_id: str) -> dict:
    path = _state_path(runtime_root, project_id, thread_id)
    return json.loads(path.read_text(encoding="utf-8"))

