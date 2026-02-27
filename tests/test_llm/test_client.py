"""Tests for the LLM client."""

import pytest

from netai_chatbot.llm.client import ChatMessage, LLMResponse


@pytest.mark.asyncio
async def test_mock_chat_default(llm_client):
    """Mock mode should return a default response."""
    messages = [ChatMessage(role="user", content="Hello, who are you?")]
    response = await llm_client.chat(messages)

    assert isinstance(response, LLMResponse)
    assert "NETAI" in response.content
    assert response.model == "mock-model"
    assert response.usage["total_tokens"] == 150


@pytest.mark.asyncio
async def test_mock_chat_throughput(llm_client):
    """Mock mode should respond contextually to throughput questions."""
    messages = [ChatMessage(role="user", content="What is the current throughput?")]
    response = await llm_client.chat(messages)
    assert "throughput" in response.content.lower() or "Gbps" in response.content


@pytest.mark.asyncio
async def test_mock_chat_latency(llm_client):
    """Mock mode should respond contextually to latency questions."""
    messages = [ChatMessage(role="user", content="What is the latency between hosts?")]
    response = await llm_client.chat(messages)
    assert "latency" in response.content.lower() or "ms" in response.content


@pytest.mark.asyncio
async def test_mock_chat_anomaly(llm_client):
    """Mock mode should respond contextually to anomaly questions."""
    messages = [ChatMessage(role="user", content="Is there a packet loss issue?")]
    response = await llm_client.chat(messages)
    assert "anomaly" in response.content.lower() or "loss" in response.content.lower()


@pytest.mark.asyncio
async def test_mock_chat_stream(llm_client):
    """Mock streaming should yield words."""
    messages = [ChatMessage(role="user", content="Hello")]
    chunks = []
    async for chunk in llm_client.chat_stream(messages):
        chunks.append(chunk)
    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert len(full_text) > 10


@pytest.mark.asyncio
async def test_mock_list_models(llm_client):
    """Mock mode should return available models."""
    models = await llm_client.list_models()
    assert len(models) == 4
    model_ids = [m["id"] for m in models]
    assert "gpt-4o" in model_ids
    assert "qwen3-vl" in model_ids


def test_chat_message_to_dict():
    """ChatMessage should serialize correctly."""
    msg = ChatMessage(role="user", content="Test message")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "Test message"}
