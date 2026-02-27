"""Tests for conversation storage."""

import pytest


@pytest.mark.asyncio
async def test_create_conversation(conversation_store):
    """Should create a conversation and return its ID."""
    conv_id = await conversation_store.create_conversation("Test Chat")
    assert conv_id is not None
    assert len(conv_id) > 0


@pytest.mark.asyncio
async def test_get_conversation(conversation_store):
    """Should retrieve a conversation by ID."""
    conv_id = await conversation_store.create_conversation("Test Chat")
    conv = await conversation_store.get_conversation(conv_id)
    assert conv is not None
    assert conv["title"] == "Test Chat"


@pytest.mark.asyncio
async def test_list_conversations(conversation_store):
    """Should list conversations ordered by recency."""
    await conversation_store.create_conversation("First")
    await conversation_store.create_conversation("Second")
    convs = await conversation_store.list_conversations()
    assert len(convs) == 2


@pytest.mark.asyncio
async def test_add_and_get_messages(conversation_store):
    """Should store and retrieve messages in order."""
    conv_id = await conversation_store.create_conversation("Test")

    await conversation_store.add_message(conv_id, "user", "Hello!")
    await conversation_store.add_message(conv_id, "assistant", "Hi there!")
    await conversation_store.add_message(conv_id, "user", "How's the network?")

    messages = await conversation_store.get_messages(conv_id)
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello!"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"


@pytest.mark.asyncio
async def test_add_message_with_metadata(conversation_store):
    """Should store and retrieve message metadata."""
    conv_id = await conversation_store.create_conversation("Test")
    await conversation_store.add_message(
        conv_id, "assistant", "Response",
        metadata={"model": "qwen3-vl", "tokens": 42},
    )
    messages = await conversation_store.get_messages(conv_id)
    assert messages[0]["metadata"]["model"] == "qwen3-vl"


@pytest.mark.asyncio
async def test_delete_conversation(conversation_store):
    """Should delete conversation and all messages."""
    conv_id = await conversation_store.create_conversation("To Delete")
    await conversation_store.add_message(conv_id, "user", "Test")
    await conversation_store.delete_conversation(conv_id)

    conv = await conversation_store.get_conversation(conv_id)
    assert conv is None
