"""Conversation history storage operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .database import Database


class ConversationStore:
    """Manages conversation persistence."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_conversation(self, title: str | None = None) -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        title = title or f"Conversation {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        await self.db.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, title),
        )
        return conv_id

    async def get_conversation(self, conversation_id: str) -> dict | None:
        """Get conversation metadata."""
        return await self.db.fetch_one(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        )

    async def list_conversations(self, limit: int = 50) -> list[dict]:
        """List recent conversations."""
        return await self.db.fetch_all(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        """Add a message to a conversation. Returns the message ID."""
        cursor = await self.db.execute(
            "INSERT INTO messages (conversation_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, json.dumps(metadata or {})),
        )
        # Update conversation timestamp
        await self.db.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        return cursor.lastrowid  # type: ignore[return-value]

    async def get_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[dict]:
        """Get messages for a conversation, ordered chronologically."""
        rows = await self.db.fetch_all(
            """SELECT id, role, content, metadata, created_at
               FROM messages
               WHERE conversation_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (conversation_id, limit),
        )
        for row in rows:
            row["metadata"] = json.loads(row["metadata"])
        return rows

    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its messages."""
        await self.db.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
        )
        await self.db.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
