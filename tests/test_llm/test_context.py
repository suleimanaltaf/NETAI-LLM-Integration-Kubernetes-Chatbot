"""Tests for context builder."""

import pytest


@pytest.mark.asyncio
async def test_build_telemetry_context_empty(context_builder):
    """Should handle empty telemetry gracefully."""
    ctx = await context_builder.build_telemetry_context()
    assert "No telemetry data" in ctx


@pytest.mark.asyncio
async def test_build_telemetry_context_with_data(context_builder, seeded_telemetry_store):
    """Should build context string from telemetry data."""
    builder = context_builder
    builder.store = seeded_telemetry_store
    ctx = await builder.build_telemetry_context(metric_type="throughput")
    assert "throughput" in ctx or "Gbps" in ctx or "No telemetry" in ctx


@pytest.mark.asyncio
async def test_build_summary_context_empty(context_builder):
    """Should handle empty summary gracefully."""
    ctx = await context_builder.build_summary_context()
    assert "No telemetry summary" in ctx


@pytest.mark.asyncio
async def test_build_anomaly_context_empty(context_builder):
    """Should report no anomalies when data is clean."""
    ctx = await context_builder.build_anomaly_context()
    assert "No recent anomalies" in ctx


@pytest.mark.asyncio
async def test_build_full_context(context_builder):
    """Should return both telemetry and anomaly context."""
    telemetry_ctx, anomaly_ctx = await context_builder.build_full_context("test query")
    assert isinstance(telemetry_ctx, str)
    assert isinstance(anomaly_ctx, str)
