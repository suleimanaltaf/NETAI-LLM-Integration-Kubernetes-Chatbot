"""Basic anomaly detection for network telemetry data."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from netai_chatbot.network.models import AnomalyReport, MetricType
from netai_chatbot.storage.telemetry_store import TelemetryStore

# Thresholds for anomaly detection
THRESHOLDS = {
    MetricType.THROUGHPUT: {"low_pct": 0.5, "unit": "Gbps"},
    MetricType.LATENCY: {"high_pct": 2.0, "unit": "ms"},
    MetricType.PACKET_LOSS: {"abs_high": 0.1, "unit": "%"},
    MetricType.RETRANSMITS: {"abs_high": 100, "unit": "count"},
    MetricType.JITTER: {"high_pct": 3.0, "unit": "ms"},
}


class AnomalyDetector:
    """Statistical anomaly detection for network metrics."""

    def __init__(self, store: TelemetryStore) -> None:
        self.store = store

    async def detect_anomalies(self, hours: int = 24) -> list[AnomalyReport]:
        """Run anomaly detection across all monitored paths."""
        summaries = await self.store.get_summary(hours=hours)
        anomalies: list[AnomalyReport] = []

        for summary in summaries:
            metric_type = summary["metric_type"]
            avg_value = summary["avg_value"]
            min_value = summary["min_value"]
            max_value = summary["max_value"]

            try:
                mt = MetricType(metric_type)
            except ValueError:
                continue

            threshold = THRESHOLDS.get(mt)
            if not threshold:
                continue

            detected = self._check_thresholds(
                mt, avg_value, min_value, max_value, threshold
            )

            for severity, desc, observed in detected:
                anomalies.append(
                    AnomalyReport(
                        id=str(uuid.uuid4()),
                        metric_type=mt,
                        src_host=summary["src_host"] or "unknown",
                        dst_host=summary["dst_host"] or "unknown",
                        expected_value=avg_value,
                        observed_value=observed,
                        unit=summary["unit"],
                        severity=severity,
                        description=desc,
                        detected_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

        return anomalies

    def _check_thresholds(
        self,
        metric_type: MetricType,
        avg: float,
        min_val: float,
        max_val: float,
        threshold: dict,
    ) -> list[tuple[str, str, float]]:
        """Check metric values against thresholds.

        Returns list of (severity, description, observed).
        """
        results = []

        if metric_type == MetricType.THROUGHPUT:
            # Throughput dropping below threshold
            if avg > 0 and min_val < avg * threshold["low_pct"]:
                severity = "critical" if min_val < avg * 0.25 else "high"
                results.append((
                    severity,
                    f"Throughput dropped to {min_val:.2f} Gbps "
                    f"(average: {avg:.2f} Gbps, {(1 - min_val/avg)*100:.0f}% below baseline)",
                    min_val,
                ))

        elif metric_type == MetricType.LATENCY:
            # Latency spike
            if avg > 0 and max_val > avg * threshold["high_pct"]:
                severity = "high" if max_val > avg * 3 else "medium"
                results.append((
                    severity,
                    f"Latency spike to {max_val:.2f} ms "
                    f"(average: {avg:.2f} ms, {(max_val/avg - 1)*100:.0f}% above baseline)",
                    max_val,
                ))

        elif metric_type == MetricType.PACKET_LOSS:
            # Any significant packet loss
            if max_val > threshold["abs_high"]:
                severity = "critical" if max_val > 1.0 else "high" if max_val > 0.5 else "medium"
                results.append((
                    severity,
                    f"Packet loss detected at {max_val:.2f}% (threshold: {threshold['abs_high']}%)",
                    max_val,
                ))

        elif metric_type == MetricType.RETRANSMITS:
            if max_val > threshold["abs_high"]:
                severity = "medium"
                results.append((
                    severity,
                    f"High TCP retransmits: {max_val:.0f} (threshold: {threshold['abs_high']})",
                    max_val,
                ))

        elif metric_type == MetricType.JITTER:
            if avg > 0 and max_val > avg * threshold["high_pct"]:
                severity = "medium"
                results.append((
                    severity,
                    f"Jitter spike to {max_val:.2f} ms (average: {avg:.2f} ms)",
                    max_val,
                ))

        return results

    async def get_active_anomalies(self, hours: int = 24) -> list[AnomalyReport]:
        """Get currently active (unresolved) anomalies."""
        return await self.detect_anomalies(hours=hours)
