from __future__ import annotations

from pathlib import Path

from ask.config import Settings
from ask.memory.in_memory import InMemoryChatMemory
from ask.memory.protocol import ChatMemory
from ask.memory.sqlite_memory import SqliteChatMemory


def _expand_persist_path(raw: str | None) -> Path | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return Path(s).expanduser().resolve()


def create_chat_memory(settings: Settings) -> ChatMemory:
    """SQLite when ``persist_path`` is set; otherwise in-memory only."""
    path = _expand_persist_path(settings.memory_persist_path)
    if path is None:
        return InMemoryChatMemory(max_messages=settings.memory_max_messages)
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteChatMemory(
        db_path=path,
        conversation_id="default",
        max_messages=settings.memory_max_messages,
        context_search_enabled=settings.memory_context_search_enabled,
        exclude_recent_for_search=settings.memory_context_exclude_recent,
    )
