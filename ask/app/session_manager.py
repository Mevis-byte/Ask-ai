from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ask.config import Settings
from ask.memory import (
    ChatMemory,
    InMemoryChatMemory,
    SqliteChatMemory,
    list_conversations,
    mark_conversation_saved,
    search_conversations,
    update_conversation_summary,
    update_conversation_title,
)


@dataclass(frozen=True)
class SessionInfo:
    id: str
    title: str
    summary: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    saved_at: str | None
    message_count: int
    persistent: bool


@dataclass
class _RamSession:
    title: str
    summary: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    saved_at: str | None
    memory: InMemoryChatMemory


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _expand_persist_path(raw: str | None) -> Path | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return Path(text).expanduser().resolve()


def _new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return f"session-{stamp}"


def derive_session_title(text: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        return "Untitled Session"
    return clean[:50] + ("..." if len(clean) > 50 else "")


def generate_session_title(messages: list[dict[str, str]]) -> str:
    """Generate a concise technical title from conversation messages.

    Uses the first user message content, cleaned and truncated intelligently.
    Attempts to extract the core technical topic from the opening line.
    """
    user_msgs = [m for m in messages if m.get("role") == "user"]
    if not user_msgs:
        return "New Session"

    first = user_msgs[0].get("content", "").strip()
    first_line = first.split("\n")[0].strip()

    clean = " ".join(first_line.split())
    if not clean:
        return "New Session"

    # Strip leading articles and common prefixes
    clean = re.sub(r"^(can you|how (do|can|would|should) (i|we)|what is|what are|explain|describe|tell me about)\s+", "", clean, flags=re.IGNORECASE)
    clean = clean.strip().strip("?").strip()

    if len(clean) <= 50:
        return clean

    # Try to truncate at a natural boundary
    truncated = clean[:50]
    # Cut at last space if possible
    last_space = truncated.rfind(" ")
    if last_space > 25:
        truncated = truncated[:last_space]
    return truncated + "..."


def _format_relative_time(iso_timestamp: str) -> str:
    """Convert ISO timestamp to a human-friendly relative string."""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = int(seconds // 60)
            return f"{m}m ago"
        if seconds < 86400:
            h = int(seconds // 3600)
            return f"{h}h ago"
        if seconds < 604800:
            d = int(seconds // 86400)
            return f"{d}d ago"
        if seconds < 2592000:
            w = int(seconds // 604800)
            return f"{w}w ago"
        return dt.strftime("%b %d")
    except (ValueError, TypeError):
        return ""


class ChatSessionManager:
    """Creates, lists, switches, and marks chat sessions without owning UI state."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._path = _expand_persist_path(settings.memory_persist_path)
        self._ram_sessions: dict[str, _RamSession] = {}
        if self._path is None:
            self.create_session(session_id="default", title="Default")

    @property
    def persistent(self) -> bool:
        return self._path is not None

    @property
    def db_path(self) -> Path | None:
        return self._path

    def initial_session_id(self) -> str:
        sessions = self.list_sessions()
        if sessions:
            return sessions[0].id
        return self.create_session(session_id="default", title="Default").id

    def create_session(
        self,
        *,
        session_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionInfo:
        sid = session_id or _new_session_id()
        label = title or "Untitled Session"
        meta = metadata or {}
        if self._path is None:
            now = _utc_now()
            memory = InMemoryChatMemory(max_messages=self._settings.memory_max_messages)
            memory.set_metadata(meta)
            self._ram_sessions[sid] = _RamSession(
                title=label,
                summary="",
                metadata=meta,
                created_at=now,
                updated_at=now,
                saved_at=None,
                memory=memory,
            )
            return self._ram_info(sid, self._ram_sessions[sid])

        memory = self.memory_for(sid)
        memory.set_metadata(meta)
        close = getattr(memory, "close", None)
        if callable(close):
            close()
        return self._session_info_for_id(sid, fallback_title=label)

    def memory_for(self, session_id: str) -> ChatMemory:
        if self._path is None:
            if session_id not in self._ram_sessions:
                self.create_session(session_id=session_id)
            return self._ram_sessions[session_id].memory
        return SqliteChatMemory(
            db_path=self._path,
            conversation_id=session_id,
            max_messages=self._settings.memory_max_messages,
            context_search_enabled=self._settings.memory_context_search_enabled,
            exclude_recent_for_search=self._settings.memory_context_exclude_recent,
        )

    def list_sessions(self) -> list[SessionInfo]:
        if self._path is None:
            return sorted(
                (self._ram_info(sid, meta) for sid, meta in self._ram_sessions.items()),
                key=lambda item: item.updated_at,
                reverse=True,
            )
        return [
            SessionInfo(
                id=item.id,
                title=item.title,
                summary=item.summary,
                metadata=item.metadata,
                created_at=item.created_at,
                updated_at=item.updated_at,
                saved_at=item.saved_at,
                message_count=item.message_count,
                persistent=True,
            )
            for item in list_conversations(self._path)
        ]

    def save_session(self, session_id: str, *, title: str | None = None, metadata: dict[str, Any] | None = None) -> SessionInfo:
        if self._path is None:
            now = _utc_now()
            if session_id not in self._ram_sessions:
                self.create_session(session_id=session_id)
            meta = self._ram_sessions[session_id]
            if title and title.strip():
                meta.title = title.strip()
            if metadata is not None:
                meta.metadata.update(metadata)
                meta.memory.set_metadata(meta.metadata)
            meta.updated_at = now
            meta.saved_at = now
            return self._ram_info(session_id, meta)

        if metadata is not None:
            memory = self.memory_for(session_id)
            existing = memory.get_metadata()
            existing.update(metadata)
            memory.set_metadata(existing)
            if hasattr(memory, "close"):
                memory.close()

        mark_conversation_saved(self._path, session_id, title=title)
        return self._session_info_for_id(session_id, fallback_title=title or "Untitled Session")

    def touch_ram_session(self, session_id: str) -> None:
        if self._path is not None or session_id not in self._ram_sessions:
            return
        self._ram_sessions[session_id].updated_at = _utc_now()

    def update_session_title(self, session_id: str, title: str) -> None:
        if not title or not title.strip():
            return
        title = title.strip()[:128]
        if self._path is None:
            if session_id in self._ram_sessions:
                self._ram_sessions[session_id].title = title
            return
        update_conversation_title(self._path, session_id, title)

    def update_session_summary(self, session_id: str, summary: str) -> None:
        if not summary or not summary.strip():
            return
        summary = summary.strip()[:1024]
        if self._path is None:
            if session_id in self._ram_sessions:
                self._ram_sessions[session_id].summary = summary
            return
        update_conversation_summary(self._path, session_id, summary)

    def find_sessions(self, query: str) -> list[SessionInfo]:
        all_sessions = self.list_sessions()
        if not query.strip():
            return all_sessions
        q = query.strip().lower()
        results: list[SessionInfo] = []
        seen: set[str] = set()
        for s in all_sessions:
            haystack = (s.title + " " + s.summary + " " + s.id).lower()
            if q in haystack:
                if s.id not in seen:
                    results.append(s)
                    seen.add(s.id)
        return results

    @staticmethod
    def generate_title(messages: list[dict[str, str]]) -> str:
        return generate_session_title(messages)

    def _session_info_for_id(self, session_id: str, *, fallback_title: str) -> SessionInfo:
        for item in self.list_sessions():
            if item.id == session_id:
                return item
        now = _utc_now()
        return SessionInfo(
            id=session_id,
            title=fallback_title,
            summary="",
            metadata={},
            created_at=now,
            updated_at=now,
            saved_at=None,
            message_count=0,
            persistent=self.persistent,
        )

    @staticmethod
    def _ram_info(session_id: str, meta: _RamSession) -> SessionInfo:
        return SessionInfo(
            id=session_id,
            title=meta.title,
            summary=meta.summary,
            metadata=meta.metadata,
            created_at=meta.created_at,
            updated_at=meta.updated_at,
            saved_at=meta.saved_at,
            message_count=len(meta.memory.get()),
            persistent=False,
        )
