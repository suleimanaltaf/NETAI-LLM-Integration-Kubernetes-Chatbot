# ── Build stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir build && \
    python -m build --wheel --outdir /build/dist

# ── Runtime stage ────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Anirudh <anirudh@example.com>"
LABEL description="NETAI Chatbot - AI-powered network diagnostics assistant for NRP"
LABEL org.opencontainers.image.source="https://github.com/anirudh/NETAI-LLM-Integration-Kubernetes-Chatbot"

# Security: run as non-root
RUN groupadd -r netai && useradd -r -g netai -m netai

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    httpx>=0.25.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    aiosqlite>=0.19.0 \
    jinja2>=3.1.0 \
    python-multipart>=0.0.6

# Install the application
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Copy application files
COPY src/ src/
COPY static/ static/
COPY data/ data/

# Create data directory for database
RUN mkdir -p /app/data && chown -R netai:netai /app

USER netai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENV PYTHONUNBUFFERED=1
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

CMD ["uvicorn", "netai_chatbot.main:app", "--host", "0.0.0.0", "--port", "8000"]
