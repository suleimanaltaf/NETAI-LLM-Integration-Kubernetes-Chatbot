.PHONY: install dev test lint run run-gpt4o demo docker-build docker-up clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ -v --cov=netai_chatbot --cov-report=term-missing

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

run:
	LLM_MOCK_MODE=true uvicorn netai_chatbot.main:app --reload --port 8000

run-gpt4o:
	@echo "Starting with GPT-4o (ensure LLM_API_KEY is set in .env)..."
	LLM_MOCK_MODE=false uvicorn netai_chatbot.main:app --reload --port 8000

demo:
	@echo "Starting server in background..."
	@LLM_MOCK_MODE=true uvicorn netai_chatbot.main:app --port 8000 > /dev/null 2>&1 & echo $$! > /tmp/netai-demo.pid
	@sleep 2
	@python scripts/demo.py || true
	@kill $$(cat /tmp/netai-demo.pid) 2>/dev/null; rm -f /tmp/netai-demo.pid

seed:
	python scripts/seed_data.py

docker-build:
	docker build -t netai-chatbot:latest .

docker-up:
	docker compose up --build

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov build dist *.egg-info data/*.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
