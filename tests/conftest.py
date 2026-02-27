"""Shared test fixtures for NETAI Chatbot tests."""

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from netai_chatbot.config import LLMSettings
from netai_chatbot.llm.client import LLMClient
from netai_chatbot.llm.context import ContextBuilder
from netai_chatbot.llm.prompts import PromptBuilder
from netai_chatbot.network.anomaly import AnomalyDetector
from netai_chatbot.network.telemetry import TelemetryProcessor
from netai_chatbot.storage.conversations import ConversationStore
from netai_chatbot.storage.database import Database
from netai_chatbot.storage.telemetry_store import TelemetryStore


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db(tmp_path):
    """Create an in-memory test database."""
    db = Database(tmp_path / "test.db")
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def conversation_store(db):
    return ConversationStore(db)


@pytest_asyncio.fixture
async def telemetry_store(db):
    return TelemetryStore(db)


@pytest_asyncio.fixture
async def telemetry_processor(telemetry_store):
    return TelemetryProcessor(telemetry_store)


@pytest_asyncio.fixture
async def context_builder(telemetry_store):
    return ContextBuilder(telemetry_store)


@pytest_asyncio.fixture
async def anomaly_detector(telemetry_store):
    return AnomalyDetector(telemetry_store)


@pytest.fixture
def prompt_builder():
    return PromptBuilder()


@pytest.fixture
def llm_settings():
    return LLMSettings(mock_mode=True)


@pytest_asyncio.fixture
async def llm_client(llm_settings):
    client = LLMClient(llm_settings)
    await client.initialize()
    yield client
    await client.close()


@pytest.fixture
def sample_data_path():
    return Path(__file__).resolve().parent.parent / "data" / "sample" / "network_telemetry.json"


@pytest_asyncio.fixture
async def seeded_telemetry_store(telemetry_store, telemetry_processor, sample_data_path):
    """Telemetry store pre-loaded with sample data."""
    if sample_data_path.exists():
        await telemetry_processor.ingest_from_file(sample_data_path)
    return telemetry_store
