"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Chat Models ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str = Field(description="User message text", min_length=1, max_length=4096)
    conversation_id: str | None = Field(
        default=None, description="Existing conversation ID to continue"
    )
    model: str | None = Field(default=None, description="Override LLM model")
    include_context: bool = Field(
        default=True, description="Include network telemetry context"
    )


class ChatResponse(BaseModel):
    """Response body for the chat endpoint."""

    conversation_id: str
    message: str
    model: str
    usage: dict = Field(default_factory=dict)


class StreamChatRequest(BaseModel):
    """Request body for the streaming chat endpoint."""

    message: str = Field(min_length=1, max_length=4096)
    conversation_id: str | None = None
    model: str | None = None
    include_context: bool = True


class ConversationInfo(BaseModel):
    """Summary information about a conversation."""

    id: str
    title: str
    created_at: str
    updated_at: str


class MessageInfo(BaseModel):
    """A message within a conversation."""

    id: int
    role: str
    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: str


# ── Diagnostics Models ───────────────────────────────────────────────────────

class DiagnosePathRequest(BaseModel):
    """Request to diagnose a specific network path."""

    src_host: str
    dst_host: str


class DiagnosePathResponse(BaseModel):
    """Diagnostic result for a network path."""

    src_host: str
    dst_host: str
    diagnosis: str
    metrics_summary: str
    anomalies: list[dict] = Field(default_factory=list)


class TelemetryQueryRequest(BaseModel):
    """Query parameters for telemetry data."""

    metric_type: str | None = None
    src_host: str | None = None
    dst_host: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class AnomalyInfo(BaseModel):
    """Information about a detected anomaly."""

    id: str
    metric_type: str
    src_host: str
    dst_host: str
    expected_value: float
    observed_value: float
    unit: str
    severity: str
    description: str
    detected_at: str


# ── Health Models ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    llm_available: bool
    database_connected: bool
    telemetry_records: int = 0
