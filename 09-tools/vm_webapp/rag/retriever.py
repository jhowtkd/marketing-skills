from __future__ import annotations
from ..memory import MemoryIndex, Hit

class Retriever:
    def __init__(self, index: MemoryIndex):
        self.index = index

    def retrieve(
        self, query: str, brand_id: str, campaign_id: str | None = None, top_k: int = 5
    ) -> list[Hit]:
        # Filter by brand
        filters = {"brand_id": brand_id}
        
        # Initial search (getting more than top_k for re-ranking)
        hits = self.index.search(query, filters=filters, top_k=top_k * 5)
        
        # Boost same campaign: (same_campaign, original_score)
        # Python's sort is stable, and we want to prioritize campaign match first
        def rank_key(h: Hit):
            match = h.meta.get("campaign_id") == campaign_id if campaign_id else False
            return (match, h.score)
            
        hits.sort(key=rank_key, reverse=True)
            
        return hits[:top_k]
