"""
Task management and monitoring endpoints.

Provides REST API endpoints for managing and monitoring background tasks,
including scheduler status, task statistics, and manual task triggers.
"""

from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.tasks.scheduler import get_scheduler
from app.tasks.stock_sync import get_task_manager, scheduled_stock_sync
from app.tasks.reddit_sync import (
    get_reddit_task_manager, 
    scheduled_reddit_finance_sync,
    scheduled_reddit_trending_analysis
)
from app.tasks.models import (
    TaskInfo, TaskResponse, TaskListResponse, TaskStatsResponse,
    TaskCommand, TaskScheduleUpdate, BulkTaskOperation,
    StockSyncResult, StockSyncStats, TaskHealthCheck,
    TaskStatus, TaskType, SchedulerStatus
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=TaskListResponse)
async def list_tasks():
    """List all scheduled tasks with their status."""
    try:
        scheduler = get_scheduler()
        
        if not scheduler.is_running:
            return TaskListResponse(
                tasks=[],
                total=0,
                active=0,
                scheduler_status=SchedulerStatus(
                    is_running=False,
                    total_jobs=0,
                    active_jobs=0,
                    paused_jobs=0
                )
            )
        
        jobs = scheduler.get_jobs()
        task_stats = await scheduler.get_job_stats()
        
        task_infos = []
        for job in jobs:
            task_info = TaskInfo(
                task_id=job.id,
                name=job.name,
                task_type=_get_task_type(job.id),
                status=TaskStatus.SCHEDULED if job.next_run_time else TaskStatus.CANCELLED,
                enabled=not job.pending,
                next_run_time=job.next_run_time,
                trigger_info=str(job.trigger),
                pending=job.pending,
                configuration=_get_task_configuration(job),
                stats=_get_task_stats(job.id, task_stats.get("execution_stats", {}))
            )
            task_infos.append(task_info)
        
        scheduler_status = SchedulerStatus(
            is_running=scheduler.is_running,
            total_jobs=len(jobs),
            active_jobs=len([j for j in jobs if j.next_run_time]),
            paused_jobs=len([j for j in jobs if j.pending])
        )
        
        return TaskListResponse(
            tasks=task_infos,
            total=len(task_infos),
            active=len([t for t in task_infos if t.status == TaskStatus.SCHEDULED]),
            scheduler_status=scheduler_status
        )
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats():
    """Get comprehensive task statistics."""
    try:
        scheduler = get_scheduler()
        task_manager = get_task_manager()
        
        # Get scheduler stats
        scheduler_stats = await scheduler.get_job_stats()
        
        # Get stock sync stats
        stock_sync_stats = await task_manager.get_sync_stats()
        
        # Get health check
        health_check = await _get_health_check(scheduler, task_manager)
        
        # Convert to response models
        scheduler_status = SchedulerStatus(
            is_running=scheduler_stats.get("scheduler_running", False),
            total_jobs=scheduler_stats.get("total_jobs", 0),
            active_jobs=len([j for j in scheduler_stats.get("job_details", []) if j.get("next_run")]),
            paused_jobs=len([j for j in scheduler_stats.get("job_details", []) if j.get("pending")])
        )
        
        stock_sync_stats_model = StockSyncStats(**stock_sync_stats)
        
        return TaskStatsResponse(
            task_stats=[],  # Will be populated with actual stats
            scheduler_status=scheduler_status,
            stock_sync_stats=stock_sync_stats_model,
            health_check=health_check
        )
        
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/stock", response_model=TaskResponse)
async def trigger_stock_sync(background_tasks: BackgroundTasks):
    """Manually trigger stock synchronization."""
    try:
        # Run sync in background
        background_tasks.add_task(scheduled_stock_sync)
        
        return TaskResponse(
            success=True,
            message="Stock synchronization triggered successfully",
            data={"triggered_at": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger stock sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/reddit", response_model=TaskResponse)
async def trigger_reddit_sync(background_tasks: BackgroundTasks):
    """Manually trigger Reddit finance discussions sync."""
    try:
        # Run sync in background
        background_tasks.add_task(scheduled_reddit_finance_sync)
        
        return TaskResponse(
            success=True,
            message="Reddit synchronization triggered successfully",
            data={"triggered_at": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger Reddit sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/reddit/trending", response_model=TaskResponse)
async def trigger_reddit_trending(background_tasks: BackgroundTasks):
    """Manually trigger Reddit trending stocks analysis."""
    try:
        # Run trending analysis in background
        background_tasks.add_task(scheduled_reddit_trending_analysis)
        
        return TaskResponse(
            success=True,
            message="Reddit trending analysis triggered successfully",
            data={"triggered_at": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger Reddit trending analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/stock/status", response_model=StockSyncStats)
async def get_stock_sync_status():
    """Get current stock synchronization status."""
    try:
        task_manager = get_task_manager()
        stats = await task_manager.get_sync_stats()
        
        return StockSyncStats(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get stock sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/reddit/status")
async def get_reddit_sync_status():
    """Get current Reddit synchronization status."""
    try:
        reddit_task_manager = get_reddit_task_manager()
        stats = await reddit_task_manager.get_sync_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get Reddit sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/reddit/trending")
async def get_reddit_trending():
    """Get current Reddit trending stocks."""
    try:
        reddit_task_manager = get_reddit_task_manager()
        stats = await reddit_task_manager.get_sync_stats()
        
        return {
            "trending_stocks": stats.get("trending_stocks", {}),
            "last_analysis": stats.get("last_sync"),
            "total_trending": len(stats.get("trending_stocks", {}))
        }
        
    except Exception as e:
        logger.error(f"Failed to get Reddit trending: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command", response_model=TaskResponse)
async def execute_task_command(command: TaskCommand):
    """Execute a task command (start, stop, pause, resume)."""
    try:
        scheduler = get_scheduler()
        
        if command.action == "start":
            if not scheduler.is_running:
                await scheduler.start()
                return TaskResponse(
                    success=True,
                    message="Scheduler started successfully"
                )
            else:
                return TaskResponse(
                    success=False,
                    message="Scheduler is already running"
                )
        
        elif command.action == "stop":
            if scheduler.is_running:
                await scheduler.shutdown()
                return TaskResponse(
                    success=True,
                    message="Scheduler stopped successfully"
                )
            else:
                return TaskResponse(
                    success=False,
                    message="Scheduler is not running"
                )
        
        elif command.action == "pause" and command.task_id:
            job = scheduler.get_job(command.task_id)
            if job:
                scheduler.scheduler.pause_job(command.task_id)
                return TaskResponse(
                    success=True,
                    message=f"Task {command.task_id} paused"
                )
            else:
                return TaskResponse(
                    success=False,
                    message=f"Task {command.task_id} not found"
                )
        
        elif command.action == "resume" and command.task_id:
            job = scheduler.get_job(command.task_id)
            if job:
                scheduler.scheduler.resume_job(command.task_id)
                return TaskResponse(
                    success=True,
                    message=f"Task {command.task_id} resumed"
                )
            else:
                return TaskResponse(
                    success=False,
                    message=f"Task {command.task_id} not found"
                )
        
        else:
            return TaskResponse(
                success=False,
                message=f"Unknown command: {command.action}"
            )
            
    except Exception as e:
        logger.error(f"Failed to execute task command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=TaskHealthCheck)
async def get_task_health():
    """Get task system health check."""
    try:
        scheduler = get_scheduler()
        task_manager = get_task_manager()
        
        health_check = await _get_health_check(scheduler, task_manager)
        return health_check
        
    except Exception as e:
        logger.error(f"Failed to get task health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskInfo)
async def get_task(task_id: str):
    """Get details of a specific task."""
    try:
        scheduler = get_scheduler()
        job = scheduler.get_job(task_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        task_stats = await scheduler.get_job_stats()
        
        return TaskInfo(
            task_id=job.id,
            name=job.name,
            task_type=_get_task_type(job.id),
            status=TaskStatus.SCHEDULED if job.next_run_time else TaskStatus.CANCELLED,
            enabled=not job.pending,
            next_run_time=job.next_run_time,
            trigger_info=str(job.trigger),
            pending=job.pending,
            configuration=_get_task_configuration(job),
            stats=_get_task_stats(job.id, task_stats.get("execution_stats", {}))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
def _get_task_type(task_id: str) -> TaskType:
    """Get task type from task ID."""
    if "stock_sync" in task_id:
        return TaskType.STOCK_SYNC
    elif "reddit" in task_id:
        return TaskType.SOCIAL_MEDIA_SYNC
    elif "discovery" in task_id:
        return TaskType.STOCK_DISCOVERY
    elif "cleanup" in task_id:
        return TaskType.CLEANUP
    elif "sentiment" in task_id:
        return TaskType.SENTIMENT_ANALYSIS
    else:
        return TaskType.STOCK_SYNC


def _get_task_configuration(job):
    """Get task configuration from job."""
    from app.tasks.models import TaskConfiguration
    
    return TaskConfiguration(
        task_id=job.id,
        task_type=_get_task_type(job.id),
        name=job.name,
        enabled=not job.pending,
        max_instances=job.max_instances,
        misfire_grace_time=job.misfire_grace_time
    )


def _get_task_stats(job_id: str, execution_stats: Dict[str, Any]):
    """Get task statistics from execution stats."""
    from app.tasks.models import TaskStats
    
    stats = execution_stats.get(job_id, {})
    
    total_executions = stats.get("total_executions", 0)
    successful_executions = stats.get("successful_executions", 0)
    
    success_rate = (successful_executions / total_executions) if total_executions > 0 else 0.0
    
    return TaskStats(
        task_id=job_id,
        task_name=job_id,
        total_executions=total_executions,
        successful_executions=successful_executions,
        failed_executions=stats.get("failed_executions", 0),
        last_execution=datetime.fromisoformat(stats["last_execution"]) if stats.get("last_execution") else None,
        last_success=datetime.fromisoformat(stats["last_success"]) if stats.get("last_success") else None,
        success_rate=success_rate
    )


async def _get_health_check(scheduler, task_manager) -> TaskHealthCheck:
    """Get comprehensive health check."""
    issues = []
    recommendations = []
    
    # Check scheduler
    scheduler_healthy = scheduler.is_running
    if not scheduler_healthy:
        issues.append("Task scheduler is not running")
        recommendations.append("Start the task scheduler")
    
    # Check Redis connection
    redis_healthy = True
    try:
        if scheduler.redis_client:
            await scheduler.redis_client.ping()
    except Exception:
        redis_healthy = False
        issues.append("Redis connection failed")
        recommendations.append("Check Redis server status")
    
    # Check database connection
    database_healthy = True
    try:
        from app.db.session import get_managed_session
        async with get_managed_session() as session:
            await session.execute("SELECT 1")
    except Exception:
        database_healthy = False
        issues.append("Database connection failed")
        recommendations.append("Check database server status")
    
    # Get task counts
    jobs = scheduler.get_jobs() if scheduler.is_running else []
    total_tasks = len(jobs)
    active_tasks = len([j for j in jobs if j.next_run_time])
    
    # Get stock sync stats
    try:
        sync_stats = await task_manager.get_sync_stats()
        last_successful_sync = None
        if sync_stats.get("recently_updated", 0) > 0:
            last_successful_sync = datetime.now()  # Approximate
    except Exception:
        sync_stats = {}
        last_successful_sync = None
    
    # Overall health
    healthy = scheduler_healthy and redis_healthy and database_healthy
    
    return TaskHealthCheck(
        healthy=healthy,
        scheduler_running=scheduler_healthy,
        redis_connected=redis_healthy,
        database_connected=database_healthy,
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        failed_tasks_last_24h=0,  # Would need to track this
        last_successful_sync=last_successful_sync,
        issues=issues,
        recommendations=recommendations
    )