from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlannedChange:
    ide: str
    target_path: Path
    proposed_content: str

