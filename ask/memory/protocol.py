from __future__ import annotations

from typing import Any, Protocol

from ask.memory.types import ChatMessage


class ChatMemory(Protocol):
    """Conversation transcript + optional retrieval over stored history."""

    def append(self, message: ChatMessage) -> None: ...

    def get(self) -> list[ChatMessage]: ...

    def clear(self) -> None: ...

    def get_metadata(self) -> dict[str, Any]: ...

    def set_metadata(self, metadata: dict[str, Any]) -> None: ...

    def retrieve_context_snippets(self, query: str, *, top_k: int) -> list[str]:
        """Return short text snippets from prior turns relevant to ``query``."""
        ...
