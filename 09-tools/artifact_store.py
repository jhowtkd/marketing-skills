from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def _run_dir(output_root: Path, project_id: str, thread_id: str) -> Path:
    return output_root / str(date.today()) / project_id / thread_id


def write_log_event(output_root: Path, project_id: str, thread_id: str, event: dict) -> Path:
    run_dir = _run_dir(output_root, project_id, thread_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "execution-log.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    return log_path


def write_artifact_file(
    output_root: Path,
    project_id: str,
    thread_id: str,
    relative_path: str,
    content: str,
) -> Path:
    artifact_path = _run_dir(output_root, project_id, thread_id) / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(content, encoding="utf-8")
    return artifact_path

