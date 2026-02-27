"""Network telemetry data handling and processing."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from netai_chatbot.network.models import MetricType
from netai_chatbot.storage.telemetry_store import TelemetryStore

logger = logging.getLogger(__name__)


class TelemetryProcessor:
    """Processes and ingests network telemetry data."""

    def __init__(self, store: TelemetryStore) -> None:
        self.store = store

    async def ingest_perfsonar_json(self, data: list[dict]) -> int:
        """Ingest perfSONAR measurement results from JSON format."""
        records = []
        for item in data:
            records.append({
                "source": "perfsonar",
                "metric_type": item.get("metric_type", "throughput"),
                "value": item["value"],
                "unit": item.get("unit", "Gbps"),
                "src_host": item.get("src_host"),
                "dst_host": item.get("dst_host"),
                "metadata": item.get("metadata", {}),
                "recorded_at": item.get("recorded_at"),
            })
        return await self.store.ingest_batch(records)

    async def ingest_from_file(self, filepath: str | Path) -> int:
        """Load and ingest telemetry data from a JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        if isinstance(data, dict) and "records" in data:
            data = data["records"]

        return await self.ingest_perfsonar_json(data)

    async def get_path_metrics(
        self, src_host: str, dst_host: str
    ) -> dict[str, list[dict]]:
        """Get all metrics for a specific network path."""
        result: dict[str, list[dict]] = {}
        for metric_type in MetricType:
            records = await self.store.query_recent(
                metric_type=metric_type.value,
                src_host=src_host,
                dst_host=dst_host,
                limit=50,
            )
            if records:
                result[metric_type.value] = records
        return result

    async def format_path_summary(self, src_host: str, dst_host: str) -> str:
        """Format a human-readable summary of path metrics."""
        metrics = await self.get_path_metrics(src_host, dst_host)

        if not metrics:
            return f"No metrics available for path {src_host} → {dst_host}"

        lines = [f"Network Path: {src_host} → {dst_host}", "=" * 50]

        for metric_type, records in metrics.items():
            values = [r["value"] for r in records]
            avg_val = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            unit = records[0]["unit"]

            lines.append(f"\n{metric_type.upper()}:")
            lines.append(f"  Average: {avg_val:.2f} {unit}")
            lines.append(f"  Min: {min_val:.2f} {unit}")
            lines.append(f"  Max: {max_val:.2f} {unit}")
            lines.append(f"  Samples: {len(values)}")

        return "\n".join(lines)
