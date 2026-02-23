from __future__ import annotations

from pathlib import Path


IDE = "cursor"


def default_target_paths(home: Path) -> list[Path]:
    return [home / ".cursor" / "mcp.json"]


def plan_changes(skill_dir: Path) -> list[dict]:
    return [
        {
            "ide": IDE,
            "target_path": str(default_target_paths(Path.home())[0]),
            "description": "Configure MCP and vibe-marketing skill rules for Cursor.",
            "proposed_content": (
                "{\n"
                f'  "generatedBy": "vm-onboard",\n'
                f'  "skillPath": "{skill_dir}"\n'
                "}\n"
            ),
        }
    ]

