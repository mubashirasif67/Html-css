# Makefile for Blessings FYP System

.PHONY: help build up down seed test lint clean logs shell migrate train

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker containers
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services are running!"
	@echo "Backend API: http://localhost:8000/docs"
	@echo "Frontend: http://localhost:8080"
	@echo "Admin Dashboard: http://localhost:3000"

down: ## Stop all services
	docker-compose down

seed: ## Seed database with sample data
	docker-compose exec backend python scripts/seed_data.py
	docker-compose exec backend python scripts/generate_receipts.py

test: ## Run all tests
	docker-compose exec backend pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	docker-compose exec backend pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests
	docker-compose exec backend pytest tests/test_integration.py -v

lint: ## Run linting and formatting checks
	docker-compose exec backend black app/ tests/ scripts/ --check
	docker-compose exec backend flake8 app/ tests/ scripts/
	docker-compose exec backend mypy app/

format: ## Format code with black
	docker-compose exec backend black app/ tests/ scripts/

clean: ## Clean up containers and volumes
	docker-compose down -v
	rm -rf backend/app/ml/models/*.joblib
	rm -rf backend/uploads/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

logs: ## Show logs for all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-celery: ## Show Celery worker logs
	docker-compose logs -f celery_worker

shell: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open MySQL shell
	docker-compose exec db mysql -u blessings_user -pblessings_pass blessings

migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"

train: ## Train ML models
	docker-compose exec backend python app/ml/train_eligibility.py
	docker-compose exec backend python app/ml/train_fraud.py

generate-data: ## Generate synthetic training data
	docker-compose exec backend python scripts/data_generator.py

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

dev: ## Start development environment with logs
	$(MAKE) build
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) seed
	$(MAKE) train
	$(MAKE) logs

prod-build: ## Build for production
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

health: ## Check health of all services
	@echo "Checking service health..."
	@docker-compose ps
	@echo "\nBackend health:"
	@curl -s http://localhost:8000/health || echo "Backend not responding"
	@echo "\n\nRedis health:"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"
	@echo "\nMySQL health:"
	@docker-compose exec db mysqladmin ping -h localhost -u root -prootpass123 || echo "MySQL not responding"