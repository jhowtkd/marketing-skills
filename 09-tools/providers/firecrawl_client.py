from __future__ import annotations

import os


def run_firecrawl_extract(urls: list[str]) -> dict:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY missing")

    return {
        "provider": "firecrawl",
        "urls": urls,
        "pages": [],
    }

