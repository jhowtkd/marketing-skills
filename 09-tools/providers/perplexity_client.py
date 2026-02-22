from __future__ import annotations

import os


def run_perplexity_research(query: str) -> dict:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY missing")

    return {
        "provider": "perplexity",
        "query": query,
        "results": [],
    }

