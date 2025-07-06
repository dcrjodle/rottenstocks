"""
Task models and schemas for background task management.

Provides Pydantic models for task status, configuration, and monitoring.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class TaskType(str, Enum):
    """Types of background tasks."""
    STOCK_SYNC = "stock_sync"
    STOCK_DISCOVERY = "stock_discovery"
    SOCIAL_MEDIA_SYNC = "social_media_sync"
    CLEANUP = "cleanup"
    SENTIMENT_ANALYSIS = "sentiment_analysis"


class TaskConfiguration(BaseModel):
    """Configuration for a scheduled task."""
    task_id: str
    task_type: TaskType
    name: str
    description: Optional[str] = None
    enabled: bool = True
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    max_instances: int = 1
    misfire_grace_time: int = 30
    timeout_seconds: Optional[int] = None
    retry_count: int = 3
    retry_delay_seconds: int = 60


class TaskExecution(BaseModel):
    """Details of a task execution."""
    execution_id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class TaskStats(BaseModel):
    """Statistics for a task."""
    task_id: str
    task_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    cancelled_executions: int = 0
    missed_executions: int = 0
    last_execution: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    average_duration_seconds: Optional[float] = None
    success_rate: float = 0.0


class TaskInfo(BaseModel):
    """Information about a scheduled task."""
    task_id: str
    name: str
    task_type: TaskType
    status: TaskStatus
    enabled: bool
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    trigger_info: str
    pending: bool = False
    configuration: TaskConfiguration
    stats: TaskStats


class SchedulerStatus(BaseModel):
    """Status of the task scheduler."""
    is_running: bool
    total_jobs: int
    active_jobs: int
    paused_jobs: int
    uptime_seconds: Optional[float] = None
    last_heartbeat: datetime = Field(default_factory=datetime.now)


class StockSyncResult(BaseModel):
    """Result of a stock synchronization task."""
    status: str
    stocks_processed: int
    successful_updates: int
    failed_updates: int
    requests_used: int
    errors: List[str] = []
    updated_stocks: List[str] = []
    reason: Optional[str] = None
    message: Optional[str] = None


class StockSyncStats(BaseModel):
    """Statistics about stock synchronization."""
    total_stocks: int
    active_stocks: int
    recently_updated: int
    needs_update: int
    requests_used_today: int
    daily_limit: int
    requests_remaining: int
    last_reset_date: str


class TaskHealthCheck(BaseModel):
    """Health check result for tasks."""
    healthy: bool
    scheduler_running: bool
    redis_connected: bool
    database_connected: bool
    total_tasks: int
    active_tasks: int
    failed_tasks_last_24h: int
    last_successful_sync: Optional[datetime] = None
    issues: List[str] = []
    recommendations: List[str] = []


class TaskCommand(BaseModel):
    """Command to execute on a task."""
    action: str  # "start", "stop", "pause", "resume", "restart"
    task_id: Optional[str] = None
    force: bool = False


class TaskScheduleUpdate(BaseModel):
    """Update to a task schedule."""
    task_id: str
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    max_instances: Optional[int] = None
    misfire_grace_time: Optional[int] = None


class BulkTaskOperation(BaseModel):
    """Bulk operation on multiple tasks."""
    task_ids: List[str]
    action: str  # "enable", "disable", "restart", "remove"
    force: bool = False


# Response models
class TaskResponse(BaseModel):
    """Generic task response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = []


class TaskListResponse(BaseModel):
    """Response for listing tasks."""
    tasks: List[TaskInfo]
    total: int
    active: int
    scheduler_status: SchedulerStatus


class TaskStatsResponse(BaseModel):
    """Response for task statistics."""
    task_stats: List[TaskStats]
    scheduler_status: SchedulerStatus
    stock_sync_stats: StockSyncStats
    health_check: TaskHealthCheck