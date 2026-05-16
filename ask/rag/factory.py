from __future__ import annotations

from ask.config.settings import Settings
from ask.rag.base import Retriever
from ask.rag.chroma_retriever import ChromaRetriever
from ask.rag.none_retriever import NoOpRetriever


def create_retriever(settings: Settings) -> Retriever:
    if settings.rag_enabled:
        return ChromaRetriever(
            persist_directory=settings.rag_persist_directory,
            embedding_model=settings.rag_embedding_model,
        )
    return NoOpRetriever()
