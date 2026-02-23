from pathlib import Path

from vm_webapp.workspace import Workspace


def test_workspace_paths(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path)
    brand_id = "b1"
    product_id = "p1"

    assert ws.brand_dir(brand_id) == tmp_path / "brands" / brand_id
    assert ws.brand_soul_path(brand_id).name == "soul.md"
    assert ws.product_essence_path(brand_id, product_id).name == "essence.md"
