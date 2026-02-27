#!/usr/bin/env python3
"""Interactive CLI demo for NETAI Chatbot.

Run:
    python scripts/demo.py                  # mock mode (no API key)
    python scripts/demo.py --live           # uses .env config (GPT-4o etc.)
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000/api/v1"

DEMO_QUERIES = [
    "What is the current throughput between UCSD and Starlight?",
    "Are there any anomalies on the network right now?",
    "I'm seeing packet loss on the UCSD-Starlight path. What could be causing this?",
    "Explain the latency spike we observed earlier today.",
    "What remediation steps do you recommend for the throughput drop?",
]


def print_colored(text: str, color: str = "blue") -> None:
    colors = {"blue": "\033[94m", "green": "\033[92m", "yellow": "\033[93m",
              "red": "\033[91m", "bold": "\033[1m", "end": "\033[0m"}
    print(f"{colors.get(color, '')}{text}{colors['end']}")


async def check_server() -> bool:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{API_BASE}/health", timeout=3)
            data = r.json()
            print_colored(f"✓ Server healthy — v{data['version']}, "
                          f"{data['telemetry_records']} telemetry records, "
                          f"LLM: {'ready' if data['llm_available'] else 'unavailable'}", "green")
            return True
        except Exception:
            return False


async def chat(message: str, conversation_id: str | None = None) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        payload = {"message": message, "include_context": True}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        r = await client.post(f"{API_BASE}/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        return data["message"], data["conversation_id"]


async def show_anomalies() -> None:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/diagnostics/anomalies")
        anomalies = r.json()

    if not anomalies:
        print_colored("  ✓ No anomalies detected", "green")
        return

    for a in anomalies:
        severity_colors = {"critical": "red", "high": "red", "medium": "yellow", "low": "green"}
        color = severity_colors.get(a["severity"], "yellow")
        print_colored(f"  [{a['severity'].upper()}] {a['description']}", color)
        print(f"         {a['src_host']} → {a['dst_host']}")


async def run_guided_demo() -> None:
    """Run a guided demo with preset queries."""
    print_colored("\n╔══════════════════════════════════════════════════╗", "bold")
    print_colored("║     NETAI — Network Diagnostics Chatbot Demo    ║", "bold")
    print_colored("╚══════════════════════════════════════════════════╝\n", "bold")

    print_colored("Current Network Anomalies:", "yellow")
    await show_anomalies()
    print()

    conversation_id = None
    for i, query in enumerate(DEMO_QUERIES, 1):
        print_colored(f"[{i}/{len(DEMO_QUERIES)}] You: {query}", "blue")
        try:
            response, conversation_id = await chat(query, conversation_id)
            print_colored("NETAI:", "green")
            print(f"  {response}\n")
        except Exception as e:
            print_colored(f"  Error: {e}", "red")
            break


async def run_interactive() -> None:
    """Run an interactive chat session."""
    print_colored("\n🌐 NETAI Interactive Chat", "bold")
    print("   Type your questions about network performance, anomalies, or diagnostics.")
    print("   Commands: /anomalies, /hosts, /diagnose <src> <dst>, /quit\n")

    conversation_id = None
    while True:
        try:
            user_input = input("\033[94mYou: \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input in ("/quit", "/exit", "quit", "exit"):
            break

        if user_input == "/anomalies":
            await show_anomalies()
            continue

        if user_input == "/hosts":
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{API_BASE}/diagnostics/telemetry/hosts")
                for p in r.json()["host_pairs"]:
                    print(f"  {p['src_host']} → {p['dst_host']} ({p['metric_types']})")
            continue

        if user_input.startswith("/diagnose"):
            parts = user_input.split()
            if len(parts) != 3:
                print("  Usage: /diagnose <src_host> <dst_host>")
                continue
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(f"{API_BASE}/diagnostics/diagnose",
                                      json={"src_host": parts[1], "dst_host": parts[2]})
                data = r.json()
                print_colored("Diagnosis:", "green")
                print(f"  {data['diagnosis']}\n")
            continue

        try:
            response, conversation_id = await chat(user_input, conversation_id)
            print_colored("NETAI:", "green")
            print(f"  {response}\n")
        except Exception as e:
            print_colored(f"  Error: {e}", "red")

    print_colored("\nGoodbye!", "green")


async def main() -> None:
    if not await check_server():
        print_colored("✗ Server not running. Start it with:", "red")
        print("  make run")
        print("  # or: uvicorn netai_chatbot.main:app --reload")
        sys.exit(1)

    if "--guided" in sys.argv or len(sys.argv) == 1 or "--live" in sys.argv:
        await run_guided_demo()
        print_colored("─" * 50, "bold")
        print("Switching to interactive mode...\n")

    await run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
