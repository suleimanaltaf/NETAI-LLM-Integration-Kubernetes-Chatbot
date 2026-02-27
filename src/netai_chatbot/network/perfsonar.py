"""perfSONAR data integration module."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from netai_chatbot.config import PerfSONARSettings
from netai_chatbot.storage.telemetry_store import TelemetryStore

logger = logging.getLogger(__name__)


class PerfSONARClient:
    """Client for interacting with perfSONAR measurement archives."""

    def __init__(self, settings: PerfSONARSettings, store: TelemetryStore) -> None:
        self.settings = settings
        self.store = store
        self._http_client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        self._http_client = httpx.AsyncClient(
            base_url=self.settings.api_url,
            timeout=30.0,
        )

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()

    async def fetch_throughput(
        self, src: str | None = None, dst: str | None = None, hours: int = 24
    ) -> list[dict]:
        """Fetch throughput measurements from perfSONAR.

        In production, this queries the perfSONAR measurement archive.
        For the prototype, returns sample data if the API is unreachable.
        """
        try:
            if self._http_client:
                params = {"time-range": hours * 3600}
                if src:
                    params["source"] = src
                if dst:
                    params["destination"] = dst

                response = await self._http_client.get(
                    "/throughput", params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    return self._normalize_perfsonar_data(data, "throughput", "Gbps")
        except (httpx.HTTPError, Exception) as e:
            logger.warning("perfSONAR API unavailable: %s. Using cached data.", e)

        return []

    async def fetch_latency(
        self, src: str | None = None, dst: str | None = None, hours: int = 24
    ) -> list[dict]:
        """Fetch latency measurements from perfSONAR."""
        try:
            if self._http_client:
                params = {"time-range": hours * 3600}
                if src:
                    params["source"] = src
                if dst:
                    params["destination"] = dst

                response = await self._http_client.get("/latency", params=params)
                if response.status_code == 200:
                    data = response.json()
                    return self._normalize_perfsonar_data(data, "latency", "ms")
        except (httpx.HTTPError, Exception) as e:
            logger.warning("perfSONAR API unavailable: %s. Using cached data.", e)

        return []

    def _normalize_perfsonar_data(
        self, raw_data: list | dict, metric_type: str, unit: str
    ) -> list[dict]:
        """Normalize perfSONAR API response into our record format."""
        if isinstance(raw_data, dict):
            raw_data = raw_data.get("results", raw_data.get("data", []))

        records = []
        for item in raw_data:
            records.append({
                "source": "perfsonar",
                "metric_type": metric_type,
                "value": float(item.get("val", item.get("value", 0))),
                "unit": unit,
                "src_host": item.get("source", item.get("src")),
                "dst_host": item.get("destination", item.get("dst")),
                "metadata": {
                    "test_type": item.get("test_type", ""),
                    "tool": item.get("tool", ""),
                },
                "recorded_at": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
            })
        return records
