"""
Database exceptions for RottenStocks application.

This module defines custom database exceptions and error handling utilities.
"""

import logging
from typing import Optional, Dict, Any

from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    DataError,
    OperationalError,
    DatabaseError as SQLAlchemyDatabaseError,
    InvalidRequestError,
    StatementError,
    NoResultFound,
    MultipleResultsFound,
    DisconnectionError,
    TimeoutError as SQLAlchemyTimeoutError
)
try:
    from asyncpg.exceptions import PostgresError as PostgreSQLError, UniqueViolationError, ForeignKeyViolationError
except ImportError:
    # Fallback if asyncpg is not available or has different names
    PostgreSQLError = Exception
    UniqueViolationError = Exception
    ForeignKeyViolationError = Exception

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base database error."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None, error_code: Optional[str] = None):
        """
        Initialize database error.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
            error_code: Error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.original_error = original_error
        self.error_code = error_code
        
        # Log the error
        logger.error(f"Database error [{error_code}]: {message}")
        if original_error:
            logger.error(f"Original error: {original_error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code
        }


class ConnectionError(DatabaseError):
    """Database connection error."""
    
    def __init__(self, message: str = "Database connection failed", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_CONNECTION_ERROR")


class TimeoutError(DatabaseError):
    """Database timeout error."""
    
    def __init__(self, message: str = "Database operation timed out", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_TIMEOUT_ERROR")


class ValidationError(DatabaseError):
    """Data validation error."""
    
    def __init__(self, message: str = "Data validation failed", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_VALIDATION_ERROR")


class DuplicateKeyError(DatabaseError):
    """Duplicate key constraint violation."""
    
    def __init__(self, message: str = "Duplicate key violation", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_DUPLICATE_KEY_ERROR")


class ForeignKeyError(DatabaseError):
    """Foreign key constraint violation."""
    
    def __init__(self, message: str = "Foreign key constraint violation", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_FOREIGN_KEY_ERROR")


class NotFoundError(DatabaseError):
    """Record not found error."""
    
    def __init__(self, message: str = "Record not found", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_NOT_FOUND_ERROR")


class MultipleResultsError(DatabaseError):
    """Multiple results found when expecting single result."""
    
    def __init__(self, message: str = "Multiple results found", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_MULTIPLE_RESULTS_ERROR")


class TransactionError(DatabaseError):
    """Transaction-related error."""
    
    def __init__(self, message: str = "Transaction failed", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_TRANSACTION_ERROR")


class QueryError(DatabaseError):
    """Query execution error."""
    
    def __init__(self, message: str = "Query execution failed", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_QUERY_ERROR")


class ConfigurationError(DatabaseError):
    """Database configuration error."""
    
    def __init__(self, message: str = "Database configuration error", original_error: Optional[Exception] = None):
        super().__init__(message, original_error, "DB_CONFIG_ERROR")


def handle_database_error(error: Exception) -> DatabaseError:
    """
    Convert SQLAlchemy and asyncpg errors to custom database exceptions.
    
    Args:
        error: Original exception
    
    Returns:
        Custom database exception
    """
    error_message = str(error)
    
    # Handle asyncpg specific errors
    if isinstance(error, UniqueViolationError):
        return DuplicateKeyError(f"Duplicate key violation: {error_message}", error)
    
    if isinstance(error, ForeignKeyViolationError):
        return ForeignKeyError(f"Foreign key constraint violation: {error_message}", error)
    
    if isinstance(error, PostgreSQLError):
        return QueryError(f"PostgreSQL error: {error_message}", error)
    
    # Handle SQLAlchemy errors
    if isinstance(error, IntegrityError):
        # Check if it's a unique constraint violation
        if "unique constraint" in error_message.lower() or "duplicate key" in error_message.lower():
            return DuplicateKeyError(f"Duplicate key violation: {error_message}", error)
        
        # Check if it's a foreign key constraint violation
        if "foreign key" in error_message.lower():
            return ForeignKeyError(f"Foreign key constraint violation: {error_message}", error)
        
        return ValidationError(f"Data integrity error: {error_message}", error)
    
    if isinstance(error, DataError):
        return ValidationError(f"Data validation error: {error_message}", error)
    
    if isinstance(error, OperationalError):
        # Check if it's a connection error
        if any(keyword in error_message.lower() for keyword in [
            "connection", "connect", "server", "network", "host", "port"
        ]):
            return ConnectionError(f"Database connection error: {error_message}", error)
        
        return QueryError(f"Database operation error: {error_message}", error)
    
    if isinstance(error, SQLAlchemyTimeoutError):
        return TimeoutError(f"Database operation timed out: {error_message}", error)
    
    if isinstance(error, DisconnectionError):
        return ConnectionError(f"Database connection lost: {error_message}", error)
    
    if isinstance(error, NoResultFound):
        return NotFoundError(f"Record not found: {error_message}", error)
    
    if isinstance(error, MultipleResultsFound):
        return MultipleResultsError(f"Multiple results found: {error_message}", error)
    
    if isinstance(error, (InvalidRequestError, StatementError)):
        return QueryError(f"Invalid query: {error_message}", error)
    
    if isinstance(error, SQLAlchemyDatabaseError):
        return QueryError(f"Database error: {error_message}", error)
    
    if isinstance(error, SQLAlchemyError):
        return DatabaseError(f"Database error: {error_message}", error)
    
    # For any other exception, wrap it in a generic DatabaseError
    return DatabaseError(f"Unexpected database error: {error_message}", error)


def handle_database_error_with_context(error: Exception, context: str) -> DatabaseError:
    """
    Convert error to custom database exception with additional context.
    
    Args:
        error: Original exception
        context: Additional context about the operation
    
    Returns:
        Custom database exception with context
    """
    db_error = handle_database_error(error)
    
    # Add context to the error message
    contextual_message = f"{context}: {db_error.message}"
    
    # Create new error with contextual message
    error_class = type(db_error)
    return error_class(contextual_message, db_error.original_error)


class DatabaseErrorHandler:
    """
    Context manager for handling database errors.
    
    Usage:
        async with DatabaseErrorHandler("Creating user"):
            # Database operations
            pass
    """
    
    def __init__(self, operation_context: str):
        """
        Initialize error handler.
        
        Args:
            operation_context: Description of the operation being performed
        """
        self.operation_context = operation_context
    
    async def __aenter__(self):
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager and handle any database errors."""
        if exc_type and issubclass(exc_type, Exception):
            # If it's already a DatabaseError, just re-raise it
            if isinstance(exc_val, DatabaseError):
                return False
            
            # Convert to database error with context
            db_error = handle_database_error_with_context(exc_val, self.operation_context)
            
            # Replace the original exception with our custom one
            raise db_error from exc_val
        
        return False


# Error code constants for programmatic handling
class ErrorCodes:
    """Constants for database error codes."""
    
    CONNECTION_ERROR = "DB_CONNECTION_ERROR"
    TIMEOUT_ERROR = "DB_TIMEOUT_ERROR"
    VALIDATION_ERROR = "DB_VALIDATION_ERROR"
    DUPLICATE_KEY_ERROR = "DB_DUPLICATE_KEY_ERROR"
    FOREIGN_KEY_ERROR = "DB_FOREIGN_KEY_ERROR"
    NOT_FOUND_ERROR = "DB_NOT_FOUND_ERROR"
    MULTIPLE_RESULTS_ERROR = "DB_MULTIPLE_RESULTS_ERROR"
    TRANSACTION_ERROR = "DB_TRANSACTION_ERROR"
    QUERY_ERROR = "DB_QUERY_ERROR"
    CONFIG_ERROR = "DB_CONFIG_ERROR"


# Utility functions for common error scenarios

def raise_not_found(entity_name: str, identifier: Any) -> None:
    """
    Raise NotFoundError with standardized message.
    
    Args:
        entity_name: Name of the entity (e.g., "User", "Stock")
        identifier: Identifier that was not found
    """
    raise NotFoundError(f"{entity_name} with identifier '{identifier}' not found")


def raise_duplicate_key(entity_name: str, field_name: str, value: Any) -> None:
    """
    Raise DuplicateKeyError with standardized message.
    
    Args:
        entity_name: Name of the entity (e.g., "User", "Stock")
        field_name: Name of the field that has duplicate value
        value: The duplicate value
    """
    raise DuplicateKeyError(f"{entity_name} with {field_name} '{value}' already exists")


def raise_foreign_key_violation(entity_name: str, referenced_entity: str, identifier: Any) -> None:
    """
    Raise ForeignKeyError with standardized message.
    
    Args:
        entity_name: Name of the entity being created/updated
        referenced_entity: Name of the referenced entity
        identifier: Identifier of the missing referenced entity
    """
    raise ForeignKeyError(f"Cannot create {entity_name}: {referenced_entity} with identifier '{identifier}' does not exist")