"""
Task scheduler management using APScheduler.

Provides a centralized scheduler for background tasks with Redis persistence
and comprehensive monitoring capabilities.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.job import Job
import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TaskScheduler:
    """Manages background task scheduling with Redis persistence."""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.redis_client: Optional[redis.Redis] = None
        self._is_running = False
        
    async def initialize(self) -> None:
        """Initialize the scheduler with Redis persistence."""
        try:
            # Initialize Redis client for task storage
            self.redis_client = redis.from_url(
                settings.REDIS_URL.replace(f"/{settings.REDIS_DB}", f"/{settings.TASK_REDIS_DB}"),
                decode_responses=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection for task scheduler established")
            
            # Configure job store
            jobstore = RedisJobStore(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.TASK_REDIS_DB,
                password=settings.REDIS_PASSWORD
            ) if settings.TASK_PERSISTENCE_ENABLED else None
            
            # Configure scheduler
            self.scheduler = AsyncIOScheduler(
                jobstores={'default': jobstore} if jobstore else {},
                executors={'default': AsyncIOExecutor()},
                job_defaults={
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 30
                }
            )
            
            # Add event listeners
            self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
            self.scheduler.add_listener(self._job_missed, EVENT_JOB_MISSED)
            
            logger.info("Task scheduler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize task scheduler: {e}")
            raise
    
    async def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler:
            await self.initialize()
        
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Task scheduler started")
    
    async def shutdown(self) -> None:
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self._is_running:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Task scheduler stopped")
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    def add_job(
        self,
        func,
        trigger: str,
        id: str,
        name: str,
        **kwargs
    ) -> Job:
        """Add a job to the scheduler."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=id,
            name=name,
            replace_existing=True,
            **kwargs
        )
        
        logger.info(f"Job '{name}' ({id}) added to scheduler")
        return job
    
    def remove_job(self, job_id: str) -> None:
        """Remove a job from the scheduler."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job {job_id} removed from scheduler")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
    
    def get_jobs(self) -> List[Job]:
        """Get all scheduled jobs."""
        if not self.scheduler:
            return []
        
        return self.scheduler.get_jobs()
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a specific job by ID."""
        if not self.scheduler:
            return None
        
        return self.scheduler.get_job(job_id)
    
    async def get_job_stats(self) -> Dict[str, Any]:
        """Get comprehensive job statistics."""
        if not self.scheduler:
            return {"error": "Scheduler not initialized"}
        
        jobs = self.get_jobs()
        
        # Get execution stats from Redis
        execution_stats = {}
        if self.redis_client:
            try:
                keys = await self.redis_client.keys("task_stats:*")
                for key in keys:
                    job_id = key.split(":")[-1]
                    stats = await self.redis_client.hgetall(key)
                    execution_stats[job_id] = {
                        "total_executions": int(stats.get("total_executions", 0)),
                        "successful_executions": int(stats.get("successful_executions", 0)),
                        "failed_executions": int(stats.get("failed_executions", 0)),
                        "last_execution": stats.get("last_execution"),
                        "last_success": stats.get("last_success"),
                        "last_error": stats.get("last_error")
                    }
            except Exception as e:
                logger.warning(f"Failed to get execution stats: {e}")
        
        return {
            "scheduler_running": self._is_running,
            "total_jobs": len(jobs),
            "job_details": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "pending": job.pending
                }
                for job in jobs
            ],
            "execution_stats": execution_stats
        }
    
    async def _job_executed(self, event) -> None:
        """Handle job execution event."""
        if self.redis_client:
            try:
                await self.redis_client.hincrby(f"task_stats:{event.job_id}", "total_executions", 1)
                await self.redis_client.hincrby(f"task_stats:{event.job_id}", "successful_executions", 1)
                await self.redis_client.hset(f"task_stats:{event.job_id}", "last_execution", datetime.now().isoformat())
                await self.redis_client.hset(f"task_stats:{event.job_id}", "last_success", datetime.now().isoformat())
                await self.redis_client.expire(f"task_stats:{event.job_id}", 86400 * 7)  # Keep for 7 days
            except Exception as e:
                logger.warning(f"Failed to update job stats: {e}")
        
        logger.info(f"Job {event.job_id} executed successfully")
    
    async def _job_error(self, event) -> None:
        """Handle job error event."""
        if self.redis_client:
            try:
                await self.redis_client.hincrby(f"task_stats:{event.job_id}", "total_executions", 1)
                await self.redis_client.hincrby(f"task_stats:{event.job_id}", "failed_executions", 1)
                await self.redis_client.hset(f"task_stats:{event.job_id}", "last_execution", datetime.now().isoformat())
                await self.redis_client.hset(f"task_stats:{event.job_id}", "last_error", str(event.exception))
                await self.redis_client.expire(f"task_stats:{event.job_id}", 86400 * 7)  # Keep for 7 days
            except Exception as e:
                logger.warning(f"Failed to update job stats: {e}")
        
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    
    async def _job_missed(self, event) -> None:
        """Handle job missed event."""
        logger.warning(f"Job {event.job_id} missed execution at {event.scheduled_run_time}")
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running


# Global scheduler instance
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


@asynccontextmanager
async def scheduler_lifespan():
    """Context manager for scheduler lifecycle."""
    scheduler = get_scheduler()
    await scheduler.start()
    try:
        yield scheduler
    finally:
        await scheduler.shutdown()