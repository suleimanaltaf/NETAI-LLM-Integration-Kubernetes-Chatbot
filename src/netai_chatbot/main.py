"""FastAPI application entry point for NETAI Chatbot."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from netai_chatbot import __version__
from netai_chatbot.config import Settings, get_settings
from netai_chatbot.llm.client import LLMClient
from netai_chatbot.llm.context import ContextBuilder
from netai_chatbot.llm.prompts import PromptBuilder
from netai_chatbot.network.anomaly import AnomalyDetector
from netai_chatbot.network.telemetry import TelemetryProcessor
from netai_chatbot.storage.conversations import ConversationStore
from netai_chatbot.storage.database import Database
from netai_chatbot.storage.telemetry_store import TelemetryStore

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Container for shared application state."""

    settings: Settings
    db: Database
    llm_client: LLMClient
    conversation_store: ConversationStore
    telemetry_store: TelemetryStore
    telemetry_processor: TelemetryProcessor
    context_builder: ContextBuilder
    prompt_builder: PromptBuilder
    anomaly_detector: AnomalyDetector


# Global state — initialized during lifespan
app_state: AppState = None  # type: ignore[assignment]


async def _seed_sample_data(processor: TelemetryProcessor) -> None:
    """Load sample telemetry data if database is empty."""
    sample_file = (
        Path(__file__).resolve().parent.parent.parent
        / "data" / "sample" / "network_telemetry.json"
    )
    if not sample_file.exists():
        return

    with open(sample_file) as f:
        data = json.load(f)

    records = data.get("records", [])
    if records:
        count = await processor.ingest_perfsonar_json(records)
        logger.info("Seeded %d sample telemetry records", count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and clean up resources."""
    global app_state

    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.app_log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialize database
    db = Database(settings.db_path)
    await db.connect()
    logger.info("Database connected: %s", settings.db_path)

    # Initialize stores
    conversation_store = ConversationStore(db)
    telemetry_store = TelemetryStore(db)

    # Initialize LLM client
    llm_client = LLMClient(settings.llm)
    await llm_client.initialize()
    logger.info(
        "LLM client initialized (model=%s, mock=%s)",
        settings.llm.model,
        settings.llm.mock_mode,
    )

    # Initialize processors
    telemetry_processor = TelemetryProcessor(telemetry_store)
    context_builder = ContextBuilder(telemetry_store)
    prompt_builder = PromptBuilder()
    anomaly_detector = AnomalyDetector(telemetry_store)

    # Set global state
    app_state = AppState(
        settings=settings,
        db=db,
        llm_client=llm_client,
        conversation_store=conversation_store,
        telemetry_store=telemetry_store,
        telemetry_processor=telemetry_processor,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        anomaly_detector=anomaly_detector,
    )

    # Seed sample data if database is empty
    result = await db.fetch_one("SELECT COUNT(*) as cnt FROM telemetry_records")
    if result and result["cnt"] == 0:
        await _seed_sample_data(telemetry_processor)

    logger.info("NETAI Chatbot v%s started", __version__)
    yield

    # Cleanup
    await llm_client.close()
    await db.disconnect()
    logger.info("NETAI Chatbot shut down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="NETAI Chatbot",
        description=(
            "AI-powered Kubernetes-native chatbot for network diagnostics "
            "on the National Research Platform (NRP). Integrates with NRP's "
            "managed LLM service to provide intelligent network diagnostics assistance."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins + ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from netai_chatbot.api.routes import chat, diagnostics, health

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(diagnostics.router, prefix="/api/v1")

    # Also mount root health/info
    app.include_router(health.router)

    # Serve static files (web UI)
    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


# Application instance
app = create_app()


def run() -> None:
    """Run the application with uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "netai_chatbot.main:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.app_log_level,
        reload=True,
    )


if __name__ == "__main__":
    run()
