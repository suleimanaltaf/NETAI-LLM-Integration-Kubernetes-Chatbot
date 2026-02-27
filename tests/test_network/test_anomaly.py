"""Tests for anomaly detection."""

import pytest

from netai_chatbot.network.models import MetricType


@pytest.mark.asyncio
async def test_detect_no_anomalies_empty(anomaly_detector):
    """Should return empty list when no data exists."""
    anomalies = await anomaly_detector.detect_anomalies()
    assert anomalies == []


@pytest.mark.asyncio
async def test_detect_packet_loss_anomaly(anomaly_detector, telemetry_store):
    """Should detect packet loss anomaly."""
    # Inject data with packet loss
    for val in [0.0, 0.0, 0.0, 2.5]:
        await telemetry_store.ingest_record(
            source="perfsonar",
            metric_type="packet_loss",
            value=val,
            unit="%",
            src_host="hostA",
            dst_host="hostB",
        )

    anomalies = await anomaly_detector.detect_anomalies()
    loss_anomalies = [a for a in anomalies if a.metric_type == MetricType.PACKET_LOSS]
    assert len(loss_anomalies) > 0
    assert loss_anomalies[0].severity in ("medium", "high", "critical")


@pytest.mark.asyncio
async def test_detect_throughput_drop(anomaly_detector, telemetry_store):
    """Should detect throughput degradation."""
    for val in [9.4, 9.3, 9.5, 2.1]:
        await telemetry_store.ingest_record(
            source="perfsonar",
            metric_type="throughput",
            value=val,
            unit="Gbps",
            src_host="hostC",
            dst_host="hostD",
        )

    anomalies = await anomaly_detector.detect_anomalies()
    tp_anomalies = [a for a in anomalies if a.metric_type == MetricType.THROUGHPUT]
    assert len(tp_anomalies) > 0
    assert "dropped" in tp_anomalies[0].description.lower() or "throughput" in tp_anomalies[0].description.lower()


@pytest.mark.asyncio
async def test_detect_latency_spike(anomaly_detector, telemetry_store):
    """Should detect latency spike."""
    for val in [42.0, 42.5, 43.0, 42.0, 42.5, 150.0]:
        await telemetry_store.ingest_record(
            source="perfsonar",
            metric_type="latency",
            value=val,
            unit="ms",
            src_host="hostE",
            dst_host="hostF",
        )

    anomalies = await anomaly_detector.detect_anomalies()
    lat_anomalies = [a for a in anomalies if a.metric_type == MetricType.LATENCY]
    assert len(lat_anomalies) > 0


@pytest.mark.asyncio
async def test_no_false_positives(anomaly_detector, telemetry_store):
    """Should not flag healthy metrics as anomalies."""
    for val in [9.3, 9.4, 9.5, 9.4]:
        await telemetry_store.ingest_record(
            source="perfsonar",
            metric_type="throughput",
            value=val,
            unit="Gbps",
            src_host="healthy-A",
            dst_host="healthy-B",
        )

    anomalies = await anomaly_detector.detect_anomalies()
    healthy_anomalies = [
        a for a in anomalies
        if a.src_host == "healthy-A" and a.dst_host == "healthy-B"
    ]
    assert len(healthy_anomalies) == 0
