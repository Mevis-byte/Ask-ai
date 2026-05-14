from __future__ import annotations

from ask.config.settings import Settings
from ask.rag.base import Retriever
from ask.rag.none_retriever import NoOpRetriever


def create_retriever(settings: Settings) -> Retriever:
    """Central place to construct vector / hybrid retrievers from config."""
    del settings  # reserved for index paths, embedding models, etc.
    return NoOpRetriever()
