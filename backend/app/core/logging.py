"""
Structured logging configuration using structlog.

Provides consistent, structured logging across the application with
correlation IDs, request tracking, and proper formatting.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from rich.logging import RichHandler

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        handlers=[RichHandler(rich_tracebacks=True)] if settings.DEBUG else []
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.DEBUG 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def setup_request_logging() -> Dict[str, Any]:
    """Setup request-specific logging context."""
    import uuid
    
    correlation_id = str(uuid.uuid4())
    return {
        "correlation_id": correlation_id,
        "request_id": correlation_id[:8]  # Short version for logs
    }