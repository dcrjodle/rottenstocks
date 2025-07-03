# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RottenStocks** is a stock rating platform that provides dual ratings (expert and popular opinion) similar to Rotten Tomatoes for movies. It analyzes social media sentiment to generate buy/sell recommendations.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite + Custom SASS/SCSS
- **Backend**: FastAPI (Python) + SQLAlchemy + PostgreSQL
- **AI/ML**: Google Gemini (gemini-1.5-flash) for sentiment analysis
- **External APIs**: Reddit, Alpha Vantage

## Development Commands

### Backend
```bash
# Start backend development server
cd backend && uvicorn app.main:app --reload

# Run backend tests
cd backend && pytest

# Run linting
cd backend && ruff check .
cd backend && ruff format .

# Database migrations
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"
```

### Frontend
```bash
# Start frontend development server
cd frontend && npm run dev

# Run frontend tests
cd frontend && npm test

# Build for production
cd frontend && npm run build

# Run linting
cd frontend && npm run lint
```

### Docker Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Makefile Commands
```bash
# Quick setup (recommended for new developers)
make setup

# Start development environment
make dev

# Run all tests
make test

# Health check all services
make health

# Install pre-commit hooks
make install-hooks

# Clean build artifacts
make clean
```

### Health Checks
```bash
# Comprehensive health check
python scripts/health-check.py --detailed

# Environment validation
python scripts/env-validator.py --check-optional
```

## Custom Claude Commands

### Phase Execution
To execute a specific implementation phase:
```
Please execute phase [PHASE_ID]
Example: Please execute phase P1.1
```

### Prompt Execution
To execute a specific prompt:
```
Please execute prompt [PROMPT_ID]
Example: Please execute prompt P1.1.1
```

### Status Check
To check implementation status:
```
Please check implementation status
```

### Run Tests
To run tests:
```
Please run tests for [backend|frontend|all]
```

## Implementation Phases Reference

- **P1**: Foundation & Documentation
  - P1.1: Documentation structure
  - P1.2: Development environment
- **P2**: Backend Foundation
  - P2.1: FastAPI setup
  - P2.2: Database setup
  - P2.3: Core API endpoints
- **P3**: External Integrations
  - P3.1: Stock data integration
  - P3.2: Social media integration
  - P3.3: AI sentiment analysis
- **P4**: Frontend Development
  - P4.1: React setup
  - P4.2: Design system
  - P4.3: Core features
- **P5**: Testing & Quality
  - P5.1: Backend testing
  - P5.2: Frontend testing
- **P6**: Production Ready
  - P6.1: Performance optimization
  - P6.2: Deployment setup

## Testing Strategy

1. Always run tests after implementing features
2. Backend: Use pytest with fixtures for database testing
3. Frontend: Use Jest and React Testing Library
4. Integration tests should use test databases

## Code Quality Standards

1. Python: Follow PEP 8, use type hints
2. TypeScript: Use strict mode, avoid any types
3. All code must pass linting before commit
4. Maintain test coverage above 80%