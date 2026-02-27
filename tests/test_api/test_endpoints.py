"""Tests for the API endpoints."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from netai_chatbot.main import app, lifespan


@pytest_asyncio.fixture
async def client(tmp_path):
    """Create a test HTTP client with isolated temp database."""
    db_path = tmp_path / "test_api.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["LLM_MOCK_MODE"] = "true"
    try:
        async with lifespan(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
    finally:
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("LLM_MOCK_MODE", None)


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Root should return service info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NETAI Chatbot"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health check should return status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "llm_available" in data
    assert "database_connected" in data


@pytest.mark.asyncio
async def test_chat_new_conversation(client):
    """Should create a new conversation and return a response."""
    response = await client.post("/api/v1/chat", json={
        "message": "Hello, what can you help me with?",
    })
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert len(data["message"]) > 0
    assert "model" in data


@pytest.mark.asyncio
async def test_chat_continue_conversation(client):
    """Should continue an existing conversation."""
    # Create conversation
    r1 = await client.post("/api/v1/chat", json={"message": "Hi!"})
    conv_id = r1.json()["conversation_id"]

    # Continue it
    r2 = await client.post("/api/v1/chat", json={
        "message": "What about throughput?",
        "conversation_id": conv_id,
    })
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id


@pytest.mark.asyncio
async def test_chat_invalid_conversation(client):
    """Should return 404 for nonexistent conversation."""
    response = await client.post("/api/v1/chat", json={
        "message": "Hello",
        "conversation_id": "nonexistent-id",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_conversations(client):
    """Should list conversations."""
    # Create one first
    await client.post("/api/v1/chat", json={"message": "Test"})

    response = await client.get("/api/v1/chat/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_conversation_messages(client):
    """Should return messages for a conversation."""
    r = await client.post("/api/v1/chat", json={"message": "Hello!"})
    conv_id = r.json()["conversation_id"]

    response = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) >= 2  # user + assistant


@pytest.mark.asyncio
async def test_delete_conversation(client):
    """Should delete a conversation."""
    r = await client.post("/api/v1/chat", json={"message": "Delete me"})
    conv_id = r.json()["conversation_id"]

    response = await client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_diagnostics_anomalies(client):
    """Should return anomaly list."""
    response = await client.get("/api/v1/diagnostics/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_diagnostics_telemetry_summary(client):
    """Should return telemetry summary."""
    response = await client.get("/api/v1/diagnostics/telemetry/summary")
    assert response.status_code == 200
    assert "summary" in response.json()


@pytest.mark.asyncio
async def test_diagnostics_hosts(client):
    """Should return monitored host pairs."""
    response = await client.get("/api/v1/diagnostics/telemetry/hosts")
    assert response.status_code == 200
    assert "host_pairs" in response.json()


@pytest.mark.asyncio
async def test_diagnostics_models(client):
    """Should return available LLM models."""
    response = await client.get("/api/v1/diagnostics/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) >= 4


@pytest.mark.asyncio
async def test_diagnose_path(client):
    """Should diagnose a network path."""
    response = await client.post("/api/v1/diagnostics/diagnose", json={
        "src_host": "perfsonar-ucsd.nrp.ai",
        "dst_host": "perfsonar-starlight.nrp.ai",
    })
    assert response.status_code == 200
    data = response.json()
    assert "diagnosis" in data
    assert "metrics_summary" in data


@pytest.mark.asyncio
async def test_query_telemetry(client):
    """Should query telemetry records."""
    response = await client.post("/api/v1/diagnostics/telemetry", json={
        "metric_type": "throughput",
        "limit": 10,
    })
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert "count" in data
