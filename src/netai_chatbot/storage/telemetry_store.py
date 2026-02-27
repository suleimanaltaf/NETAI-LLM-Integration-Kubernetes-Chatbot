"""Telemetry data storage operations."""

from __future__ import annotations

import json

from .database import Database


class TelemetryStore:
    """Manages network telemetry data persistence."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def ingest_record(
        self,
        source: str,
        metric_type: str,
        value: float,
        unit: str,
        src_host: str | None = None,
        dst_host: str | None = None,
        metadata: dict | None = None,
        recorded_at: str | None = None,
    ) -> int:
        """Ingest a single telemetry record. Returns record ID."""
        sql = """INSERT INTO telemetry_records
                 (source, metric_type, value, unit, src_host, dst_host, metadata, recorded_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))"""
        cursor = await self.db.execute(
            sql,
            (
                source,
                metric_type,
                value,
                unit,
                src_host,
                dst_host,
                json.dumps(metadata or {}),
                recorded_at,
            ),
        )
        return cursor.lastrowid  # type: ignore[return-value]

    async def ingest_batch(self, records: list[dict]) -> int:
        """Ingest multiple telemetry records. Returns count of inserted records."""
        count = 0
        for rec in records:
            await self.ingest_record(**rec)
            count += 1
        return count

    async def query_recent(
        self,
        metric_type: str | None = None,
        src_host: str | None = None,
        dst_host: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query recent telemetry records with optional filters."""
        conditions: list[str] = []
        params: list = []

        if metric_type:
            conditions.append("metric_type = ?")
            params.append(metric_type)
        if src_host:
            conditions.append("src_host = ?")
            params.append(src_host)
        if dst_host:
            conditions.append("dst_host = ?")
            params.append(dst_host)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        rows = await self.db.fetch_all(
            f"""SELECT id, source, metric_type, src_host, dst_host,
                       value, unit, metadata, recorded_at
                FROM telemetry_records {where}
                ORDER BY recorded_at DESC LIMIT ?""",
            tuple(params),
        )
        for row in rows:
            row["metadata"] = json.loads(row["metadata"])
        return rows

    async def get_summary(
        self,
        metric_type: str | None = None,
        hours: int = 24,
    ) -> list[dict]:
        """Get aggregated summary of telemetry data."""
        type_filter = "AND metric_type = ?" if metric_type else ""
        params: tuple = (hours,) if not metric_type else (hours, metric_type)

        return await self.db.fetch_all(
            f"""SELECT metric_type, unit, src_host, dst_host,
                       COUNT(*) as sample_count,
                       ROUND(AVG(value), 2) as avg_value,
                       ROUND(MIN(value), 2) as min_value,
                       ROUND(MAX(value), 2) as max_value,
                       ROUND(AVG(value) - 2 * (
                           CASE WHEN COUNT(*) > 1
                           THEN SQRT(SUM((value - (SELECT AVG(t2.value)
                               FROM telemetry_records t2
                               WHERE t2.metric_type = telemetry_records.metric_type))
                               * (value - (SELECT AVG(t3.value)
                               FROM telemetry_records t3
                               WHERE t3.metric_type = telemetry_records.metric_type))
                           ) / (COUNT(*) - 1))
                           ELSE 0 END
                       ), 2) as lower_bound
                FROM telemetry_records
                WHERE recorded_at >= datetime('now', '-' || ? || ' hours')
                {type_filter}
                GROUP BY metric_type, src_host, dst_host, unit
                ORDER BY metric_type, src_host""",
            params,
        )

    async def get_host_pairs(self) -> list[dict]:
        """Get unique source-destination host pairs with latest metrics."""
        return await self.db.fetch_all(
            """SELECT DISTINCT src_host, dst_host,
                      GROUP_CONCAT(DISTINCT metric_type) as metric_types,
                      MAX(recorded_at) as last_seen
               FROM telemetry_records
               WHERE src_host IS NOT NULL AND dst_host IS NOT NULL
               GROUP BY src_host, dst_host
               ORDER BY last_seen DESC"""
        )
