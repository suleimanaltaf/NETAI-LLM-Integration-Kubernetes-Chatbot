"""Context builder for RAG-style network diagnostics responses."""

from __future__ import annotations

from netai_chatbot.storage.telemetry_store import TelemetryStore


class ContextBuilder:
    """Builds context strings from network telemetry for prompt injection."""

    def __init__(self, telemetry_store: TelemetryStore) -> None:
        self.store = telemetry_store

    async def build_telemetry_context(
        self,
        metric_type: str | None = None,
        src_host: str | None = None,
        dst_host: str | None = None,
        limit: int = 20,
    ) -> str:
        """Build a telemetry context string from recent data."""
        records = await self.store.query_recent(
            metric_type=metric_type,
            src_host=src_host,
            dst_host=dst_host,
            limit=limit,
        )

        if not records:
            return "No telemetry data available for the specified criteria."

        lines = []
        for rec in records:
            line = (
                f"- [{rec['recorded_at']}] {rec['metric_type']}: "
                f"{rec['src_host']} → {rec['dst_host']} = "
                f"{rec['value']} {rec['unit']}"
            )
            lines.append(line)

        return "\n".join(lines)

    async def build_summary_context(self, hours: int = 24) -> str:
        """Build a summary context from aggregated telemetry data."""
        summaries = await self.store.get_summary(hours=hours)

        if not summaries:
            return "No telemetry summary available."

        lines = []
        for s in summaries:
            line = (
                f"- {s['metric_type']} ({s['src_host']} → {s['dst_host']}): "
                f"avg={s['avg_value']} {s['unit']}, "
                f"min={s['min_value']}, max={s['max_value']}, "
                f"samples={s['sample_count']}"
            )
            lines.append(line)

        return "\n".join(lines)

    async def build_anomaly_context(self, hours: int = 24) -> str:
        """Build context highlighting anomalies from recent data."""
        summaries = await self.store.get_summary(hours=hours)

        anomalies = []
        for s in summaries:
            # Flag anomalies: values significantly different from average
            if s["sample_count"] < 3:
                continue

            avg = s["avg_value"]
            min_val = s["min_value"]
            max_val = s["max_value"]

            # Check for high variance indicating anomalies
            if avg > 0 and (max_val - min_val) / avg > 0.5:
                anomalies.append(
                    f"⚠ {s['metric_type']} ({s['src_host']} → {s['dst_host']}): "
                    f"High variance detected — range [{min_val}, {max_val}] {s['unit']} "
                    f"(avg: {avg})"
                )

            # Check for concerning absolute values
            if s["metric_type"] == "packet_loss" and s["max_value"] > 0.1:
                anomalies.append(
                    f"🔴 Packet loss alert: {s['src_host']} → {s['dst_host']} "
                    f"peaked at {s['max_value']}%"
                )

            if s["metric_type"] == "throughput" and s["min_value"] < avg * 0.5:
                anomalies.append(
                    f"🟡 Throughput degradation: {s['src_host']} → {s['dst_host']} "
                    f"dropped to {s['min_value']} {s['unit']} (avg: {avg})"
                )

        return "\n".join(anomalies) if anomalies else "No recent anomalies detected."

    async def build_full_context(
        self,
        user_message: str,
        hours: int = 24,
    ) -> tuple[str, str]:
        """Build complete telemetry and anomaly context for a user query.

        Returns (telemetry_context, anomaly_context) tuple.
        """
        # Extract host mentions from user message for targeted context
        telemetry_ctx = await self.build_summary_context(hours=hours)
        anomaly_ctx = await self.build_anomaly_context(hours=hours)

        return telemetry_ctx, anomaly_ctx
