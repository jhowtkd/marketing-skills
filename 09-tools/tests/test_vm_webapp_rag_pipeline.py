import pytest
from pathlib import Path
from vm_webapp.rag.indexer import Indexer
from vm_webapp.rag.retriever import Retriever
from vm_webapp.memory import MemoryIndex

def test_rag_retrieval_prefers_same_brand_and_campaign(tmp_path: Path) -> None:
    index = MemoryIndex(root=tmp_path / "rag_index")
    indexer = Indexer(index)
    retriever = Retriever(index)
    
    # Ingest docs from different brands/campaigns
    indexer.ingest_text(
        doc_id="d1",
        text="Acme Brand Soul: We are innovative and fast.",
        brand_id="acme",
        campaign_id="launch"
    )
    indexer.ingest_text(
        doc_id="d2",
        text="Globex Brand Soul: We are traditional and stable.",
        brand_id="globex",
        campaign_id="rebrand"
    )
    indexer.ingest_text(
        doc_id="d3",
        text="Acme Brand Soul: We value safety above all.",
        brand_id="acme",
        campaign_id="safety_first"
    )

    # Search for Acme Brand Soul, preferring 'launch' campaign
    hits = retriever.retrieve(
        query="Brand Soul",
        brand_id="acme",
        campaign_id="launch",
        top_k=5
    )
    
    assert len(hits) >= 2
    # Should only have acme docs
    for hit in hits:
        assert hit.meta["brand_id"] == "acme"
        
    # Should prefer the same campaign (d1 over d3)
    assert hits[0].meta["original_doc_id"] == "d1"
