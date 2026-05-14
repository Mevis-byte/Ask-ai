from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Document:
    """A retrieved chunk (text + optional source id)."""

    text: str
    source: str | None = None


class Retriever(Protocol):
    def retrieve(self, query: str, *, top_k: int) -> list[Document]:
        ...
