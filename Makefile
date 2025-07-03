# RottenStocks Makefile
# Convenient commands for development, testing, and deployment

.PHONY: help setup clean install test lint format run docker-up docker-down docker-logs docker-clean env-check env-create

# Default target
.DEFAULT_GOAL := help

# Colors for output
YELLOW := \033[1;33m
GREEN := \033[1;32m
RED := \033[1;31m
BLUE := \033[1;34m
NC := \033[0m

# Project configuration
PROJECT_NAME := rottenstocks
BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON := python3
NODE := node
NPM := npm

help: ## Show this help message
	@echo "$(BLUE)RottenStocks Development Commands$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(YELLOW)Setup Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(setup|install|env-)"
	@echo ""
	@echo "$(YELLOW)Development Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(run|dev|start)"
	@echo ""
	@echo "$(YELLOW)Testing Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(test|lint|format)"
	@echo ""
	@echo "$(YELLOW)Docker Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "docker-"
	@echo ""
	@echo "$(YELLOW)Database Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(db-|migrate|seed)"
	@echo ""
	@echo "$(YELLOW)Utility Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -v -E "(setup|install|env-|run|dev|start|test|lint|format|docker-|db-|migrate|seed)"

# =============================================================================
# Setup Commands
# =============================================================================

setup: ## Complete project setup (install dependencies, setup env, start services)
	@echo "$(BLUE)Setting up RottenStocks development environment...$(NC)"
	@$(MAKE) env-create
	@$(MAKE) docker-up
	@$(MAKE) install-backend
	@$(MAKE) install-frontend
	@$(MAKE) env-check
	@echo "$(GREEN)✓ Setup complete! Run 'make dev' to start development servers$(NC)"

env-create: ## Create .env file from .env.example
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env file from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env file created. Please edit it with your API keys$(NC)"; \
		echo "$(YELLOW)📝 Don't forget to add your API keys to .env!$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

env-check: ## Validate environment variables
	@echo "$(BLUE)Validating environment variables...$(NC)"
	@$(PYTHON) scripts/env-validator.py --check-optional

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend directory not found. Run Phase P2.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		$(PYTHON) -m venv venv && \
		. venv/bin/activate && \
		pip install --upgrade pip && \
		echo "$(YELLOW)Note: Installing minimal dependencies due to Python 3.13 compatibility$(NC)" && \
		pip install -r requirements-minimal.txt || \
		(echo "$(YELLOW)Falling back to individual package installation...$(NC)" && \
		pip install fastapi uvicorn python-dotenv structlog rich)
	@echo "$(GREEN)✓ Backend dependencies installed (minimal set)$(NC)"

install-frontend: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend directory not found. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

# =============================================================================
# Development Commands
# =============================================================================

dev: ## Start all development servers (requires 3 terminals)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@echo "$(YELLOW)This will start all services. You need 3 terminals:$(NC)"
	@echo "$(YELLOW)Terminal 1: make docker-up$(NC)"
	@echo "$(YELLOW)Terminal 2: make run-backend$(NC)" 
	@echo "$(YELLOW)Terminal 3: make run-frontend$(NC)"
	@echo ""
	@echo "$(GREEN)Starting Docker services...$(NC)"
	@$(MAKE) docker-up

run-backend: ## Start backend development server
	@echo "$(BLUE)Starting backend server...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Start frontend development server
	@echo "$(BLUE)Starting frontend server...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend not set up. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) run dev

start: dev ## Alias for dev

# =============================================================================
# Testing Commands
# =============================================================================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		pytest -v --cov=app --cov-report=term-missing

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend not set up. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) test

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running E2E tests...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend not set up. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) run test:e2e

lint: lint-backend lint-frontend ## Run linting for all code

lint-backend: ## Run backend linting
	@echo "$(BLUE)Linting backend code...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		ruff check .

lint-frontend: ## Run frontend linting
	@echo "$(BLUE)Linting frontend code...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend not set up. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) run lint

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend code...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		ruff format .

format-frontend: ## Format frontend code
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend not set up. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) run format

# =============================================================================
# Docker Commands
# =============================================================================

docker-up: ## Start Docker services (PostgreSQL, Redis, etc.)
	@echo "$(BLUE)Starting Docker services...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✓ Docker services started$(NC)"
	@$(MAKE) docker-status

docker-down: ## Stop Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✓ Docker services stopped$(NC)"

docker-restart: ## Restart Docker services
	@$(MAKE) docker-down
	@$(MAKE) docker-up

docker-logs: ## View Docker services logs
	@docker-compose logs -f

docker-status: ## Show Docker services status
	@echo "$(BLUE)Docker services status:$(NC)"
	@docker-compose ps

docker-clean: ## Clean Docker containers, volumes, and images
	@echo "$(YELLOW)⚠️  This will remove ALL Docker containers, volumes, and images$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or wait 10 seconds to continue...$(NC)"
	@sleep 10
	@echo "$(BLUE)Cleaning Docker environment...$(NC)"
	@docker-compose down -v --remove-orphans
	@docker system prune -af --volumes
	@echo "$(GREEN)✓ Docker environment cleaned$(NC)"

docker-build: ## Build Docker images for production
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
	@echo "$(GREEN)✓ Docker images built$(NC)"

# =============================================================================
# Database Commands
# =============================================================================

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.2 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		alembic upgrade head
	@echo "$(GREEN)✓ Database migrations completed$(NC)"

db-migration: ## Create new database migration
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)❌ Please provide a migration message: make db-migration MSG='your message'$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating new migration: $(MSG)$(NC)"
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✓ Migration created$(NC)"

db-seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database with sample data...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.2 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		$(PYTHON) -m app.scripts.seed_data
	@echo "$(GREEN)✓ Database seeded$(NC)"

db-reset: ## Reset database (drop and recreate)
	@echo "$(YELLOW)⚠️  This will DROP the entire database!$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or wait 5 seconds to continue...$(NC)"
	@sleep 5
	@echo "$(BLUE)Resetting database...$(NC)"
	@$(MAKE) docker-down
	@docker volume rm rottenstocks_postgres_data 2>/dev/null || true
	@$(MAKE) docker-up
	@sleep 10
	@$(MAKE) db-migrate
	@$(MAKE) db-seed
	@echo "$(GREEN)✓ Database reset completed$(NC)"

db-backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	@docker exec rottenstocks_postgres pg_dump -U postgres rottenstocks > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Database backup created in backups/$(NC)"

# =============================================================================
# Build Commands
# =============================================================================

build: build-backend build-frontend ## Build for production

build-backend: ## Build backend for production
	@echo "$(BLUE)Building backend for production...$(NC)"
	@if [ ! -d "$(BACKEND_DIR)" ]; then \
		echo "$(RED)❌ Backend not set up. Run Phase P2.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		. venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt
	@echo "$(GREEN)✓ Backend built$(NC)"

build-frontend: ## Build frontend for production
	@echo "$(BLUE)Building frontend for production...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)" ]; then \
		echo "$(RED)❌ Frontend not set up. Run Phase P4.1 first.$(NC)"; \
		exit 1; \
	fi
	@cd $(FRONTEND_DIR) && \
		$(NPM) run build
	@echo "$(GREEN)✓ Frontend built$(NC)"

# =============================================================================
# Utility Commands
# =============================================================================

clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Build artifacts cleaned$(NC)"

health: ## Check health of all services
	@echo "$(BLUE)Running comprehensive health check...$(NC)"
	@$(PYTHON) scripts/health-check.py --detailed

health-json: ## Check health of all services (JSON output)
	@$(PYTHON) scripts/health-check.py --json

health-quick: ## Quick health check of main services
	@echo "$(BLUE)Quick health check...$(NC)"
	@echo "$(YELLOW)Docker Services:$(NC)"
	@$(MAKE) docker-status
	@echo ""
	@echo "$(YELLOW)Backend API:$(NC)"
	@curl -f http://localhost:8000/health 2>/dev/null && echo "$(GREEN)✓ Backend: Healthy$(NC)" || echo "$(RED)❌ Backend: Not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Frontend:$(NC)"
	@curl -f http://localhost:5173 2>/dev/null && echo "$(GREEN)✓ Frontend: Healthy$(NC)" || echo "$(RED)❌ Frontend: Not responding$(NC)"

logs: ## View application logs
	@echo "$(BLUE)Application logs:$(NC)"
	@$(MAKE) docker-logs

deploy-local: ## Deploy locally for testing
	@echo "$(BLUE)Deploying locally...$(NC)"
	@$(MAKE) docker-down
	@$(MAKE) build
	@$(MAKE) docker-build
	@docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✓ Local deployment completed$(NC)"

# =============================================================================
# Git Hooks and Code Quality
# =============================================================================

install-hooks: ## Install Git pre-commit hooks
	@echo "$(BLUE)Installing Git hooks...$(NC)"
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "$(GREEN)✓ Git hooks installed$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  pre-commit not found. Installing...$(NC)"; \
		pip install pre-commit; \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "$(GREEN)✓ Git hooks installed$(NC)"; \
	fi

pre-commit: ## Run pre-commit on all files
	@echo "$(BLUE)Running pre-commit checks...$(NC)"
	@pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	@echo "$(BLUE)Updating pre-commit hooks...$(NC)"
	@pre-commit autoupdate

# =============================================================================
# Information Commands
# =============================================================================

info: ## Show project information
	@echo "$(BLUE)RottenStocks Project Information$(NC)"
	@echo "================================"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Backend: $(BACKEND_DIR)/"
	@echo "Frontend: $(FRONTEND_DIR)/"
	@echo "Python: $(shell $(PYTHON) --version 2>/dev/null || echo 'Not found')"
	@echo "Node: $(shell $(NODE) --version 2>/dev/null || echo 'Not found')"
	@echo "Docker: $(shell docker --version 2>/dev/null || echo 'Not found')"
	@echo ""
	@echo "URLs:"
	@echo "  Backend API: http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Adminer: http://localhost:8080"
	@echo "  PgAdmin: http://localhost:5050"

urls: ## Show all service URLs
	@echo "$(BLUE)Service URLs:$(NC)"
	@echo "🚀 Frontend:        http://localhost:5173"
	@echo "🔧 Backend API:     http://localhost:8000"
	@echo "📚 API Docs:        http://localhost:8000/docs"
	@echo "🗄️  Adminer:         http://localhost:8080"
	@echo "🐘 PgAdmin:         http://localhost:5050"
	@echo "🔴 Redis Commander: http://localhost:8081"

# Development shortcuts
backend: run-backend  ## Alias for run-backend
frontend: run-frontend  ## Alias for run-frontend
up: docker-up  ## Alias for docker-up
down: docker-down  ## Alias for docker-down
restart: docker-restart  ## Alias for docker-restart