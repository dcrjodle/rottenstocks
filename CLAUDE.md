# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RottenStocks** is a stock rating platform that provides dual ratings (expert and popular opinion) similar to Rotten Tomatoes for movies. It analyzes social media sentiment to generate buy/sell recommendations.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite + Custom SASS/SCSS
- **Backend**: FastAPI (Python) + SQLAlchemy + PostgreSQL
- **AI/ML**: Google Gemini (gemini-1.5-flash) for sentiment analysis
- **External APIs**: Reddit, Alpha Vantage

## Python Environment

**IMPORTANT**: This project uses a virtual environment for Python dependencies. The virtual environment is located in the `backend/` directory and can only be used from there.

```bash
# Navigate to backend directory first
cd backend

# Activate virtual environment (REQUIRED for all Python commands)
source venv/bin/activate

# Deactivate when done
deactivate
```

## Development Commands

### Backend
```bash
# Navigate to backend directory and activate virtual environment
cd backend
source venv/bin/activate

# Start backend development server
uvicorn app.main:app --reload

# Run backend tests
pytest

# Run linting
ruff check .
ruff format .

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Run dev-tools (from backend directory)
python ../dev-tools/api_query_tool.py --help
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
# Navigate to backend directory and activate virtual environment
cd backend
source venv/bin/activate

# Comprehensive health check
python ../scripts/health-check.py --detailed

# Environment validation
python ../scripts/env-validator.py --check-optional
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

**CRITICAL REQUIREMENT**: For every major functionality implemented, comprehensive tests MUST be added before the feature is considered complete.

### Test Requirements
1. **Test Coverage**: Maintain test coverage above 80% for all code
2. **Test-First Approach**: Write tests for every new feature, API endpoint, database model, service, and utility function
3. **Test Types Required**:
   - Unit tests for all functions and methods
   - Integration tests for API endpoints
   - Database tests with proper fixtures and cleanup
   - Error handling and edge case tests
   - Security and validation tests

### Backend Testing Standards
1. Use pytest with fixtures for database testing
2. Test all API endpoints (success, error, edge cases)
3. Test database models, relationships, and constraints
4. Test authentication, authorization, and security features
5. Test external API integrations with mocking
6. Test background tasks and asynchronous operations
7. Integration tests should use test databases with proper isolation

### Frontend Testing Standards
1. Use Jest and React Testing Library
2. Test all components (rendering, interactions, state changes)
3. Test hooks and custom logic
4. Test API integration and error handling
5. Test user workflows and accessibility

### Test Implementation Rules
- **Before committing**: All new code must have corresponding tests
- **Before merging**: Test suite must pass with 80%+ coverage
- **Test organization**: Group related tests in logical modules
- **Test naming**: Use descriptive test names that explain the scenario
- **Mock external dependencies**: Use proper mocking for external APIs and services

## Code Quality Standards

1. Python: Follow PEP 8, use type hints
2. TypeScript: Use strict mode, avoid any types
3. All code must pass linting before commit
4. Maintain test coverage above 80%
5. **No feature is complete without comprehensive tests**

## Reporting and Documentation

When significant issues, implementation challenges, or architectural decisions are encountered, Claude should create detailed reports in the `docs/reports/` folder.

### Report Guidelines

1. **File Naming**: Use format `{topic}-{YYYY-MM-DD}.md`
   - Example: `database-testing-tools-issues-2025-07-04.md`

2. **Report Structure**:
   ```markdown
   # Title
   **Date**: Date  
   **Author**: Claude Code Assistant  
   **Context**: Brief context
   
   ## Overview
   ## Issues Encountered and Solutions
   ## Architecture Lessons
   ## Recommendations for Future Development
   ## Conclusion
   ```

3. **When to Create Reports**:
   - Complex debugging sessions with multiple issues
   - Architecture decisions and trade-offs
   - Performance analysis and optimization
   - Security issue analysis
   - Integration challenges with external systems
   - Tool development and process improvements

4. **Report Content Should Include**:
   - Root cause analysis of issues
   - Solutions attempted and their outcomes
   - Lessons learned and prevention strategies
   - Code examples and patterns
   - Performance observations
   - Security considerations
   - Recommendations for future development

These reports help maintain institutional knowledge and prevent similar issues in the future.