"""Health check API routes."""

from __future__ import annotations

from fastapi import APIRouter

from netai_chatbot import __version__
from netai_chatbot.api.models import HealthResponse

router = APIRouter(tags=["health"])


def _get_app_state():
    from netai_chatbot.main import app_state
    return app_state


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health of the NETAI Chatbot service."""
    state = _get_app_state()

    # Check database
    db_ok = False
    telemetry_count = 0
    try:
        result = await state.db.fetch_one("SELECT COUNT(*) as cnt FROM telemetry_records")
        db_ok = True
        telemetry_count = result["cnt"] if result else 0
    except Exception:
        pass

    # Check LLM
    llm_ok = state.llm_client.settings.mock_mode or bool(state.llm_client.settings.api_key)

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version=__version__,
        llm_available=llm_ok,
        database_connected=db_ok,
        telemetry_records=telemetry_count,
    )


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "NETAI Chatbot",
        "version": __version__,
        "description": "AI-powered Kubernetes-native chatbot for network diagnostics",
        "docs": "/docs",
        "health": "/health",
    }
