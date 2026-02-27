"""Tests for network telemetry processing."""

import pytest


@pytest.mark.asyncio
async def test_ingest_perfsonar_json(telemetry_processor, telemetry_store):
    """Should ingest perfSONAR format data."""
    data = [
        {
            "metric_type": "throughput",
            "src_host": "hostA",
            "dst_host": "hostB",
            "value": 9.4,
            "unit": "Gbps",
        },
        {
            "metric_type": "latency",
            "src_host": "hostA",
            "dst_host": "hostB",
            "value": 42.3,
            "unit": "ms",
        },
    ]
    count = await telemetry_processor.ingest_perfsonar_json(data)
    assert count == 2

    records = await telemetry_store.query_recent(src_host="hostA")
    assert len(records) == 2


@pytest.mark.asyncio
async def test_ingest_from_file(telemetry_processor, sample_data_path, telemetry_store):
    """Should load and ingest from JSON file."""
    if not sample_data_path.exists():
        pytest.skip("Sample data file not found")

    count = await telemetry_processor.ingest_from_file(sample_data_path)
    assert count > 0

    records = await telemetry_store.query_recent(limit=10)
    assert len(records) > 0


@pytest.mark.asyncio
async def test_get_path_metrics(telemetry_processor, telemetry_store):
    """Should retrieve metrics grouped by type for a path."""
    # Seed data
    await telemetry_processor.ingest_perfsonar_json([
        {"metric_type": "throughput", "src_host": "A", "dst_host": "B", "value": 9.0, "unit": "Gbps"},
        {"metric_type": "latency", "src_host": "A", "dst_host": "B", "value": 42.0, "unit": "ms"},
    ])

    metrics = await telemetry_processor.get_path_metrics("A", "B")
    assert "throughput" in metrics
    assert "latency" in metrics


@pytest.mark.asyncio
async def test_format_path_summary(telemetry_processor):
    """Should format a readable path summary."""
    await telemetry_processor.ingest_perfsonar_json([
        {"metric_type": "throughput", "src_host": "X", "dst_host": "Y", "value": 8.5, "unit": "Gbps"},
        {"metric_type": "throughput", "src_host": "X", "dst_host": "Y", "value": 9.2, "unit": "Gbps"},
    ])

    summary = await telemetry_processor.format_path_summary("X", "Y")
    assert "X" in summary
    assert "Y" in summary
    assert "THROUGHPUT" in summary


@pytest.mark.asyncio
async def test_format_path_summary_no_data(telemetry_processor):
    """Should handle missing path data."""
    summary = await telemetry_processor.format_path_summary("none", "none")
    assert "No metrics" in summary
