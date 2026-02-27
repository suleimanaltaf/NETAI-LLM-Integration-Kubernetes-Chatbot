# Architecture

## System Overview

NETAI Chatbot is a Kubernetes-native application that integrates with NRP's managed LLM service to provide intelligent network diagnostics assistance. The system follows a layered architecture with clear separation of concerns.

## Components

### API Layer (`api/`)
- **FastAPI** application with versioned REST endpoints
- Request/response validation via Pydantic models
- CORS middleware for cross-origin web UI access
- SSE (Server-Sent Events) for streaming chat responses

### LLM Integration Layer (`llm/`)
- **LLM Client**: OpenAI-compatible HTTP client supporting Qwen3-VL, GLM-4.7, GPT-OSS
- **Prompt Engine**: Domain-specific system prompts, few-shot examples, and template-based prompt construction
- **Context Builder**: RAG-style context injection from network telemetry data into LLM prompts

### Network Module (`network/`)
- **Telemetry Processor**: Ingests and normalizes perfSONAR measurement data
- **perfSONAR Client**: Fetches real-time data from perfSONAR measurement archives
- **Anomaly Detector**: Statistical anomaly detection using threshold-based analysis on metric summaries

### Storage Layer (`storage/`)
- **Database**: Async SQLite with WAL mode for concurrent read/write
- **Conversation Store**: CRUD operations for multi-turn chat conversations
- **Telemetry Store**: Time-series storage with aggregation queries

### Fine-Tuning Pipeline (`fine_tuning/`)
- **Data Preparation**: Converts network diagnostics conversations to training format
- **Training**: LoRA-based fine-tuning using 4-bit quantization for memory efficiency

## Data Flow

1. User sends a message via Web UI or API
2. Context Builder queries telemetry database for relevant network data
3. Prompt Engine constructs a context-aware system prompt with few-shot examples
4. LLM Client sends the prompt + conversation history to NRP's LLM service
5. Response is stored in conversation history and returned to the user
6. Anomaly Detector periodically scans telemetry for issues

## Deployment Architecture

### Standard Deployment (API-only)
- 2 replicas behind a ClusterIP Service
- Uses NRP managed LLM API for inference
- Minimal resource requirements (256Mi–512Mi RAM)

### GPU Deployment (Local Inference)
- Single replica with NVIDIA GPU (A100/A40)
- Runs fine-tuned model locally for low-latency inference
- 8–16Gi RAM, 1 GPU
- Model weights cached on persistent volume (50Gi)
