"""Network diagnostics API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from netai_chatbot.api.models import (
    AnomalyInfo,
    DiagnosePathRequest,
    DiagnosePathResponse,
    TelemetryQueryRequest,
)
from netai_chatbot.llm.client import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _get_app_state():
    from netai_chatbot.main import app_state
    return app_state


@router.post("/diagnose", response_model=DiagnosePathResponse)
async def diagnose_path(request: DiagnosePathRequest) -> DiagnosePathResponse:
    """Diagnose a network path between two hosts using AI analysis."""
    state = _get_app_state()

    # Get path metrics
    metrics_summary = await state.telemetry_processor.format_path_summary(
        request.src_host, request.dst_host
    )

    # Build diagnosis prompt
    diagnosis_prompt = state.prompt_builder.build_diagnose_prompt(
        src_host=request.src_host,
        dst_host=request.dst_host,
        measurements=metrics_summary,
    )

    # Get AI diagnosis
    system_prompt = state.prompt_builder.build_system_prompt()
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=diagnosis_prompt),
    ]

    try:
        response = await state.llm_client.chat(messages=messages)
        diagnosis = response.content
    except Exception as e:
        logger.error("Diagnosis failed: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")

    # Get anomalies for this path
    all_anomalies = await state.anomaly_detector.detect_anomalies()
    path_anomalies = [
        a.model_dump()
        for a in all_anomalies
        if a.src_host == request.src_host and a.dst_host == request.dst_host
    ]

    return DiagnosePathResponse(
        src_host=request.src_host,
        dst_host=request.dst_host,
        diagnosis=diagnosis,
        metrics_summary=metrics_summary,
        anomalies=path_anomalies,
    )


@router.post("/telemetry")
async def query_telemetry(request: TelemetryQueryRequest):
    """Query network telemetry records."""
    state = _get_app_state()
    records = await state.telemetry_store.query_recent(
        metric_type=request.metric_type,
        src_host=request.src_host,
        dst_host=request.dst_host,
        limit=request.limit,
    )
    return {"records": records, "count": len(records)}


@router.get("/telemetry/summary")
async def get_telemetry_summary(hours: int = 24):
    """Get aggregated telemetry summary."""
    state = _get_app_state()
    summary = await state.telemetry_store.get_summary(hours=hours)
    return {"summary": summary, "hours": hours}


@router.get("/telemetry/hosts")
async def get_monitored_hosts():
    """Get list of monitored host pairs."""
    state = _get_app_state()
    pairs = await state.telemetry_store.get_host_pairs()
    return {"host_pairs": pairs}


@router.get("/anomalies", response_model=list[AnomalyInfo])
async def get_anomalies(hours: int = 24):
    """Get currently detected network anomalies."""
    state = _get_app_state()
    anomalies = await state.anomaly_detector.detect_anomalies(hours=hours)
    return [AnomalyInfo(**a.model_dump()) for a in anomalies]


@router.get("/models")
async def list_available_models():
    """List available LLM models on the NRP platform."""
    state = _get_app_state()
    try:
        models = await state.llm_client.list_models()
        return {"models": models}
    except Exception as e:
        logger.error("Failed to list models: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")
