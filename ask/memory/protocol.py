from __future__ import annotations

from typing import Protocol

from ask.memory.types import ChatMessage


class ChatMemory(Protocol):
    """Conversation transcript + optional retrieval over stored history."""

    def append(self, message: ChatMessage) -> None: ...

    def get(self) -> list[ChatMessage]: ...

    def clear(self) -> None: ...

    def retrieve_context_snippets(self, query: str, *, top_k: int) -> list[str]:
        """Return short text snippets from prior turns relevant to ``query``."""
        ...
