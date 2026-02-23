from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Hit:
    doc_id: str
    text: str
    meta: dict[str, Any]
    score: float


class MemoryIndex:
    """Simple local index with sparse retrieval and metadata filters.

    This keeps an explicit fallback path that does not depend on downloading or
    initializing dense embedding models.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._docs_path = self.root / "docs.json"
        self._docs: dict[str, dict[str, Any]] = {}
        self._load()

    def upsert_doc(self, doc_id: str, text: str, meta: dict[str, Any]) -> None:
        self._docs[doc_id] = {"doc_id": doc_id, "text": text, "meta": dict(meta)}
        self._persist()

    def search(
        self,
        query: str,
        *,
        filters: dict[str, Any],
        top_k: int,
    ) -> list[Hit]:
        query_terms = set(TOKEN_RE.findall(query.lower()))
        hits: list[Hit] = []
        for item in self._docs.values():
            meta = item["meta"]
            if any(meta.get(k) != v for k, v in filters.items()):
                continue
            text = item["text"]
            score = self._sparse_score(query_terms, text)
            if score <= 0 and query_terms:
                continue
            hits.append(
                Hit(
                    doc_id=item["doc_id"],
                    text=text,
                    meta=meta,
                    score=score,
                )
            )

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def _load(self) -> None:
        if not self._docs_path.exists():
            return
        data = json.loads(self._docs_path.read_text(encoding="utf-8"))
        self._docs = {item["doc_id"]: item for item in data}

    def _persist(self) -> None:
        items = list(self._docs.values())
        self._docs_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _sparse_score(query_terms: set[str], text: str) -> float:
        if not query_terms:
            return 1.0
        tokens = TOKEN_RE.findall(text.lower())
        if not tokens:
            return 0.0
        overlap = sum(1 for token in tokens if token in query_terms)
        return overlap / max(len(tokens), 1)
