# RottenStocks Backend

FastAPI-based backend for the RottenStocks stock sentiment analysis platform.

## 🏗️ Architecture

This backend follows clean architecture principles with clear separation of concerns:

- **`app/api/`** - FastAPI routes and endpoint handlers
- **`app/core/`** - Core functionality (config, security, logging)
- **`app/db/`** - Database models and repositories
- **`app/schemas/`** - Pydantic models for validation
- **`app/services/`** - Business logic layer
- **`app/tasks/`** - Background tasks and Celery workers
- **`app/utils/`** - Utility functions and helpers

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (via Docker)
- Redis (via Docker)

### Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Environment configuration:**
   ```bash
   # Copy environment template from project root
   cp ../.env.example ../.env
   # Edit .env with your API keys
   ```

4. **Start services:**
   ```bash
   # From project root
   docker-compose up -d
   ```

5. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

## 🔧 Development

### Running the Server

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the script
python -m app.main
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run tests matching pattern
pytest -k "test_health"
```

### Code Quality

```bash
# Lint code
ruff check .

# Format code
ruff format .

# Type checking
mypy app/

# Security scan
bandit -r app/
```

## 📚 API Documentation

When running in development mode, API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🏥 Health Checks

The backend provides health check endpoints:

- **Basic health**: `GET /health`
- **Detailed health**: `GET /api/v1/health/detailed`

Example response:
```json
{
  "status": "healthy",
  "service": "RottenStocks API",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": 1703123456.789,
  "uptime": 3600.0,
  "correlation_id": "abc123def456"
}
```

## 🔐 Authentication

The API supports JWT-based authentication:

1. **Login** to get access and refresh tokens
2. **Include** access token in `Authorization: Bearer <token>` header
3. **Refresh** tokens when they expire

## 📊 Monitoring & Logging

### Structured Logging

The application uses structured logging with correlation IDs:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing request", user_id=123, action="create_stock")
```

### Request Tracing

Every request gets a unique correlation ID that's:
- Included in all log entries
- Returned in the `X-Correlation-ID` response header
- Used for distributed tracing

## 🗄️ Database

### Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade migration
alembic downgrade -1
```

### Models

Database models are located in `app/db/models/` and use SQLAlchemy 2.0 syntax.

## 🔄 Background Tasks

Background tasks are handled by Celery:

```bash
# Start Celery worker
celery -A app.tasks.worker worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.tasks.worker beat --loglevel=info

# Monitor tasks
celery -A app.tasks.worker flower
```

## 🔧 Configuration

Configuration is handled through environment variables and Pydantic Settings:

- **Development**: `.env` file
- **Production**: Environment variables
- **Testing**: `.env.test` file

Key configuration sections:
- Database connection
- Redis connection
- External API keys
- Security settings
- Rate limiting
- Caching configuration

## 🚦 Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Default**: 60 requests per minute
- **Burst**: Up to 100 requests in short bursts
- **Headers**: Rate limit info in response headers

## 🎯 External Integrations

### Reddit API
- **Purpose**: Fetch social media sentiment data
- **Rate Limit**: 60 requests per minute
- **Authentication**: OAuth2 client credentials

### Alpha Vantage API
- **Purpose**: Real-time stock price data
- **Rate Limit**: 5 requests per minute
- **Authentication**: API key

### Google Gemini API
- **Purpose**: AI-powered sentiment analysis
- **Rate Limit**: 1000 requests per minute
- **Authentication**: API key

## 🔍 Debugging

### VS Code Configuration

Launch configurations are provided in `.vscode/launch.json`:

- **Debug FastAPI**: Debug the main application
- **Debug Tests**: Debug specific test files
- **Debug Current Test**: Debug the currently open test file

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes the backend directory
2. **Database Errors**: Check that PostgreSQL is running and migrations are applied
3. **Redis Errors**: Verify Redis is running and accessible
4. **API Key Errors**: Ensure all required API keys are set in environment

## 📦 Dependencies

### Core Dependencies
- **FastAPI**: Web framework
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation
- **Celery**: Background tasks
- **Redis**: Caching and message broker

### Development Dependencies
- **pytest**: Testing framework
- **ruff**: Linting and formatting
- **mypy**: Type checking
- **pre-commit**: Git hooks

## 🔒 Security

### Best Practices
- JWT tokens for authentication
- Password hashing with bcrypt
- Rate limiting on all endpoints
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention with SQLAlchemy
- Security headers middleware

### Environment Security
- Never commit `.env` files
- Use strong secret keys in production
- Rotate API keys regularly
- Enable HTTPS in production
- Use trusted host middleware