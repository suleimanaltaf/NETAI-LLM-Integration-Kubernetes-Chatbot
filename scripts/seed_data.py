"""Seed sample network telemetry data into the database."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from netai_chatbot.storage.database import Database
from netai_chatbot.storage.telemetry_store import TelemetryStore
from netai_chatbot.network.telemetry import TelemetryProcessor


async def main():
    """Seed the database with sample network telemetry data."""
    db_path = Path(__file__).resolve().parent.parent / "data" / "netai_chatbot.db"
    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample" / "network_telemetry.json"

    print(f"Database: {db_path}")
    print(f"Sample data: {sample_path}")

    db = Database(db_path)
    await db.connect()

    store = TelemetryStore(db)
    processor = TelemetryProcessor(store)

    # Check if already seeded
    result = await db.fetch_one("SELECT COUNT(*) as cnt FROM telemetry_records")
    if result and result["cnt"] > 0:
        print(f"Database already has {result['cnt']} records. Skipping seed.")
        await db.disconnect()
        return

    # Load and ingest sample data
    count = await processor.ingest_from_file(sample_path)
    print(f"Seeded {count} telemetry records")

    # Verify
    summary = await store.get_summary()
    print(f"\nTelemetry summary ({len(summary)} metric groups):")
    for s in summary:
        print(f"  {s['metric_type']} ({s['src_host']} → {s['dst_host']}): "
              f"avg={s['avg_value']} {s['unit']}")

    hosts = await store.get_host_pairs()
    print(f"\nMonitored host pairs: {len(hosts)}")
    for h in hosts:
        print(f"  {h['src_host']} → {h['dst_host']} ({h['metric_types']})")

    await db.disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
