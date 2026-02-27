"""LLM API client supporting NRP managed models (OpenAI-compatible)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from netai_chatbot.config import LLMSettings

logger = logging.getLogger(__name__)

MOCK_RESPONSES = {
    "throughput": (
        "Based on the network telemetry data, the throughput between the specified hosts "
        "has been averaging {value} Gbps over the last 24 hours. This is within normal "
        "operating parameters for NRP backbone links. The slight variation you see is "
        "typical of shared research network infrastructure during peak usage hours."
    ),
    "latency": (
        "The latency measurements show an average round-trip time of {value} ms between "
        "the endpoints. I've checked the traceroute data and the path traverses {hops} hops "
        "through the NRP backbone. The latency is consistent with the geographic distance "
        "and current network conditions."
    ),
    "anomaly": (
        "I've detected a potential anomaly in the network path. The packet loss rate has "
        "increased to {value}% which exceeds the baseline threshold of 0.1%. This could "
        "indicate congestion at an intermediate router or a failing optical link. "
        "I recommend running a targeted traceroute to isolate the affected segment."
    ),
    "default": (
        "I'm the NETAI network diagnostics assistant. I can help you analyze network "
        "performance metrics from perfSONAR, diagnose anomalies, interpret traceroute data, "
        "and suggest remediation strategies. What would you like to know about your "
        "network infrastructure?"
    ),
}


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: str  # 'system', 'user', 'assistant'
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """Response from the LLM service."""

    content: str
    model: str
    usage: dict = field(default_factory=dict)
    finish_reason: str = "stop"


class LLMClient:
    """Client for NRP's managed LLM service (OpenAI-compatible API)."""

    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        self._http_client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        self._http_client = httpx.AsyncClient(
            base_url=self.settings.api_base_url,
            headers=headers,
            timeout=self.settings.timeout,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            raise RuntimeError("LLMClient not initialized. Call initialize() first.")
        return self._http_client

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a chat completion request to the LLM service."""
        if self.settings.mock_mode:
            return self._mock_response(messages)

        payload = {
            "model": model or self.settings.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.settings.temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
        }

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", payload["model"]),
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "stop"),
            )
        except httpx.HTTPStatusError as e:
            logger.error("LLM API error: %s %s", e.response.status_code, e.response.text)
            raise
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            raise

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response."""
        if self.settings.mock_mode:
            resp = self._mock_response(messages)
            for word in resp.content.split():
                yield word + " "
            return

        payload = {
            "model": model or self.settings.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.settings.temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "stream": True,
        }

        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def list_models(self) -> list[dict]:
        """List available models from the LLM service."""
        if self.settings.mock_mode:
            return [
                {"id": "gpt-4o", "object": "model"},
                {"id": "qwen3-vl", "object": "model"},
                {"id": "glm-4.7", "object": "model"},
                {"id": "gpt-oss", "object": "model"},
            ]

        response = await self.client.get("/models")
        response.raise_for_status()
        return response.json().get("data", [])

    def _mock_response(self, messages: list[ChatMessage]) -> LLMResponse:
        """Generate a mock response for testing without an LLM API."""
        user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                user_msg = m.content.lower()
                break

        # Select contextual mock response
        if any(w in user_msg for w in ["throughput", "bandwidth", "speed", "gbps"]):
            content = MOCK_RESPONSES["throughput"].format(value="9.4")
        elif any(w in user_msg for w in ["latency", "delay", "rtt", "ping"]):
            content = MOCK_RESPONSES["latency"].format(value="12.3", hops="7")
        elif any(w in user_msg for w in ["anomaly", "issue", "problem", "error", "loss", "drop"]):
            content = MOCK_RESPONSES["anomaly"].format(value="2.3")
        else:
            content = MOCK_RESPONSES["default"]

        return LLMResponse(
            content=content,
            model="mock-model",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        )
