"""Tests for prompt engineering module."""


from netai_chatbot.llm.prompts import (
    SYSTEM_PROMPT_NETWORK_DIAGNOSTICS,
)


def test_system_prompt_contains_key_info():
    """System prompt should contain essential context."""
    assert "NETAI" in SYSTEM_PROMPT_NETWORK_DIAGNOSTICS
    assert "National Research Platform" in SYSTEM_PROMPT_NETWORK_DIAGNOSTICS
    assert "perfSONAR" in SYSTEM_PROMPT_NETWORK_DIAGNOSTICS
    assert "throughput" in SYSTEM_PROMPT_NETWORK_DIAGNOSTICS.lower()


def test_build_system_prompt_default(prompt_builder):
    """Default system prompt should include base prompt."""
    prompt = prompt_builder.build_system_prompt()
    assert "NETAI" in prompt
    assert "No real-time telemetry" in prompt


def test_build_system_prompt_with_context(prompt_builder):
    """System prompt should inject provided context."""
    prompt = prompt_builder.build_system_prompt(
        telemetry_context="Throughput: 9.4 Gbps",
        anomaly_context="Packet loss detected on UCSD path",
    )
    assert "9.4 Gbps" in prompt
    assert "Packet loss detected" in prompt


def test_build_diagnose_prompt(prompt_builder):
    """Diagnose prompt should include path details."""
    prompt = prompt_builder.build_diagnose_prompt(
        src_host="perfsonar-ucsd.nrp.ai",
        dst_host="perfsonar-starlight.nrp.ai",
        measurements="Throughput: 3.2 Gbps (avg: 9.4 Gbps)",
    )
    assert "perfsonar-ucsd" in prompt
    assert "perfsonar-starlight" in prompt
    assert "3.2 Gbps" in prompt


def test_build_anomaly_prompt(prompt_builder):
    """Anomaly prompt should calculate deviation."""
    prompt = prompt_builder.build_anomaly_prompt(
        metric_type="throughput",
        src_host="hostA",
        dst_host="hostB",
        expected_value=9.4,
        observed_value=3.2,
        unit="Gbps",
    )
    assert "throughput" in prompt
    assert "hostA" in prompt
    assert "9.4" in prompt
    assert "3.2" in prompt
    assert "%" in prompt  # deviation percentage


def test_build_summary_prompt(prompt_builder):
    """Summary prompt should include metrics and time window."""
    prompt = prompt_builder.build_summary_prompt(
        metrics_summary="5 paths monitored, 2 anomalies detected",
        time_window="12 hours",
    )
    assert "5 paths" in prompt
    assert "12 hours" in prompt


def test_few_shot_examples(prompt_builder):
    """Should return properly formatted few-shot examples."""
    examples = prompt_builder.get_few_shot_messages()
    assert len(examples) >= 4  # At least 2 user-assistant pairs
    assert examples[0]["role"] == "user"
    assert examples[1]["role"] == "assistant"
