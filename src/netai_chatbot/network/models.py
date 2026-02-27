"""Network telemetry data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    PACKET_LOSS = "packet_loss"
    RETRANSMITS = "retransmits"
    JITTER = "jitter"


class TelemetryRecord(BaseModel):
    """A single network telemetry measurement."""

    source: str = Field(description="Data source (e.g., 'perfsonar', 'traceroute')")
    metric_type: MetricType
    src_host: str | None = None
    dst_host: str | None = None
    value: float
    unit: str
    metadata: dict = Field(default_factory=dict)
    recorded_at: str | None = None


class TracerouteHop(BaseModel):
    """A single hop in a traceroute."""

    hop_number: int
    hostname: str | None = None
    ip_address: str
    rtt_ms: float | None = None
    asn: str | None = None


class TracerouteResult(BaseModel):
    """Complete traceroute result between two hosts."""

    src_host: str
    dst_host: str
    hops: list[TracerouteHop]
    timestamp: str
    total_hops: int = 0
    completed: bool = True

    def model_post_init(self, __context: object) -> None:
        if not self.total_hops:
            self.total_hops = len(self.hops)


class NetworkPathHealth(BaseModel):
    """Health assessment of a network path."""

    src_host: str
    dst_host: str
    status: str = Field(description="healthy, degraded, or critical")
    throughput_gbps: float | None = None
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    retransmits: int | None = None
    anomalies: list[str] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AnomalyReport(BaseModel):
    """A detected network anomaly."""

    id: str
    metric_type: MetricType
    src_host: str
    dst_host: str
    expected_value: float
    observed_value: float
    unit: str
    severity: str = Field(description="low, medium, high, critical")
    description: str
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False
