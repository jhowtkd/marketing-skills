from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path

    def brand_dir(self, brand_id: str) -> Path:
        return self.root / "brands" / brand_id

    def brand_soul_path(self, brand_id: str) -> Path:
        return self.brand_dir(brand_id) / "soul.md"

    def product_dir(self, brand_id: str, product_id: str) -> Path:
        return self.brand_dir(brand_id) / "products" / product_id

    def product_essence_path(self, brand_id: str, product_id: str) -> Path:
        return self.product_dir(brand_id, product_id) / "essence.md"
