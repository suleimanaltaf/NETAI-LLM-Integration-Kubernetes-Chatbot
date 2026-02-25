# Initial PoC for OSRE26 / NETAI Chatbot

Kubernetes-native micro Proof-of-Concept (PoC) for **NETAI: LLM Integration & Kubernetes Chatbot** (UC OSPO / GSoC 2026 context).

This project demonstrates a production-style backend that ingests network telemetry (mock perfSONAR/traceroute data), grounds a managed LLM request, and returns operator-friendly anomaly analysis through a FastAPI endpoint.

## Project Scope

- **Telemetry Source**: `data/mock_telemetry.json` with traceroute, latency, throughput, and anomaly summary.
- **API Layer**: FastAPI `/chat` endpoint that accepts operator queries.
- **LLM Integration**: Official `openai` Python SDK with configurable `OPENAI_BASE_URL` for managed non-OpenAI providers.
- **Containerization**: Lean Python 3.11 slim image with non-root runtime.
- **Kubernetes**: Stateless deployment, probes, resource constraints, and service exposure.

## Architecture Overview

1. Operator submits a question to `/chat`.
2. API loads telemetry context from `data/mock_telemetry.json`.
3. API builds a strict system prompt for network diagnostics.
4. Prompt + user query are sent to `gpt-4o` (or provider-compatible model).
5. API returns evidence-grounded diagnostics in structured markdown sections.

## Repository Layout

```text
.
├── data/
│   └── mock_telemetry.json
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── Dockerfile
├── main.py
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) installed
- Docker (for container workflow)
- Kubernetes cluster + `kubectl` (for deployment workflow)
- LLM API key compatible with the OpenAI SDK interface

## Local Setup (uv + FastAPI)

1. Create and activate a virtual environment:

```bash
uv venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
uv pip install -r requirements.txt
```

3. Set required environment variables:

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # override for managed OSS LLM endpoint
export OPENAI_MODEL="gpt-4o"
```

4. Run the API:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

5. Verify health:

```bash
curl -s http://localhost:8000/healthz | jq
```

## Test `/chat` Endpoint

```bash
curl -s -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why is the connection to k8s-worker-7 failing and what should I check first?"
  }' | jq
```

Expected behavior:
- Response contains a structured diagnostic answer with root-cause hypothesis, confidence, and actionable next checks tied to telemetry evidence.

## Docker Workflow

Build image:

```bash
docker build -t netai-chatbot-api:0.1.0 .
```

Run container:

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_BASE_URL="https://api.openai.com/v1" \
  -e OPENAI_MODEL="gpt-4o" \
  netai-chatbot-api:0.1.0
```

## Kubernetes Deployment

1. Create LLM secret:

```bash
kubectl create secret generic netai-llm-secret \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"
```

2. Deploy resources:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

3. Check rollout and service:

```bash
kubectl rollout status deployment/netai-chatbot-api
kubectl get pods -l app=netai-chatbot-api
kubectl get svc netai-chatbot-api
```

4. (Optional local test via port-forward):

```bash
kubectl port-forward svc/netai-chatbot-api 8000:80
curl -s http://localhost:8000/healthz | jq
```

## Notes for Future NETAI Expansion

- Replace static JSON with real perfSONAR/TSDB ingestion.
- Add retrieval layer for historical path anomalies.
- Introduce authn/authz and request-level audit logging.
- Route high-load inference requests to GPU-backed pods when self-hosting larger models.
