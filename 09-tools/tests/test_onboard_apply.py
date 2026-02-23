from __future__ import annotations

from pathlib import Path

from onboard import apply_change


def test_apply_change_creates_backup_and_writes_target(tmp_path: Path) -> None:
    target = tmp_path / "cfg.yml"
    target.write_text("old\n", encoding="utf-8")

    result = apply_change(target, "new\n")

    assert target.read_text(encoding="utf-8") == "new\n"
    assert result["backup_path"]
    assert Path(result["backup_path"]).exists()

