"""Tests for the SQLite database layer."""

import pytest


@pytest.mark.asyncio
async def test_database_connect(db):
    """Database should be connected and schema initialized."""
    result = await db.fetch_one("SELECT COUNT(*) as cnt FROM conversations")
    assert result is not None
    assert result["cnt"] == 0


@pytest.mark.asyncio
async def test_database_execute(db):
    """Should execute SQL statements."""
    await db.execute(
        "INSERT INTO conversations (id, title) VALUES (?, ?)",
        ("test-1", "Test Conversation"),
    )
    result = await db.fetch_one("SELECT * FROM conversations WHERE id = ?", ("test-1",))
    assert result is not None
    assert result["title"] == "Test Conversation"


@pytest.mark.asyncio
async def test_database_fetch_all(db):
    """Should fetch all matching rows."""
    await db.execute("INSERT INTO conversations (id, title) VALUES (?, ?)", ("c1", "Conv 1"))
    await db.execute("INSERT INTO conversations (id, title) VALUES (?, ?)", ("c2", "Conv 2"))

    results = await db.fetch_all("SELECT * FROM conversations ORDER BY id")
    assert len(results) == 2
    assert results[0]["id"] == "c1"
    assert results[1]["id"] == "c2"


@pytest.mark.asyncio
async def test_database_fetch_one_missing(db):
    """Should return None for missing rows."""
    result = await db.fetch_one("SELECT * FROM conversations WHERE id = ?", ("nonexistent",))
    assert result is None
