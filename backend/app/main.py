"""
RottenStocks FastAPI Application

Main application entry point with FastAPI app initialization,
middleware configuration, and route registration.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings, validate_environment
from app.core.logging import configure_logging, get_logger, setup_request_logging
from app.tasks.scheduler import get_scheduler
from app.tasks.stock_sync import scheduled_stock_sync

# Configure logging before importing other modules
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting RottenStocks API")
    
    # Validate environment configuration
    env_status = validate_environment()
    logger.info("Environment validation", status=env_status)
    
    # Initialize and start task scheduler
    settings = get_settings()
    if settings.ENABLE_SCHEDULED_TASKS:
        scheduler = get_scheduler()
        await scheduler.start()
        
        # Schedule stock synchronization task with dynamic configuration
        sync_interval = settings.get_sync_interval_minutes()
        daily_limit = settings.get_alpha_vantage_daily_limit()
        
        scheduler.add_job(
            scheduled_stock_sync,
            trigger="interval",
            minutes=sync_interval,
            id="stock_sync",
            name="Stock Data Synchronization"
        )
        
        logger.info(
            f"Scheduled stock sync every {sync_interval} minutes "
            f"(Daily limit: {daily_limit} requests, Mode: {settings.SCHEDULING_MODE})"
        )
    
    logger.info("RottenStocks API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RottenStocks API")
    
    # Stop task scheduler
    if settings.ENABLE_SCHEDULED_TASKS:
        scheduler = get_scheduler()
        await scheduler.shutdown()
        logger.info("Task scheduler stopped")
    
    logger.info("RottenStocks API shutdown complete")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Add routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Add basic health endpoint at root level
    @app.get("/health")
    async def basic_health_check(request: Request) -> dict:
        """Basic health check endpoint at root level."""
        from app.api.v1.endpoints.health import _start_time
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": time.time(),
            "uptime": time.time() - _start_time,
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
        }
    
    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""
    settings = get_settings()
    
    # Trusted host middleware (security)
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.TRUSTED_HOSTS
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        """Log all HTTP requests with correlation ID."""
        # Setup request context
        request_context = setup_request_logging()
        
        # Bind logger with request context
        request_logger = logger.bind(**request_context)
        
        # Store context in request state for use in endpoints
        request.state.logger = request_logger
        request.state.correlation_id = request_context["correlation_id"]
        
        start_time = time.time()
        
        # Log request start
        request_logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = request_context["correlation_id"]
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log request completion
            request_logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time=process_time,
            )
            
            return response
            
        except Exception as exc:
            # Calculate processing time for failed requests
            process_time = time.time() - start_time
            
            # Log request failure
            request_logger.error(
                "Request failed",
                error=str(exc),
                process_time=process_time,
                exc_info=True,
            )
            
            # Re-raise the exception
            raise
    
    # Rate limiting middleware (placeholder)
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next) -> Response:
        """Rate limiting middleware placeholder."""
        # TODO: Implement actual rate limiting with Redis
        # For now, just pass through
        response = await call_next(request)
        return response


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> JSONResponse:
        """Handle 404 Not Found errors."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "NOT_FOUND",
                "message": "The requested resource was not found",
                "path": str(request.url.path),
                "method": request.method,
            }
        )
    
    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc) -> JSONResponse:
        """Handle 500 Internal Server Error."""
        # Get logger from request state if available
        request_logger = getattr(request.state, "logger", logger)
        
        request_logger.error(
            "Internal server error",
            error=str(exc),
            path=str(request.url.path),
            method=request.method,
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "correlation_id": getattr(request.state, "correlation_id", None),
            }
        )


# Create the application instance
app = create_application()


def run_server() -> None:
    """Run the development server."""
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD and settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )


if __name__ == "__main__":
    run_server()