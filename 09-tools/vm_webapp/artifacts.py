from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_stage_outputs(
    *,
    stage_dir: Path,
    run_id: str,
    thread_id: str,
    stage_key: str,
    stage_position: int,
    attempt: int,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    artifacts: dict[str, str],
    event_id: str,
    status: str,
) -> dict[str, Any]:
    artifacts_dir = stage_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    _write_text_atomic(
        stage_dir / "input.json",
        json.dumps(input_payload, ensure_ascii=False, indent=2),
    )
    _write_text_atomic(
        stage_dir / "output.json",
        json.dumps(output_payload, ensure_ascii=False, indent=2),
    )

    manifest_items: list[dict[str, Any]] = []
    for name, content in artifacts.items():
        data = content.encode("utf-8")
        file_path = artifacts_dir / name
        _write_text_atomic(file_path, content)
        manifest_items.append(
            {
                "path": str(file_path.relative_to(stage_dir)),
                "kind": file_path.suffix.lstrip("."),
                "sha256": _sha256_bytes(data),
                "size": len(data),
            }
        )

    manifest = {
        "run_id": run_id,
        "thread_id": thread_id,
        "stage_key": stage_key,
        "stage_position": stage_position,
        "attempt": attempt,
        "status": status,
        "event_id": event_id,
        "artifacts": manifest_items,
        "output": output_payload,
    }
    _write_text_atomic(
        stage_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    return manifest
