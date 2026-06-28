# ─── FinAI Platform Makefile ──────────────────────────────────────────────────
.PHONY: help install dev test lint format migrate seed docker-up docker-down clean

PYTHON   = python3
PIP      = pip3
APP      = app.main:app
UVICORN  = uvicorn $(APP) --reload --host 0.0.0.0 --port 8000
CELERY_W = celery -A app.workers.celery_app worker --loglevel=info
CELERY_B = celery -A app.workers.celery_app beat  --loglevel=info

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Installation ─────────────────────────────────────────────────────────────
install: ## Install all dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install dev dependencies (includes testing tools)
	$(PIP) install -r requirements.txt
	pre-commit install

# ─── Development ──────────────────────────────────────────────────────────────
dev: ## Run FastAPI in development mode (with hot-reload)
	cp -n .env.example .env 2>/dev/null || true
	$(UVICORN)

worker: ## Start Celery worker
	$(CELERY_W)

beat: ## Start Celery beat scheduler
	$(CELERY_B)

flower: ## Start Celery Flower monitoring (port 5555)
	celery -A app.workers.celery_app flower --port=5555

shell: ## Open Python shell with app context loaded
	$(PYTHON) -c "import asyncio; from app.config.settings import get_settings; s=get_settings(); print('Settings loaded:', s.app_name)"

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations (upgrade to head)
	alembic upgrade head

migrate-down: ## Rollback last Alembic migration
	alembic downgrade -1

migrate-gen: ## Generate a new migration (usage: make migrate-gen MSG="add_column")
	alembic revision --autogenerate -m "$(MSG)"

migrate-history: ## Show migration history
	alembic history --verbose

seed: ## Seed development database with demo data
	$(PYTHON) scripts/seed_data.py

db-reset: ## Drop and recreate the database (DESTRUCTIVE — dev only)
	alembic downgrade base
	alembic upgrade head
	$(PYTHON) scripts/seed_data.py

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run all tests with coverage
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html \
	       --cov-fail-under=70 -x

test-unit: ## Run only unit tests
	pytest tests/unit/ -v

test-api: ## Run only API integration tests
	pytest tests/api/ -v

test-integration: ## Run integration tests (requires running DB)
	pytest tests/integration/ -v

test-fast: ## Run tests without coverage (faster)
	pytest tests/ -v -x

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Run ruff linter
	ruff check app/ tests/

lint-fix: ## Auto-fix ruff violations
	ruff check --fix app/ tests/

format: ## Format code with black
	black app/ tests/ scripts/

format-check: ## Check formatting without modifying
	black --check app/ tests/

type-check: ## Run mypy type checker
	mypy app/ --ignore-missing-imports --no-strict-optional

security: ## Run bandit security scanner
	bandit -r app/ -ll

quality: lint format-check type-check security ## Run all quality checks

pre-commit: ## Run all pre-commit hooks manually
	pre-commit run --all-files

# ─── Docker ───────────────────────────────────────────────────────────────────
docker-build: ## Build all Docker images
	docker compose build

docker-up: ## Start all services (detached)
	docker compose up -d

docker-down: ## Stop and remove containers
	docker compose down

docker-restart: ## Restart the API service
	docker compose restart api

docker-logs: ## Tail logs for all services
	docker compose logs -f --tail=100

docker-logs-api: ## Tail API logs only
	docker compose logs -f api --tail=100

docker-shell: ## Open shell in API container
	docker compose exec api /bin/bash

docker-psql: ## Open psql in postgres container
	docker compose exec postgres psql -U finai_user -d finai_db

docker-neo4j: ## Open cypher-shell in Neo4j container
	docker compose exec neo4j cypher-shell -u neo4j -p password

docker-migrate: ## Run migrations inside Docker
	docker compose exec api alembic upgrade head

docker-seed: ## Seed data inside Docker
	docker compose exec api python scripts/seed_data.py

# ─── Monitoring ───────────────────────────────────────────────────────────────
metrics: ## Open Prometheus (port 9090)
	open http://localhost:9090 || xdg-open http://localhost:9090

grafana: ## Open Grafana (port 3000, admin/admin)
	open http://localhost:3000 || xdg-open http://localhost:3000

# ─── Cleanup ──────────────────────────────────────────────────────────────────
clean: ## Remove __pycache__, .pyc, coverage artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/ dist/ build/

clean-docker: ## Remove Docker volumes (DESTRUCTIVE)
	docker compose down -v --remove-orphans
