from pathlib import Path

from vm_webapp.memory import MemoryIndex


def test_memory_index_retrieves_brand_soul(tmp_path: Path) -> None:
    index = MemoryIndex(root=tmp_path / "zvec")
    index.upsert_doc(
        doc_id="brand:b1:soul",
        text="Acme speaks with calm, evidence-led clarity.",
        meta={"brand_id": "b1", "kind": "soul"},
    )

    hits = index.search("evidence clarity", filters={"brand_id": "b1"}, top_k=3)
    assert hits
    assert "evidence-led" in hits[0].text
