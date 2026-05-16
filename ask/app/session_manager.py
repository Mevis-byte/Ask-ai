from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ask.config import Settings
from ask.memory import (
    ChatMemory,
    InMemoryChatMemory,
    SqliteChatMemory,
    list_conversations,
    mark_conversation_saved,
)


@dataclass(frozen=True)
class SessionInfo:
    id: str
    title: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    saved_at: str | None
    message_count: int
    persistent: bool


@dataclass
class _RamSession:
    title: str
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
    return clean[:44] + ("..." if len(clean) > 44 else "")


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

    def _session_info_for_id(self, session_id: str, *, fallback_title: str) -> SessionInfo:
        for item in self.list_sessions():
            if item.id == session_id:
                return item
        now = _utc_now()
        return SessionInfo(
            id=session_id,
            title=fallback_title,
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
            created_at=meta.created_at,
            updated_at=meta.updated_at,
            saved_at=meta.saved_at,
            message_count=len(meta.memory.get()),
            persistent=False,
        )
