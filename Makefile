.PHONY: help install install-dev test test-fast test-cov test-privacy lint format clean run build-dataset verify-anon start stop status

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Quick start/stop commands
start:  ## 🚀 Start all services (Docker)
	@./start-docker.sh

stop:  ## 🛑 Stop all services (Docker)
	@./stop-docker.sh

status:  ## 📊 Check services status
	@./status-docker.sh

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements.txt -r requirements-dev.txt

test:  ## Run all tests
	pytest tests/ -v

test-fast:  ## Run fast tests only (skip slow tests)
	pytest tests/ -v -m "not slow"

test-cov:  ## Run tests with coverage report
	pytest tests/ -v --cov=src --cov=api --cov=scripts --cov-report=html --cov-report=term

test-privacy:  ## Run privacy/anonymization tests only
	pytest tests/test_anonymization.py -v
	python3 scripts/verify_anonymization.py

test-api:  ## Run API integration tests
	pytest tests/test_api.py -v

test-vectorstore:  ## Run vectorstore tests
	pytest tests/test_vectorstore.py -v

lint:  ## Run code quality checks
	ruff check src/ api/ scripts/
	black --check src/ api/ scripts/
	isort --check-only src/ api/ scripts/

format:  ## Auto-format code
	black src/ api/ scripts/ tests/
	isort src/ api/ scripts/ tests/

security:  ## Run security scans
	bandit -r src/ api/ scripts/ --severity-level medium
	pip-audit

clean:  ## Clean temporary files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	rm -rf .ruff_cache .mypy_cache

run:  ## Start the FastAPI backend
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

build-dataset:  ## Build dataset from DICOM files
	python3 scripts/build_dataset.py

rebuild-dataset:  ## Rebuild dataset (clean + build)
	./rebuild_dataset.sh

verify-anon:  ## Verify dataset anonymization
	python3 scripts/verify_anonymization.py

start:  ## Full system startup (recommended)
	./start.sh

docker-qdrant:  ## Start Qdrant in Docker
	docker run -d -p 6333:6333 -v $$(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

ci-test:  ## Run tests as in CI
	pytest tests/ -v --cov=src --cov=api --cov-report=xml

pre-commit:  ## Run pre-commit checks (lint + test + privacy)
	@echo "Running pre-commit checks..."
	@$(MAKE) lint
	@$(MAKE) test-fast
	@$(MAKE) test-privacy
	@echo "✅ All pre-commit checks passed!"

# Docker commands
docker-build:  ## Build all Docker images
	docker-compose build

docker-build-api:  ## Build API Docker image
	docker build -f Dockerfile.api -t rag-healthcare-api:latest .

docker-build-streamlit:  ## Build Streamlit Docker image
	docker build -f Dockerfile.streamlit -t rag-healthcare-streamlit:latest .

docker-up:  ## Start all services with Docker Compose
	docker-compose up -d

docker-up-build:  ## Build and start all services
	docker-compose up -d --build

docker-down:  ## Stop all services
	docker-compose down

docker-logs:  ## Show logs from all services
	docker-compose logs -f

docker-logs-api:  ## Show API logs
	docker-compose logs -f api

docker-logs-streamlit:  ## Show Streamlit logs
	docker-compose logs -f streamlit

docker-ps:  ## Show running containers
	docker-compose ps

docker-clean:  ## Remove all containers, volumes, and images
	docker-compose down -v --rmi all

docker-dev:  ## Start services in development mode with hot reload
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-shell-api:  ## Open shell in API container
	docker-compose exec api /bin/bash

docker-shell-streamlit:  ## Open shell in Streamlit container
	docker-compose exec streamlit /bin/bash
