# RottenStocks Implementation Guide

This document outlines all implementation phases, sub-phases, and detailed prompts for building the RottenStocks platform.

## Phase 1: Foundation & Documentation [P1]

### P1.1 - Create Documentation Structure
**Goal**: Establish comprehensive documentation for the project.

#### P1.1.1 - Create docs folder and architecture.md ✓
**Status**: Completed

#### P1.1.2 - Create API specification document
**Prompts**:
1. "Create an OpenAPI 3.0 specification file (api-spec.yaml) in the docs folder that defines all REST endpoints, request/response schemas, and authentication methods"
2. "Generate example API requests and responses for each endpoint, including error cases"
3. "Add API versioning strategy and deprecation policy to the specification"

#### P1.1.3 - Create development guide
**Prompts**:
1. "Create a development-guide.md that explains local setup, coding standards, git workflow, and PR process"
2. "Add troubleshooting section with common issues and solutions"
3. "Include code style examples for Python and TypeScript with best practices"

### P1.2 - Setup Development Environment
**Goal**: Create a reproducible development environment.

#### P1.2.1 - Create docker-compose.yml for local services
**Prompts**:
1. "Create docker-compose.yml with PostgreSQL, Redis, and adminer services with proper networking and volumes"
2. "Add healthchecks and restart policies for all services"
3. "Create docker-compose.override.yml.example for local customization"

#### P1.2.2 - Setup environment variables structure
**Prompts**:
1. "Create .env.example file with all required environment variables documented"
2. "Create env-validator.py script that checks for missing required variables"
3. "Add environment-specific configs for development, testing, and production"

#### P1.2.3 - Create Makefile with common commands
**Prompts**:
1. "Create Makefile with targets for setup, test, lint, format, and run commands"
2. "Add database migration and seed data commands"
3. "Include docker cleanup and troubleshooting commands"

## Phase 2: Backend Foundation [P2]

### P2.1 - Initialize FastAPI Backend
**Goal**: Setup a scalable FastAPI application structure.

#### P2.1.1 - Create backend folder structure
**Prompts**:
1. "Create backend directory with proper Python package structure following clean architecture principles"
2. "Setup pyproject.toml with all dependencies and development tools configuration"
3. "Create __init__.py files and establish import structure"

#### P2.1.2 - Setup FastAPI with basic configuration
**Prompts**:
1. "Create main.py with FastAPI app initialization, including middleware and exception handlers"
2. "Implement health check and version endpoints with proper monitoring integration"
3. "Setup structured logging with correlation IDs and request tracking"

#### P2.1.3 - Configure CORS and middleware
**Prompts**:
1. "Configure CORS middleware with environment-specific allowed origins"
2. "Add request validation, rate limiting, and compression middleware"
3. "Implement custom middleware for request timing and error tracking"

### P2.2 - Database Setup
**Goal**: Implement robust database layer with SQLAlchemy.

#### P2.2.1 - Create database models
**Prompts**:
1. "Create SQLAlchemy models for Stock, Rating, Expert, and SocialPost with proper relationships"
2. "Add model mixins for timestamps, soft deletes, and audit fields"
3. "Implement model validation and custom properties"

#### P2.2.2 - Setup Alembic for migrations
**Prompts**:
1. "Initialize Alembic with proper configuration for async SQLAlchemy"
2. "Create custom migration template with safety checks"
3. "Add migration testing utilities and rollback procedures"

#### P2.2.3 - Create initial migration
**Prompts**:
1. "Generate and verify initial migration with all tables and indexes"
2. "Add database seed script with sample stocks and experts"
3. "Create migration documentation and naming conventions"

### P2.3 - Core API Endpoints
**Goal**: Implement RESTful API with best practices.

#### P2.3.1 - Implement stock CRUD endpoints
**Prompts**:
1. "Create stock router with GET, POST, PUT, DELETE endpoints using dependency injection"
2. "Implement stock search with full-text search and filtering"
3. "Add response caching and ETags for stock endpoints"

#### P2.3.2 - Implement rating endpoints
**Prompts**:
1. "Create rating endpoints with historical data and aggregations"
2. "Implement rating calculation service with expert vs popular scoring"
3. "Add WebSocket endpoint for real-time rating updates"

#### P2.3.3 - Add pagination and filtering
**Prompts**:
1. "Create reusable pagination dependency with cursor and offset strategies"
2. "Implement dynamic filtering with type-safe query parameters"
3. "Add sorting capabilities with multiple field support"

## Phase 3: External Integrations [P3]

### P3.1 - Stock Data Integration
**Goal**: Integrate real-time stock market data.

#### P3.1.1 - Integrate Alpha Vantage API
**Prompts**:
1. "Create Alpha Vantage client with rate limiting and retry logic"
2. "Implement data models for stock quotes, company info, and time series"
3. "Add comprehensive error handling for API failures"

#### P3.1.2 - Create stock data sync service
**Prompts**:
1. "Build background job to sync stock prices every 15 minutes during market hours"
2. "Implement incremental sync with change detection"
3. "Add monitoring and alerting for sync failures"

#### P3.1.3 - Implement caching strategy
**Prompts**:
1. "Setup Redis caching layer with TTL based on data volatility"
2. "Implement cache warming for frequently accessed stocks"
3. "Add cache invalidation on data updates"

### P3.2 - Social Media Integration
**Goal**: Aggregate social media data for sentiment analysis.

#### P3.2.1 - Setup Twitter API client
**Prompts**:
1. "Create Twitter API v2 client with OAuth 2.0 authentication"
2. "Implement filtered stream for stock symbol mentions"
3. "Add tweet enrichment with user metrics and engagement data"

#### P3.2.2 - Setup Reddit API client
**Prompts**:
1. "Create Reddit client focusing on finance subreddits"
2. "Implement post and comment collection with scoring"
3. "Add subreddit reputation scoring for quality filtering"

#### P3.2.3 - Create data aggregation service
**Prompts**:
1. "Build unified social media aggregator with deduplication"
2. "Implement expert account verification system"
3. "Create content quality scoring algorithm"

### P3.3 - AI Sentiment Analysis
**Goal**: Implement AI-powered sentiment analysis.

#### P3.3.1 - Integrate Google Gemini API
**Prompts**:
1. "Create Google Gemini client with gemini-1.5-flash model for sentiment analysis"
2. "Implement prompt engineering for financial sentiment analysis"
3. "Add response parsing and validation with error handling"

#### P3.3.2 - Create sentiment analysis service
**Prompts**:
1. "Build sentiment analyzer with batching for efficiency"
2. "Implement sentiment confidence scoring"
3. "Add sentiment explanation extraction"

#### P3.3.3 - Implement rating calculation algorithm
**Prompts**:
1. "Create weighted rating algorithm combining sentiment scores"
2. "Implement time decay for older social posts"
3. "Add anomaly detection for manipulation attempts"

## Phase 4: Frontend Development [P4]

### P4.1 - React Setup
**Goal**: Initialize modern React application.

#### P4.1.1 - Initialize React + Vite + TypeScript
**Prompts**:
1. "Create React app with Vite, TypeScript strict mode, and path aliases"
2. "Setup ESLint, Prettier, and husky for code quality"
3. "Configure absolute imports and module resolution"

#### P4.1.2 - Setup routing and state management
**Prompts**:
1. "Implement React Router v6 with lazy loading and auth guards"
2. "Setup Zustand stores for global state with TypeScript"
3. "Create persistent state management with localStorage sync"

#### P4.1.3 - Configure API client
**Prompts**:
1. "Setup Axios with interceptors for auth and error handling"
2. "Implement React Query for server state management"
3. "Create typed API hooks with automatic retries"

### P4.2 - Design System
**Goal**: Build consistent and accessible UI components.

#### P4.2.1 - Setup SASS and components
**Prompts**:
1. "Configure SASS/SCSS with custom theme structure and dark mode variables"
2. "Create modular SCSS architecture with BEM methodology"
3. "Setup component library structure with Storybook and SASS integration"

#### P4.2.2 - Create base UI components
**Prompts**:
1. "Build Button, Input, Card, and Modal components with variants"
2. "Create data display components: Table, List, Charts"
3. "Implement loading states, error boundaries, and empty states"

#### P4.2.3 - Implement responsive layout
**Prompts**:
1. "Create responsive navigation with mobile menu"
2. "Build adaptive grid system for different screen sizes"
3. "Implement touch gestures for mobile interactions"

### P4.3 - Core Features
**Goal**: Implement main application features.

#### P4.3.1 - Build stock list view
**Prompts**:
1. "Create stock list with virtual scrolling for performance"
2. "Implement real-time price updates with WebSocket"
3. "Add advanced filtering and search functionality"

#### P4.3.2 - Create stock detail page
**Prompts**:
1. "Build stock detail page with price chart and ratings"
2. "Implement rating breakdown with expert vs popular views"
3. "Add social sentiment feed with infinite scroll"

#### P4.3.3 - Implement search and filters
**Prompts**:
1. "Create autocomplete search with debouncing"
2. "Build advanced filter panel with saved filters"
3. "Implement URL-based state for shareable searches"

## Phase 5: Testing & Quality [P5]

### P5.1 - Backend Testing
**Goal**: Comprehensive backend test coverage.

#### P5.1.1 - Setup pytest and test structure
**Prompts**:
1. "Configure pytest with async support and fixtures"
2. "Create test database with automatic migrations"
3. "Setup test data factories with Factory Boy"

#### P5.1.2 - Write unit tests for services
**Prompts**:
1. "Create unit tests for all service layer functions with mocking"
2. "Test edge cases and error scenarios"
3. "Add performance benchmarks for critical paths"

#### P5.1.3 - Create integration tests
**Prompts**:
1. "Write API integration tests with full request/response cycle"
2. "Test external API integrations with VCR.py"
3. "Create end-to-end workflow tests"

### P5.2 - Frontend Testing
**Goal**: Reliable frontend test suite.

#### P5.2.1 - Setup Jest and React Testing Library
**Prompts**:
1. "Configure Jest with TypeScript and module mocking"
2. "Setup React Testing Library with custom renders"
3. "Add coverage reporting with thresholds"

#### P5.2.2 - Write component tests
**Prompts**:
1. "Create unit tests for all UI components"
2. "Test user interactions and state changes"
3. "Add accessibility tests with jest-axe"

#### P5.2.3 - Create E2E tests with Playwright
**Prompts**:
1. "Setup Playwright with page object pattern"
2. "Create E2E tests for critical user journeys"
3. "Add visual regression testing"

## Phase 6: Production Ready [P6]

### P6.1 - Performance Optimization
**Goal**: Optimize for production scale.

#### P6.1.1 - Implement API rate limiting
**Prompts**:
1. "Add Redis-based rate limiting with sliding window"
2. "Implement tiered rate limits for different user types"
3. "Create rate limit headers and documentation"

#### P6.1.2 - Add frontend lazy loading
**Prompts**:
1. "Implement code splitting for routes and components"
2. "Add lazy loading for images and heavy components"
3. "Optimize bundle size with tree shaking"

#### P6.1.3 - Optimize database queries
**Prompts**:
1. "Add database query analysis and optimization"
2. "Implement database connection pooling"
3. "Create materialized views for complex aggregations"

### P6.2 - Deployment Setup
**Goal**: Production-ready deployment pipeline.

#### P6.2.1 - Create production Dockerfiles
**Prompts**:
1. "Create multi-stage Dockerfiles for frontend and backend"
2. "Optimize image size and layer caching"
3. "Add security scanning to build process"

#### P6.2.2 - Setup CI/CD pipeline
**Prompts**:
1. "Create GitHub Actions workflow for testing and deployment"
2. "Add automated release process with semantic versioning"
3. "Implement blue-green deployment strategy"

#### P6.2.3 - Configure monitoring
**Prompts**:
1. "Setup application monitoring with Sentry"
2. "Add custom metrics with Prometheus"
3. "Create alerting rules and runbooks"

## Execution Commands

### To execute any phase:
```
Please execute phase [PHASE_ID]
Example: Please execute phase P2.1
```

### To execute any specific prompt:
```
Please execute prompt [PHASE_ID].[PROMPT_NUMBER]
Example: Please execute prompt P2.1.1
```

### To check status:
```
Please check implementation status
```

## Success Criteria

Each phase is considered complete when:
1. All sub-phases are implemented
2. Tests are passing
3. Documentation is updated
4. Code is reviewed and refactored
5. No critical issues remain

## Notes

- Always run tests after implementing features
- Update documentation as you go
- Follow the established patterns and conventions
- Ask for clarification if requirements are unclear