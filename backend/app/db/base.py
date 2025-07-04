"""
Database base classes and utilities.

Provides SQLAlchemy base class, session management, and common mixins
for all database models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column


@as_declarative()
class Base:
    """Base class for all database models."""
    
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class IDMixin:
    """Mixin that adds a UUID primary key column."""
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality."""
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """Mixin that adds audit trail fields."""
    
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )
    
    def update_audit_fields(self, user_id: Optional[str] = None) -> None:
        """Update audit fields for the current user."""
        if user_id:
            if not self.created_by:
                self.created_by = user_id
            self.updated_by = user_id
        self.version += 1


class BaseModel(Base, IDMixin, TimestampMixin):
    """
    Base model class that includes ID and timestamp mixins.
    
    This is the recommended base class for most models.
    """
    __abstract__ = True
    
    def __init__(self, **kwargs):
        """Initialize model with defaults for mixins."""
        # Set ID default if not provided
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        # Set timestamp defaults if not provided
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
        
        # Initialize the SQLAlchemy model
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = [
            f"{key}={repr(value)}"
            for key, value in self.to_dict().items()
            if key in ["id", "name", "symbol", "title"]  # Common display fields
        ]
        attr_str = ", ".join(attrs[:3])  # Limit to first 3 attributes
        return f"<{class_name}({attr_str})>"


class AuditableModel(BaseModel, SoftDeleteMixin, AuditMixin):
    """
    Extended base model with soft delete and audit capabilities.
    
    Use this for models that require full audit trail and soft delete.
    """
    __abstract__ = True
    
    def __init__(self, **kwargs):
        """Initialize model with defaults for all mixins."""
        # Set soft delete defaults if not provided
        if 'is_deleted' not in kwargs:
            kwargs['is_deleted'] = False
        
        # Set audit defaults if not provided
        if 'version' not in kwargs:
            kwargs['version'] = 1
        
        # Call parent constructor (BaseModel handles ID and timestamps)
        super().__init__(**kwargs)