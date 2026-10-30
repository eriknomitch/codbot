"""Saved chat history: conversations and their messages, kept in a SQLite database."""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "history.sqlite3"
TITLE_LENGTH = 80

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_by_conversation ON messages(conversation_id, id);
-- Outside identifiers (like Discord message IDs) and the conversation each belongs to.
CREATE TABLE IF NOT EXISTS links (
    key TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
);
"""


def history_path() -> Path:
    return Path(os.environ.get("CODBOT_HISTORY_DB", DEFAULT_PATH))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_title(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= TITLE_LENGTH else title[: TITLE_LENGTH - 1].rstrip() + "…"


class History:
    def __init__(self, path: Path | None = None) -> None:
        path = path or history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    def create(self, title: str) -> str:
        """Start a conversation and return its ID."""
        conversation_id = uuid.uuid4().hex[:12]
        stamp = now()
        with self.db:
            self.db.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, make_title(title), stamp, stamp),
            )
        return conversation_id

    def exists(self, conversation_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone() is not None

    def add(self, conversation_id: str, role: str, content: str) -> None:
        stamp = now()
        with self.db:
            self.db.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, stamp),
            )
            self.db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (stamp, conversation_id))

    def messages(self, conversation_id: str) -> list[dict]:
        """A conversation's messages, oldest first, as {"role", "content", "created_at"} dicts."""
        rows = self.db.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        )
        return [dict(row) for row in rows]

    def get(self, conversation_id: str) -> dict | None:
        """A conversation's details and messages, or None if there's no such conversation."""
        row = self.db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return {**dict(row), "messages": self.messages(conversation_id)} if row else None

    def list(self, limit: int = 50) -> list[dict]:
        """The most recently active conversations first."""
        rows = self.db.execute("SELECT * FROM conversations ORDER BY updated_at DESC, rowid DESC LIMIT ?", (limit,))
        return [dict(row) for row in rows]

    def latest(self) -> str | None:
        conversations = self.list(limit=1)
        return conversations[0]["id"] if conversations else None

    def delete(self, conversation_id: str) -> bool:
        with self.db:
            return self.db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,)).rowcount > 0

    def link(self, key: str, conversation_id: str) -> None:
        """Remember that an outside identifier belongs to a conversation."""
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO links (key, conversation_id) VALUES (?, ?)", (key, conversation_id)
            )

    def find(self, key: str) -> str | None:
        """The conversation an outside identifier was linked to, if any."""
        row = self.db.execute("SELECT conversation_id FROM links WHERE key = ?", (key,)).fetchone()
        return row["conversation_id"] if row else None
