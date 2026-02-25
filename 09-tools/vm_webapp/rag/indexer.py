from __future__ import annotations
from typing import Any
from ..memory import MemoryIndex
from .chunker import chunk_text

class Indexer:
    def __init__(self, index: MemoryIndex):
        self.index = index

    def ingest_text(self, doc_id: str, text: str, brand_id: str, campaign_id: str | None = None):
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            meta = {
                "brand_id": brand_id,
                "original_doc_id": doc_id,
                "chunk_index": i
            }
            if campaign_id:
                meta["campaign_id"] = campaign_id
                
            self.index.upsert_doc(
                doc_id=f"{doc_id}:{i}",
                text=chunk,
                meta=meta
            )
