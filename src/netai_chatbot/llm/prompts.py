"""Prompt engineering templates for network diagnostics."""

from __future__ import annotations

from string import Template

# ── System Prompts ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_NETWORK_DIAGNOSTICS = """You are NETAI, an AI-powered network diagnostics assistant for the National Research Platform (NRP). You help network operators understand complex network behaviors, diagnose anomalies, and receive actionable recommendations.

## Your Capabilities
- Analyze perfSONAR throughput, latency, and packet loss measurements
- Interpret traceroute data to identify network path issues
- Detect and explain network anomalies in plain language
- Suggest remediation strategies for common network issues
- Correlate metrics across different measurement points

## Response Guidelines
- Be precise and technical but accessible
- Always reference specific metrics and data points when available
- Provide confidence levels for diagnoses (high/medium/low)
- Suggest specific next steps or commands for further investigation
- When data is insufficient, clearly state what additional information would help

## Network Context
You are operating within the NRP infrastructure, which spans multiple research institutions connected via high-speed backbone links. Common metrics include:
- Throughput: measured in Gbps, typical backbone links support 10-100 Gbps
- Latency (RTT): measured in milliseconds, varies by geographic distance
- Packet loss: measured as percentage, should be < 0.01% on healthy links
- Retransmits: TCP retransmission count, indicates congestion or errors
- Jitter: variation in latency, important for real-time applications"""

SYSTEM_PROMPT_WITH_CONTEXT = """${base_prompt}

## Current Network Telemetry Context
The following real-time data is available for this conversation:
${telemetry_context}

## Recent Anomalies
${anomaly_context}"""

# ── User Prompt Templates ────────────────────────────────────────────────────

DIAGNOSE_PATH_TEMPLATE = """Analyze the network path between ${src_host} and ${dst_host}.

Recent measurements:
${measurements}

Traceroute data:
${traceroute}

Please identify any issues and provide recommendations."""

EXPLAIN_ANOMALY_TEMPLATE = """Explain the following network anomaly detected at ${timestamp}:

Metric: ${metric_type}
Source: ${src_host}
Destination: ${dst_host}
Expected value: ${expected_value} ${unit}
Observed value: ${observed_value} ${unit}
Deviation: ${deviation_pct}% from baseline

Context: ${additional_context}

Provide a clear explanation and suggest remediation steps."""

SUMMARIZE_METRICS_TEMPLATE = """Summarize the network health for the following metrics collected over the past ${time_window}:

${metrics_summary}

Highlight any areas of concern and overall network health status."""

# ── Few-Shot Examples ────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = [
    {
        "user": "The throughput between UCSD and Starlight has dropped to 2 Gbps. What's going on?",
        "assistant": (
            "A throughput drop from the typical 9-10 Gbps baseline to 2 Gbps on the UCSD-Starlight "
            "path indicates a significant issue. Here's my analysis:\n\n"
            "**Likely Causes (in order of probability):**\n"
            "1. **Congestion at intermediate hop** (High confidence): The path traverses multiple "
            "backbone segments. A competing high-volume data transfer could be saturating a shared link.\n"
            "2. **MTU/MSS mismatch** (Medium confidence): If a router along the path recently changed "
            "its MTU settings, TCP performance can degrade significantly.\n"
            "3. **Optical signal degradation** (Low confidence): Fiber issues on one of the long-haul "
            "segments.\n\n"
            "**Recommended Next Steps:**\n"
            "1. Run `perfsonar traceroute` to check if the path has changed\n"
            "2. Check per-hop latency to identify the bottleneck segment\n"
            "3. Verify with `iperf3` using different TCP window sizes\n"
            "4. Contact NOC if the issue persists beyond 30 minutes"
        ),
    },
    {
        "user": "I'm seeing 5% packet loss on tests from TACC to NERSC. Is this normal?",
        "assistant": (
            "No, 5% packet loss is **not normal** for the TACC-NERSC path. The baseline for this "
            "link should be < 0.01% loss. This is a critical issue that needs immediate attention.\n\n"
            "**Analysis:**\n"
            "- **Severity: HIGH** — 5% loss will severely impact TCP throughput and application performance\n"
            "- The TACC-NERSC path typically goes through Internet2 backbone\n"
            "- This level of loss suggests either a hardware failure or severe congestion\n\n"
            "**Possible Causes:**\n"
            "1. Failing network interface or optic on an intermediate router\n"
            "2. Buffer overflow from a microburst or sustained congestion\n"
            "3. CRC errors from a damaged fiber patch cable\n\n"
            "**Immediate Actions:**\n"
            "1. Check if loss is unidirectional (NERSC→TACC as well)\n"
            "2. Run `mtr` for continuous path monitoring\n"
            "3. Escalate to Internet2 NOC with traceroute and loss data\n"
            "4. Check if other paths through the same backbone segment are affected"
        ),
    },
]


class PromptBuilder:
    """Builds context-aware prompts for the LLM."""

    def __init__(self) -> None:
        self._system_template = Template(SYSTEM_PROMPT_WITH_CONTEXT)
        self._diagnose_template = Template(DIAGNOSE_PATH_TEMPLATE)
        self._anomaly_template = Template(EXPLAIN_ANOMALY_TEMPLATE)
        self._summarize_template = Template(SUMMARIZE_METRICS_TEMPLATE)

    def build_system_prompt(
        self,
        telemetry_context: str = "No real-time telemetry data currently loaded.",
        anomaly_context: str = "No recent anomalies detected.",
    ) -> str:
        """Build the system prompt with optional context injection."""
        return self._system_template.safe_substitute(
            base_prompt=SYSTEM_PROMPT_NETWORK_DIAGNOSTICS,
            telemetry_context=telemetry_context,
            anomaly_context=anomaly_context,
        )

    def build_diagnose_prompt(
        self,
        src_host: str,
        dst_host: str,
        measurements: str,
        traceroute: str = "No traceroute data available.",
    ) -> str:
        """Build a path diagnosis prompt."""
        return self._diagnose_template.safe_substitute(
            src_host=src_host,
            dst_host=dst_host,
            measurements=measurements,
            traceroute=traceroute,
        )

    def build_anomaly_prompt(
        self,
        metric_type: str,
        src_host: str,
        dst_host: str,
        expected_value: float,
        observed_value: float,
        unit: str,
        timestamp: str = "now",
        additional_context: str = "",
    ) -> str:
        """Build an anomaly explanation prompt."""
        deviation = abs(observed_value - expected_value) / max(expected_value, 0.001) * 100
        return self._anomaly_template.safe_substitute(
            metric_type=metric_type,
            src_host=src_host,
            dst_host=dst_host,
            expected_value=expected_value,
            observed_value=observed_value,
            unit=unit,
            timestamp=timestamp,
            deviation_pct=f"{deviation:.1f}",
            additional_context=additional_context or "None",
        )

    def build_summary_prompt(
        self,
        metrics_summary: str,
        time_window: str = "24 hours",
    ) -> str:
        """Build a metrics summary prompt."""
        return self._summarize_template.safe_substitute(
            metrics_summary=metrics_summary,
            time_window=time_window,
        )

    def get_few_shot_messages(self) -> list[dict[str, str]]:
        """Return few-shot examples as message pairs."""
        messages = []
        for example in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": example["user"]})
            messages.append({"role": "assistant", "content": example["assistant"]})
        return messages
