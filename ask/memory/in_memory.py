from __future__ import annotations

from ask.memory.types import ChatMessage


class InMemoryChatMemory:
    """Session-scoped transcript store."""

    def __init__(self, *, max_messages: int | None = None) -> None:
        self._messages: list[ChatMessage] = []
        self._max_messages = max_messages

    def append(self, message: ChatMessage) -> None:
        self._messages.append(message)
        self._trim()

    def _trim(self) -> None:
        if self._max_messages is None:
            return
        while len(self._messages) > self._max_messages:
            self._messages.pop(0)

    def get(self) -> list[ChatMessage]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def retrieve_context_snippets(self, query: str, *, top_k: int) -> list[str]:
        del query, top_k
        return []
