from __future__ import annotations

from typing import Any, Protocol


class ChatBackend(Protocol):
    """Pluggable LLM transport (Ollama today; swap for HTTP APIs later)."""

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> Any:
        """Return a full response dict (stream=False) or an iterable of stream chunks."""
        ...
