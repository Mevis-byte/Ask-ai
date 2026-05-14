from __future__ import annotations

from ask.rag.base import Document, Retriever


class NoOpRetriever:
    """Default retriever until vector backends are wired in."""

    def retrieve(self, query: str, *, top_k: int) -> list[Document]:
        del query, top_k
        return []
