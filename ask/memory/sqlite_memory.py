from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ask.memory.types import ChatMessage

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conversation_id, id);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    tokenize = 'porter',
    content = 'messages',
    content_rowid = 'id'
);

CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _build_fts_query(text: str) -> str | None:
    tokens = [t for t in re.findall(r"[\w']+", text, flags=re.UNICODE) if len(t) > 2][:14]
    if not tokens:
        return None
    parts: list[str] = []
    for t in tokens:
        safe = t.replace('"', "")
        if safe:
            parts.append(f'"{safe}"')
    if not parts:
        return None
    return " OR ".join(parts)


class SqliteChatMemory:
    """SQLite-backed transcript with FTS5 BM25 retrieval."""

    def __init__(
        self,
        *,
        db_path: Path,
        conversation_id: str = "default",
        max_messages: int | None = None,
        context_search_enabled: bool = True,
        exclude_recent_for_search: int = 24,
    ) -> None:
        self._path = db_path
        self._conversation_id = conversation_id
        self._max_messages = max_messages
        self._context_search_enabled = context_search_enabled
        self._exclude_recent = max(0, exclude_recent_for_search)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._ensure_conversation()

    def _ensure_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _ensure_conversation(self) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO conversations (id, created_at, updated_at)
            VALUES (?, ?, ?)
            """,
            (self._conversation_id, now, now),
        )
        self._conn.commit()

    def _touch_conversation(self) -> None:
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_utc_now(), self._conversation_id),
        )

    def _trim(self) -> None:
        if self._max_messages is None:
            return
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
            (self._conversation_id,),
        )
        total = int(cur.fetchone()[0])
        excess = total - self._max_messages
        if excess <= 0:
            return
        self._conn.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
              AND id IN (
                SELECT id FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                LIMIT ?
              )
            """,
            (self._conversation_id, self._conversation_id, excess),
        )
        self._conn.commit()

    def append(self, message: ChatMessage) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (self._conversation_id, message["role"], message["content"], now),
        )
        self._touch_conversation()
        self._conn.commit()
        self._trim()

    def get(self) -> list[ChatMessage]:
        if self._max_messages is None:
            cur = self._conn.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (self._conversation_id,),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (self._conversation_id, self._max_messages),
            )
            rows = list(cur.fetchall())
            rows.reverse()
            return [{"role": r["role"], "content": r["content"]} for r in rows]
        return [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]

    def clear(self) -> None:
        self._conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (self._conversation_id,),
        )
        self._touch_conversation()
        self._conn.commit()

    def _recent_message_ids(self, limit: int) -> list[int]:
        if limit <= 0:
            return []
        cur = self._conn.execute(
            """
            SELECT id FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (self._conversation_id, limit),
        )
        return [int(r["id"]) for r in cur.fetchall()]

    def retrieve_context_snippets(self, query: str, *, top_k: int) -> list[str]:
        if not self._context_search_enabled or top_k <= 0:
            return []
        fts = _build_fts_query(query)
        if fts is None:
            return []
        exclude = set(self._recent_message_ids(self._exclude_recent))
        try:
            cur = self._conn.execute(
                """
                SELECT m.id, m.role, m.content
                FROM messages_fts AS f
                JOIN messages AS m ON m.id = f.rowid
                WHERE f MATCH ?
                  AND m.conversation_id = ?
                ORDER BY bm25(f)
                LIMIT ?
                """,
                (fts, self._conversation_id, top_k * 4),
            )
        except sqlite3.OperationalError:
            return []

        snippets: list[str] = []
        seen: set[str] = set()
        for row in cur.fetchall():
            mid = int(row["id"])
            if mid in exclude:
                continue
            role = row["role"]
            content = row["content"].strip()
            if not content:
                continue
            preview = content if len(content) <= 600 else content[:597] + "..."
            line = f"[{role}] {preview}"
            key = line[:200]
            if key in seen:
                continue
            seen.add(key)
            snippets.append(line)
            if len(snippets) >= top_k:
                break
        return snippets

    def close(self) -> None:
        self._conn.close()
