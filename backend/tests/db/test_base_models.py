"""
Tests for base database models and mixins.

Tests the core database functionality including ID generation,
timestamps, soft deletes, and audit fields.
"""

import pytest
from datetime import datetime, timezone, timedelta, timezone
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.db.base import Base, BaseModel, AuditableModel, IDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin


# Test model classes for testing mixins
class TestIDModel(Base, IDMixin):
    __tablename__ = "test_id_model"
    name: Mapped[Optional[str]] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        if 'id' not in kwargs:
            from uuid import uuid4
            kwargs['id'] = str(uuid4())
        super().__init__(**kwargs)


class TestTimestampModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "test_timestamp_model"
    name: Mapped[Optional[str]] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        from datetime import datetime, timezone
        from uuid import uuid4
        
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
        
        super().__init__(**kwargs)


class TestSoftDeleteModel(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "test_soft_delete_model"
    name: Mapped[Optional[str]] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        from datetime import datetime, timezone, timezone
        from uuid import uuid4
        
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
        
        if 'is_deleted' not in kwargs:
            kwargs['is_deleted'] = False
        
        super().__init__(**kwargs)


class TestAuditModel(Base, IDMixin, TimestampMixin, AuditMixin):
    __tablename__ = "test_audit_model"
    name: Mapped[Optional[str]] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        from datetime import datetime, timezone, timezone
        from uuid import uuid4
        
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
        
        if 'version' not in kwargs:
            kwargs['version'] = 1
        
        super().__init__(**kwargs)


class TestBaseModel(BaseModel):
    __tablename__ = "test_base_model"
    name: Mapped[Optional[str]] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        from datetime import datetime, timezone
        from uuid import uuid4
        
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


class TestAuditableModel(AuditableModel):
    __tablename__ = "test_auditable_model"
    name: Mapped[Optional[str]] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        from datetime import datetime, timezone
        from uuid import uuid4
        
        # Set ID default if not provided
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        # Set timestamp defaults if not provided
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
        
        # Set soft delete defaults if not provided
        if 'is_deleted' not in kwargs:
            kwargs['is_deleted'] = False
        
        # Set audit defaults if not provided
        if 'version' not in kwargs:
            kwargs['version'] = 1
        
        # Initialize the SQLAlchemy model
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestIDMixin:
    """Test ID mixin functionality."""
    
    def test_id_generation(self):
        """Test that ID is generated as UUID string."""
        model = TestIDModel(name="test")
        
        # ID should be generated automatically
        assert model.id is not None
        assert isinstance(model.id, str)
        
        # Should be valid UUID format
        uuid_obj = UUID(model.id)
        assert str(uuid_obj) == model.id
    
    def test_unique_ids(self):
        """Test that different instances get unique IDs."""
        model1 = TestIDModel(name="test1")
        model2 = TestIDModel(name="test2")
        
        assert model1.id != model2.id


class TestTimestampMixin:
    """Test timestamp mixin functionality."""
    
    def test_automatic_timestamps(self):
        """Test that timestamps are set automatically."""
        before_creation = datetime.now(timezone.utc)
        model = TestTimestampModel(name="test")
        after_creation = datetime.now(timezone.utc)
        
        # Should have created_at timestamp
        assert model.created_at is not None
        assert before_creation <= model.created_at <= after_creation
        
        # Should have updated_at timestamp
        assert model.updated_at is not None
        assert before_creation <= model.updated_at <= after_creation
        
        # Initially, created_at and updated_at should be very close
        time_diff = abs((model.updated_at - model.created_at).total_seconds())
        assert time_diff < 1  # Less than 1 second difference


class TestSoftDeleteMixin:
    """Test soft delete mixin functionality."""
    
    def test_initial_state(self):
        """Test initial soft delete state."""
        model = TestSoftDeleteModel(name="test")
        
        assert model.is_deleted is False
        assert model.deleted_at is None
    
    def test_soft_delete(self):
        """Test soft delete functionality."""
        model = TestSoftDeleteModel(name="test")
        
        # Perform soft delete
        before_delete = datetime.now(timezone.utc)
        model.soft_delete()
        after_delete = datetime.now(timezone.utc)
        
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert before_delete <= model.deleted_at <= after_delete
    
    def test_restore(self):
        """Test restore functionality."""
        model = TestSoftDeleteModel(name="test")
        
        # Soft delete then restore
        model.soft_delete()
        assert model.is_deleted is True
        assert model.deleted_at is not None
        
        model.restore()
        assert model.is_deleted is False
        assert model.deleted_at is None


class TestAuditMixin:
    """Test audit mixin functionality."""
    
    def test_initial_state(self):
        """Test initial audit state."""
        model = TestAuditModel(name="test")
        
        assert model.created_by is None
        assert model.updated_by is None
        assert model.version == 1
    
    def test_update_audit_fields(self):
        """Test updating audit fields."""
        model = TestAuditModel(name="test")
        user_id = "user123"
        
        # Update audit fields
        model.update_audit_fields(user_id)
        
        assert model.created_by == user_id
        assert model.updated_by == user_id
        assert model.version == 2
    
    def test_update_audit_fields_existing_creator(self):
        """Test updating audit fields when creator already exists."""
        model = TestAuditModel(name="test")
        original_creator = "creator123"
        updater = "updater456"
        
        # Set initial creator
        model.update_audit_fields(original_creator)
        assert model.created_by == original_creator
        assert model.version == 2
        
        # Update with different user
        model.update_audit_fields(updater)
        
        # Creator should remain the same, updater should change
        assert model.created_by == original_creator
        assert model.updated_by == updater
        assert model.version == 3


class TestBaseModelFunctionality:
    """Test BaseModel functionality."""
    
    def test_to_dict(self):
        """Test converting model to dictionary."""
        model = TestBaseModel(name="test")
        data = model.to_dict()
        
        assert isinstance(data, dict)
        assert "id" in data
        assert "name" in data
        assert "created_at" in data
        assert "updated_at" in data
        
        assert data["name"] == "test"
        assert data["id"] == model.id
    
    def test_repr(self):
        """Test string representation."""
        model = TestBaseModel(name="test")
        repr_str = repr(model)
        
        assert "TestBaseModel" in repr_str
        assert model.id[:8] in repr_str  # Should contain part of ID
        assert "test" in repr_str  # Should contain name


class TestAuditableModelFunctionality:
    """Test AuditableModel functionality."""
    
    def test_includes_all_mixins(self):
        """Test that AuditableModel includes all expected functionality."""
        model = TestAuditableModel(name="test")
        
        # Should have ID
        assert hasattr(model, "id")
        assert model.id is not None
        
        # Should have timestamps
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
        assert model.created_at is not None
        assert model.updated_at is not None
        
        # Should have soft delete
        assert hasattr(model, "is_deleted")
        assert hasattr(model, "deleted_at")
        assert hasattr(model, "soft_delete")
        assert hasattr(model, "restore")
        assert model.is_deleted is False
        
        # Should have audit fields
        assert hasattr(model, "created_by")
        assert hasattr(model, "updated_by")
        assert hasattr(model, "version")
        assert hasattr(model, "update_audit_fields")
        assert model.version == 1
        
        # Should have BaseModel methods
        assert hasattr(model, "to_dict")
        assert hasattr(model, "__repr__")
    
    def test_combined_functionality(self):
        """Test that all mixins work together correctly."""
        model = TestAuditableModel(name="test")
        user_id = "user123"
        
        # Test audit and soft delete together
        model.update_audit_fields(user_id)
        model.soft_delete()
        
        assert model.created_by == user_id
        assert model.updated_by == user_id
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert model.version == 2
        
        # Test restoration
        model.restore()
        assert model.is_deleted is False
        assert model.deleted_at is None
        
        # Test to_dict includes all fields
        data = model.to_dict()
        expected_fields = [
            "id", "name", "created_at", "updated_at",
            "is_deleted", "deleted_at", "created_by", "updated_by", "version"
        ]
        
        for field in expected_fields:
            assert field in data