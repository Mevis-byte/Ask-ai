from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ask.memory.types import ChatMessage

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    saved_at TEXT
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


@dataclass(frozen=True)
class ConversationSummary:
    id: str
    title: str
    created_at: str
    updated_at: str
    saved_at: str | None
    message_count: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_title(conversation_id: str) -> str:
    if conversation_id == "default":
        return "Default"
    return conversation_id.replace("_", " ").replace("-", " ").title()


def _is_readonly_error(exc: sqlite3.OperationalError) -> bool:
    return "readonly" in str(exc).lower()


def _conversation_columns(conn: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(conversations)")}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _ensure_conversation_columns(conn: sqlite3.Connection) -> None:
    columns = _conversation_columns(conn)
    if "title" not in columns:
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
        except sqlite3.OperationalError as exc:
            if _is_readonly_error(exc):
                return
            raise
    if "saved_at" not in columns:
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN saved_at TEXT")
        except sqlite3.OperationalError as exc:
            if _is_readonly_error(exc):
                return
            raise


def _ensure_schema_on_connection(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    _ensure_conversation_columns(conn)


def ensure_sqlite_memory_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_schema_on_connection(conn)
        conn.commit()
    finally:
        conn.close()


def list_conversations(db_path: Path) -> list[ConversationSummary]:
    try:
        ensure_sqlite_memory_db(db_path)
    except sqlite3.OperationalError as exc:
        if not _is_readonly_error(exc) or not db_path.exists():
            raise
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "conversations"):
            return []
        columns = _conversation_columns(conn)
        title_expr = "COALESCE(NULLIF(c.title, ''), c.id)" if "title" in columns else "c.id"
        saved_expr = "c.saved_at" if "saved_at" in columns else "NULL"
        rows = conn.execute(
            f"""
            SELECT
                c.id,
                {title_expr} AS title,
                c.created_at,
                c.updated_at,
                {saved_expr} AS saved_at,
                COUNT(m.id) AS message_count
            FROM conversations AS c
            LEFT JOIN messages AS m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.created_at DESC
            """
        ).fetchall()
        return [
            ConversationSummary(
                id=str(row["id"]),
                title=str(row["title"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                saved_at=str(row["saved_at"]) if row["saved_at"] is not None else None,
                message_count=int(row["message_count"]),
            )
            for row in rows
        ]
    finally:
        conn.close()


def mark_conversation_saved(
    db_path: Path,
    conversation_id: str,
    *,
    title: str | None = None,
) -> None:
    ensure_sqlite_memory_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        columns = _conversation_columns(conn)
        if "title" not in columns or "saved_at" not in columns:
            raise sqlite3.OperationalError("session metadata columns are unavailable")
        now = _utc_now()
        effective_title = title.strip() if title and title.strip() else _default_title(conversation_id)
        conn.execute(
            """
            INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at, saved_at)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (conversation_id, effective_title, now, now),
        )
        conn.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?, saved_at = ?
            WHERE id = ?
            """,
            (effective_title, now, now, conversation_id),
        )
        conn.commit()
    finally:
        conn.close()


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
        try:
            _ensure_schema_on_connection(self._conn)
        except sqlite3.OperationalError as exc:
            if not _is_readonly_error(exc):
                raise
        self._conn.commit()

    def _ensure_conversation(self) -> None:
        now = _utc_now()
        columns = _conversation_columns(self._conn)
        try:
            if "title" in columns and "saved_at" in columns:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at, saved_at)
                    VALUES (?, ?, ?, ?, NULL)
                    """,
                    (self._conversation_id, _default_title(self._conversation_id), now, now),
                )
                self._conn.execute(
                    """
                    UPDATE conversations
                    SET title = COALESCE(NULLIF(title, ''), ?)
                    WHERE id = ?
                    """,
                    (_default_title(self._conversation_id), self._conversation_id),
                )
            else:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO conversations (id, created_at, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (self._conversation_id, now, now),
                )
        except sqlite3.OperationalError as exc:
            if not _is_readonly_error(exc):
                raise
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
