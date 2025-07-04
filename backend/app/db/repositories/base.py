"""
Base repository for RottenStocks database operations.

This module provides the abstract base repository class with common CRUD operations
and patterns that can be extended by model-specific repositories.
"""

import logging
from abc import ABC, abstractmethod
from typing import (
    TypeVar, Generic, Type, Optional, List, Dict, Any, Tuple, Union, Sequence
)
from datetime import datetime, timezone

from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from ..base import BaseModel
from ..exceptions import (
    DatabaseError,
    NotFoundError,
    DuplicateKeyError,
    ValidationError,
    handle_database_error,
    DatabaseErrorHandler
)

logger = logging.getLogger(__name__)

# Generic type for model classes
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType], ABC):
    """
    Abstract base repository with common database operations.
    
    This class provides a foundation for model-specific repositories with
    standard CRUD operations, error handling, and query utilities.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    @abstractmethod
    def get_model_class(self) -> Type[ModelType]:
        """
        Get the model class for this repository.
        
        Returns:
            Model class
        """
        pass
    
    def get_primary_key_field(self) -> str:
        """
        Get the primary key field name for the model.
        
        Returns:
            Primary key field name (defaults to 'id')
        """
        return "id"
    
    def get_unique_fields(self) -> List[str]:
        """
        Get list of unique fields for the model.
        
        Returns:
            List of unique field names
        """
        return [self.get_primary_key_field()]
    
    # Basic CRUD operations
    
    async def get_by_id(
        self, 
        id_value: Any, 
        options: Optional[List] = None
    ) -> Optional[ModelType]:
        """
        Get record by primary key.
        
        Args:
            id_value: Primary key value
            options: SQLAlchemy query options (e.g., selectinload)
        
        Returns:
            Model instance or None if not found
        """
        async with DatabaseErrorHandler(f"Getting {self.get_model_class().__name__} by ID"):
            model_class = self.get_model_class()
            pk_field = getattr(model_class, self.get_primary_key_field())
            
            query = select(model_class).where(pk_field == id_value)
            
            if options:
                query = query.options(*options)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
    
    async def get_by_field(
        self, 
        field_name: str, 
        value: Any, 
        options: Optional[List] = None
    ) -> Optional[ModelType]:
        """
        Get record by field value.
        
        Args:
            field_name: Field name to search by
            value: Field value
            options: SQLAlchemy query options
        
        Returns:
            Model instance or None if not found
        """
        async with DatabaseErrorHandler(f"Getting {self.get_model_class().__name__} by {field_name}"):
            model_class = self.get_model_class()
            field = getattr(model_class, field_name)
            
            query = select(model_class).where(field == value)
            
            if options:
                query = query.options(*options)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        options: Optional[List] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Get all records with optional pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            options: SQLAlchemy query options
            order_by: Field name to order by
        
        Returns:
            List of model instances
        """
        async with DatabaseErrorHandler(f"Getting all {self.get_model_class().__name__} records"):
            model_class = self.get_model_class()
            query = select(model_class)
            
            if options:
                query = query.options(*options)
            
            if order_by:
                order_field = getattr(model_class, order_by)
                query = query.order_by(order_field)
            
            if offset:
                query = query.offset(offset)
            
            if limit:
                query = query.limit(limit)
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create new record.
        
        Args:
            **kwargs: Field values for the new record
        
        Returns:
            Created model instance
        """
        async with DatabaseErrorHandler(f"Creating {self.get_model_class().__name__}"):
            model_class = self.get_model_class()
            instance = model_class(**kwargs)
            
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            
            logger.info(f"Created {model_class.__name__} with ID: {getattr(instance, self.get_primary_key_field())}")
            return instance
    
    async def update(self, id_value: Any, **kwargs) -> Optional[ModelType]:
        """
        Update existing record by ID.
        
        Args:
            id_value: Primary key value
            **kwargs: Field values to update
        
        Returns:
            Updated model instance or None if not found
        """
        async with DatabaseErrorHandler(f"Updating {self.get_model_class().__name__}"):
            instance = await self.get_by_id(id_value)
            if not instance:
                return None
            
            # Update fields
            for field, value in kwargs.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
                else:
                    logger.warning(f"Field '{field}' not found on {self.get_model_class().__name__}")
            
            # Update timestamp if model has updated_at field
            if hasattr(instance, 'updated_at'):
                instance.updated_at = datetime.now(timezone.utc)
            
            await self.session.flush()
            await self.session.refresh(instance)
            
            logger.info(f"Updated {self.get_model_class().__name__} with ID: {id_value}")
            return instance
    
    async def delete(self, id_value: Any) -> bool:
        """
        Delete record by ID.
        
        Args:
            id_value: Primary key value
        
        Returns:
            True if deleted, False if not found
        """
        async with DatabaseErrorHandler(f"Deleting {self.get_model_class().__name__}"):
            instance = await self.get_by_id(id_value)
            if not instance:
                return False
            
            await self.session.delete(instance)
            await self.session.flush()
            
            logger.info(f"Deleted {self.get_model_class().__name__} with ID: {id_value}")
            return True
    
    # Advanced operations
    
    async def get_or_create(
        self, 
        defaults: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> Tuple[ModelType, bool]:
        """
        Get existing record or create new one.
        
        Args:
            defaults: Default values for creation
            **kwargs: Query parameters for lookup
        
        Returns:
            Tuple of (instance, created_flag)
        """
        async with DatabaseErrorHandler(f"Get or create {self.get_model_class().__name__}"):
            # Try to get existing record
            model_class = self.get_model_class()
            query = select(model_class)
            
            # Build where conditions
            conditions = []
            for field, value in kwargs.items():
                field_attr = getattr(model_class, field)
                conditions.append(field_attr == value)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await self.session.execute(query)
            instance = result.scalar_one_or_none()
            
            if instance:
                return instance, False
            
            # Create new record
            create_kwargs = {**kwargs, **(defaults or {})}
            instance = await self.create(**create_kwargs)
            return instance, True
    
    async def upsert(
        self, 
        constraint_fields: List[str], 
        **kwargs
    ) -> ModelType:
        """
        Insert or update record using PostgreSQL ON CONFLICT.
        
        Args:
            constraint_fields: Fields that define uniqueness
            **kwargs: Field values
        
        Returns:
            Upserted model instance
        """
        async with DatabaseErrorHandler(f"Upserting {self.get_model_class().__name__}"):
            model_class = self.get_model_class()
            table = model_class.__table__
            
            # Create insert statement
            stmt = insert(table).values(**kwargs)
            
            # Add ON CONFLICT clause
            update_dict = {
                key: stmt.excluded[key] 
                for key in kwargs.keys() 
                if key not in constraint_fields
            }
            
            if update_dict:
                stmt = stmt.on_conflict_do_update(
                    index_elements=constraint_fields,
                    set_=update_dict
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=constraint_fields)
            
            # Add RETURNING clause
            stmt = stmt.returning(table)
            
            result = await self.session.execute(stmt)
            row = result.fetchone()
            
            if row:
                # Convert row to model instance
                instance_data = dict(row._mapping)
                instance = model_class(**instance_data)
                return instance
            else:
                # Get existing record if nothing was returned (conflict with no update)
                conditions = []
                for field in constraint_fields:
                    field_attr = getattr(model_class, field)
                    conditions.append(field_attr == kwargs[field])
                
                query = select(model_class).where(and_(*conditions))
                result = await self.session.execute(query)
                return result.scalar_one()
    
    async def bulk_create(self, records: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            records: List of dictionaries with record data
        
        Returns:
            List of created model instances
        """
        async with DatabaseErrorHandler(f"Bulk creating {self.get_model_class().__name__} records"):
            if not records:
                return []
            
            model_class = self.get_model_class()
            instances = []
            
            for record_data in records:
                instance = model_class(**record_data)
                instances.append(instance)
                self.session.add(instance)
            
            await self.session.flush()
            
            # Refresh all instances to get generated IDs
            for instance in instances:
                await self.session.refresh(instance)
            
            logger.info(f"Bulk created {len(instances)} {model_class.__name__} records")
            return instances
    
    async def bulk_update(
        self, 
        updates: List[Dict[str, Any]], 
        id_field: str = None
    ) -> int:
        """
        Update multiple records in bulk.
        
        Args:
            updates: List of dictionaries with update data (must include ID)
            id_field: ID field name (defaults to primary key)
        
        Returns:
            Number of updated records
        """
        async with DatabaseErrorHandler(f"Bulk updating {self.get_model_class().__name__} records"):
            if not updates:
                return 0
            
            model_class = self.get_model_class()
            id_field = id_field or self.get_primary_key_field()
            
            updated_count = 0
            
            for update_data in updates:
                if id_field not in update_data:
                    logger.warning(f"Skipping update: missing {id_field}")
                    continue
                
                id_value = update_data.pop(id_field)
                
                if update_data:  # Only update if there are fields to update
                    stmt = (
                        update(model_class)
                        .where(getattr(model_class, id_field) == id_value)
                        .values(**update_data)
                    )
                    
                    result = await self.session.execute(stmt)
                    updated_count += result.rowcount
            
            logger.info(f"Bulk updated {updated_count} {model_class.__name__} records")
            return updated_count
    
    # Query utilities
    
    async def count(self, **conditions) -> int:
        """
        Count records matching conditions.
        
        Args:
            **conditions: Filter conditions
        
        Returns:
            Number of matching records
        """
        async with DatabaseErrorHandler(f"Counting {self.get_model_class().__name__} records"):
            model_class = self.get_model_class()
            query = select(func.count(getattr(model_class, self.get_primary_key_field())))
            
            # Add conditions
            if conditions:
                where_conditions = []
                for field, value in conditions.items():
                    field_attr = getattr(model_class, field)
                    where_conditions.append(field_attr == value)
                
                query = query.where(and_(*where_conditions))
            
            result = await self.session.execute(query)
            return result.scalar()
    
    async def exists(self, **conditions) -> bool:
        """
        Check if record exists matching conditions.
        
        Args:
            **conditions: Filter conditions
        
        Returns:
            True if record exists, False otherwise
        """
        async with DatabaseErrorHandler(f"Checking existence of {self.get_model_class().__name__}"):
            model_class = self.get_model_class()
            query = select(1).select_from(model_class)
            
            # Add conditions
            if conditions:
                where_conditions = []
                for field, value in conditions.items():
                    field_attr = getattr(model_class, field)
                    where_conditions.append(field_attr == value)
                
                query = query.where(and_(*where_conditions))
            
            query = query.limit(1)
            result = await self.session.execute(query)
            return result.first() is not None
    
    async def filter(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        options: Optional[List] = None
    ) -> List[ModelType]:
        """
        Filter records with complex conditions.
        
        Args:
            filters: Dictionary of filter conditions
            order_by: Field name to order by
            limit: Maximum number of records
            offset: Number of records to skip
            options: SQLAlchemy query options
        
        Returns:
            List of filtered model instances
        """
        async with DatabaseErrorHandler(f"Filtering {self.get_model_class().__name__} records"):
            model_class = self.get_model_class()
            query = select(model_class)
            
            # Add filters
            if filters:
                where_conditions = []
                for field, value in filters.items():
                    if hasattr(model_class, field):
                        field_attr = getattr(model_class, field)
                        
                        if isinstance(value, list):
                            where_conditions.append(field_attr.in_(value))
                        elif isinstance(value, dict):
                            # Handle complex conditions like {"gt": 10, "lt": 100}
                            for op, op_value in value.items():
                                if op == "gt":
                                    where_conditions.append(field_attr > op_value)
                                elif op == "gte":
                                    where_conditions.append(field_attr >= op_value)
                                elif op == "lt":
                                    where_conditions.append(field_attr < op_value)
                                elif op == "lte":
                                    where_conditions.append(field_attr <= op_value)
                                elif op == "ne":
                                    where_conditions.append(field_attr != op_value)
                                elif op == "like":
                                    where_conditions.append(field_attr.like(op_value))
                                elif op == "ilike":
                                    where_conditions.append(field_attr.ilike(op_value))
                        else:
                            where_conditions.append(field_attr == value)
                
                if where_conditions:
                    query = query.where(and_(*where_conditions))
            
            # Add options
            if options:
                query = query.options(*options)
            
            # Add ordering
            if order_by:
                if order_by.startswith("-"):
                    # Descending order
                    field_name = order_by[1:]
                    if hasattr(model_class, field_name):
                        order_field = getattr(model_class, field_name)
                        query = query.order_by(order_field.desc())
                else:
                    # Ascending order
                    if hasattr(model_class, order_by):
                        order_field = getattr(model_class, order_by)
                        query = query.order_by(order_field)
            
            # Add pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
    
    # Validation utilities
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data for record creation.
        
        Args:
            data: Data to validate
        
        Returns:
            Validated data
        
        Raises:
            ValidationError: If validation fails
        """
        # Override in subclasses for model-specific validation
        return data
    
    def validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data for record update.
        
        Args:
            data: Data to validate
        
        Returns:
            Validated data
        
        Raises:
            ValidationError: If validation fails
        """
        # Override in subclasses for model-specific validation
        return data