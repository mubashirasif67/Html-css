# Blessings Donation System - Makefile
# Provides convenient commands for development and deployment

.PHONY: help build up down seed test lint format clean logs shell

# Default target
help:
	@echo "Blessings Donation System - Available Commands:"
	@echo ""
	@echo "Development Commands:"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make seed      - Populate database with sample data"
	@echo "  make logs      - Show logs from all services"
	@echo "  make shell     - Open shell in backend container"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test      - Run all tests"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make coverage  - Run tests with coverage report"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  make lint      - Run linting checks"
	@echo "  make format    - Format code"
	@echo "  make type-check - Run type checking"
	@echo ""
	@echo "ML Commands:"
	@echo "  make train-models - Train ML models"
	@echo "  make generate-receipts - Generate synthetic receipt images"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  make clean     - Clean up containers and volumes"
	@echo "  make reset     - Complete reset (clean + rebuild)"

# Build all Docker images
build:
	@echo "Building Docker images..."
	docker-compose build --no-cache

# Start all services
up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started! Access points:"
	@echo "  - Public Pages: http://localhost"
	@echo "  - Admin Dashboard: http://localhost:3000"
	@echo "  - API Documentation: http://localhost:8000/docs"
	@echo "  - Celery Flower: http://localhost:5555"

# Stop all services
down:
	@echo "Stopping all services..."
	docker-compose down

# Populate database with sample data
seed:
	@echo "Seeding database with sample data..."
	docker-compose exec backend python scripts/data_generator.py
	docker-compose exec backend python scripts/seed_data.py
	docker-compose exec backend python scripts/generate_synthetic_receipts.py
	@echo "Database seeded successfully!"
	@echo "Sample data includes:"
	@echo "  - 200 employees with synthetic CNICs and addresses"
	@echo "  - 500 donations with various amounts and types"
	@echo "  - 100 synthetic receipt images for OCR testing"
	@echo "  - Admin user: admin@blessings.org / password: admin123"

# Run all tests
test:
	@echo "Running all tests..."
	docker-compose exec backend python -m pytest tests/ -v --tb=short

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	docker-compose exec backend python -m pytest tests/test_*.py -v -k "not integration"

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	docker-compose exec backend python -m pytest tests/test_integration.py -v

# Run tests with coverage
coverage:
	@echo "Running tests with coverage..."
	docker-compose exec backend python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in backend/htmlcov/"

# Run linting checks
lint:
	@echo "Running linting checks..."
	docker-compose exec backend flake8 app/ --max-line-length=88 --extend-ignore=E203,W503
	docker-compose exec backend black --check app/
	docker-compose exec backend isort --check-only app/

# Format code
format:
	@echo "Formatting code..."
	docker-compose exec backend black app/
	docker-compose exec backend isort app/

# Type checking
type-check:
	@echo "Running type checks..."
	docker-compose exec backend mypy app/ --ignore-missing-imports

# Train ML models
train-models:
	@echo "Training ML models..."
	docker-compose exec backend python scripts/train_eligibility.py
	docker-compose exec backend python scripts/train_fraud.py
	@echo "Models trained and saved to app/ml/models/"

# Generate synthetic receipt images
generate-receipts:
	@echo "Generating synthetic receipt images..."
	docker-compose exec backend python scripts/generate_synthetic_receipts.py
	@echo "Synthetic receipts generated in data/synthetic_receipts/"

# Show logs from all services
logs:
	docker-compose logs -f

# Show logs from specific service
logs-%:
	docker-compose logs -f $*

# Open shell in backend container
shell:
	docker-compose exec backend /bin/bash

# Open shell in specific container
shell-%:
	docker-compose exec $* /bin/bash

# Clean up containers and volumes
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Complete reset
reset: clean build up seed
	@echo "Complete reset completed!"

# Database operations
db-migrate:
	@echo "Running database migrations..."
	docker-compose exec backend alembic upgrade head

db-reset:
	@echo "Resetting database..."
	docker-compose exec backend alembic downgrade base
	docker-compose exec backend alembic upgrade head

# Development helpers
dev-install:
	@echo "Installing development dependencies..."
	pip install -r backend/requirements-dev.txt

dev-setup: build up seed train-models
	@echo "Development environment setup complete!"
	@echo "Run 'make logs' to monitor services"

# Production commands
prod-build:
	@echo "Building production images..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up:
	@echo "Starting production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Health checks
health:
	@echo "Checking service health..."
	@echo "Backend API:"
	@curl -f http://localhost:8000/health || echo "Backend not responding"
	@echo ""
	@echo "Admin Dashboard:"
	@curl -f http://localhost:3000 || echo "Admin not responding"
	@echo ""
	@echo "Database:"
	@docker-compose exec db mysqladmin ping -h localhost || echo "Database not responding"
	@echo ""
	@echo "Redis:"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"

# Backup and restore
backup:
	@echo "Creating database backup..."
	docker-compose exec db mysqldump -u blessings_user -pblessings_pass blessings > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

restore:
	@echo "Usage: make restore BACKUP_FILE=backup_20231201_120000.sql"
ifdef BACKUP_FILE
	docker-compose exec -T db mysql -u blessings_user -pblessings_pass blessings < $(BACKUP_FILE)
	@echo "Database restored from $(BACKUP_FILE)"
else
	@echo "Please specify BACKUP_FILE parameter"
endif