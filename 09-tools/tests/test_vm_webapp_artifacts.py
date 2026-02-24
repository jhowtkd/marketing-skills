from pathlib import Path

from vm_webapp.artifacts import write_stage_outputs


def test_write_stage_outputs_creates_manifest_with_hashes(tmp_path: Path) -> None:
    stage_dir = tmp_path / "runs" / "run-1" / "stages" / "01-plan"
    result = write_stage_outputs(
        stage_dir=stage_dir,
        run_id="run-1",
        thread_id="t1",
        stage_key="plan",
        stage_position=1,
        attempt=1,
        input_payload={"request_text": "Build plan"},
        output_payload={"summary": "Done"},
        artifacts={
            "plan.md": "# Plan\n\nOutput",
            "meta.json": '{"ok": true}',
        },
        event_id="evt-1",
        status="completed",
    )

    manifest = stage_dir / "manifest.json"
    assert manifest.exists()
    assert (stage_dir / "input.json").exists()
    assert (stage_dir / "output.json").exists()
    assert len(result["artifacts"]) == 2
    assert all(item["sha256"] for item in result["artifacts"])


def test_write_stage_outputs_uses_atomic_writes(tmp_path: Path) -> None:
    stage_dir = tmp_path / "runs" / "run-2" / "stages" / "01-plan"
    write_stage_outputs(
        stage_dir=stage_dir,
        run_id="run-2",
        thread_id="t2",
        stage_key="plan",
        stage_position=1,
        attempt=1,
        input_payload={"request_text": "Build plan"},
        output_payload={"summary": "Done"},
        artifacts={"plan.md": "# Plan"},
        event_id="evt-2",
        status="completed",
    )

    leftovers = list(stage_dir.rglob("*.tmp"))
    assert leftovers == []
