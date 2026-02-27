# Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run
```bash
# Mock mode (no API key needed)
LLM_MOCK_MODE=true uvicorn netai_chatbot.main:app --reload --port 8000
```

### Configuration
Copy `.env.example` to `.env` and set your values:
```bash
cp .env.example .env
# Edit .env with your LLM API key and settings
```

## Docker Deployment

### Build
```bash
docker build -t netai-chatbot:latest .
```

### Run
```bash
docker run -p 8000:8000 \
  -e LLM_MOCK_MODE=true \
  -v netai-data:/app/data \
  netai-chatbot:latest
```

### Docker Compose
```bash
# Default (mock mode)
docker compose up -d

# With live LLM
LLM_API_KEY=your-key docker compose --profile live up -d
```

## Kubernetes Deployment

### Prerequisites
- Access to an NRP Kubernetes cluster
- `kubectl` configured for the cluster
- Container image pushed to a registry

### Deploy

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Configure secrets (edit with your API key first)
kubectl apply -f k8s/configmap.yaml

# 3. Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 4. (Optional) Enable ingress
kubectl apply -f k8s/ingress.yaml

# 5. (Optional) GPU-enabled deployment for local inference
kubectl apply -f k8s/gpu-deployment.yaml
```

### Verify
```bash
kubectl -n netai get pods
kubectl -n netai get svc
kubectl -n netai logs -f deployment/netai-chatbot
```

### Port Forward (for testing)
```bash
kubectl -n netai port-forward svc/netai-chatbot 8000:80
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE_URL` | `https://llm.nrp-nautilus.io/v1` | NRP LLM service endpoint |
| `LLM_API_KEY` | (empty) | API key for LLM service |
| `LLM_MODEL` | `qwen3-vl` | Default model (qwen3-vl, glm-4.7, gpt-oss) |
| `LLM_MOCK_MODE` | `true` | Use mock responses (no API needed) |
| `APP_HOST` | `0.0.0.0` | Server bind address |
| `APP_PORT` | `8000` | Server port |
| `APP_LOG_LEVEL` | `info` | Log level (debug, info, warning, error) |
| `DATABASE_URL` | `sqlite:///data/netai_chatbot.db` | SQLite database path |
| `PERFSONAR_API_URL` | `https://ps-dashboard.nrp.ai/api` | perfSONAR API endpoint |
