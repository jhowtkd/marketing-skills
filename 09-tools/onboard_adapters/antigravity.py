from __future__ import annotations

from pathlib import Path


IDE = "antigravity"


def default_target_paths(home: Path) -> list[Path]:
    return [home / ".agents" / "workflows" / "vibe-onboard.yaml"]


def plan_changes(skill_dir: Path) -> list[dict]:
    return [
        {
            "ide": IDE,
            "target_path": str(default_target_paths(Path.home())[0]),
            "description": "Configure Antigravity workflow hook for vibe-marketing onboarding.",
            "proposed_content": (
                "name: vibe-onboard\n"
                "generatedBy: vm-onboard\n"
                f"skillPath: {skill_dir}\n"
            ),
        }
    ]

