"""APScheduler integration for scheduled test execution."""

import logging
from datetime import datetime
from typing import Callable
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger as APSCronTrigger
from apscheduler.triggers.date import DateTrigger as APSDateTrigger
from apscheduler.triggers.interval import IntervalTrigger as APSIntervalTrigger

from agent.models import (
    CronTrigger,
    DateTrigger,
    IntervalTrigger,
    ScheduleConfig,
    TriggerType,
)

logger = logging.getLogger(__name__)


class TestScheduler:
    """Manages scheduled test executions using APScheduler.

    Wraps APScheduler to provide a simple interface for scheduling
    test runs based on cron expressions or intervals.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self._scheduler = AsyncIOScheduler()
        self._callbacks: dict[str, Callable] = {}

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        """Check if scheduler is running."""
        return self._scheduler.running

    def _build_trigger(self, config: ScheduleConfig):
        """Build APScheduler trigger from config.

        Args:
            config: Schedule configuration

        Returns:
            APScheduler trigger instance
        """
        trigger = config.trigger

        if isinstance(trigger, CronTrigger):
            return APSCronTrigger(
                minute=trigger.minute,
                hour=trigger.hour,
                day=trigger.day,
                month=trigger.month,
                day_of_week=trigger.day_of_week,
                timezone=trigger.timezone,
            )
        elif isinstance(trigger, IntervalTrigger):
            kwargs = {}
            if trigger.seconds:
                kwargs["seconds"] = trigger.seconds
            if trigger.minutes:
                kwargs["minutes"] = trigger.minutes
            if trigger.hours:
                kwargs["hours"] = trigger.hours
            if trigger.days:
                kwargs["days"] = trigger.days
            return APSIntervalTrigger(**kwargs)
        elif isinstance(trigger, DateTrigger):
            return APSDateTrigger(run_date=trigger.run_date)
        else:
            raise ValueError(f"Unknown trigger type: {type(trigger)}")

    def add_schedule(
        self,
        config: ScheduleConfig,
        callback: Callable[[UUID], None],
    ) -> None:
        """Add a scheduled test.

        Args:
            config: Schedule configuration
            callback: Function to call when schedule triggers (receives schedule_id)
        """
        job_id = str(config.id)

        # Remove existing job if present
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        if not config.enabled:
            logger.info(f"Schedule {config.name} is disabled, not adding to scheduler")
            return

        trigger = self._build_trigger(config)

        def job_callback():
            callback(config.id)

        self._scheduler.add_job(
            job_callback,
            trigger=trigger,
            id=job_id,
            name=config.name,
            replace_existing=True,
        )
        self._callbacks[job_id] = callback
        logger.info(f"Added schedule: {config.name} ({job_id})")

    def remove_schedule(self, schedule_id: UUID) -> bool:
        """Remove a scheduled test.

        Args:
            schedule_id: Schedule ID to remove

        Returns:
            True if removed, False if not found
        """
        job_id = str(schedule_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            self._callbacks.pop(job_id, None)
            logger.info(f"Removed schedule: {job_id}")
            return True
        return False

    def pause_schedule(self, schedule_id: UUID) -> bool:
        """Pause a scheduled test.

        Args:
            schedule_id: Schedule ID to pause

        Returns:
            True if paused, False if not found
        """
        job_id = str(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job:
            job.pause()
            logger.info(f"Paused schedule: {job_id}")
            return True
        return False

    def resume_schedule(self, schedule_id: UUID) -> bool:
        """Resume a paused schedule.

        Args:
            schedule_id: Schedule ID to resume

        Returns:
            True if resumed, False if not found
        """
        job_id = str(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job:
            job.resume()
            logger.info(f"Resumed schedule: {job_id}")
            return True
        return False

    def get_next_run_time(self, schedule_id: UUID) -> datetime | None:
        """Get the next scheduled run time.

        Args:
            schedule_id: Schedule ID

        Returns:
            Next run time or None if not scheduled
        """
        job_id = str(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None

    def list_jobs(self) -> list[dict]:
        """List all scheduled jobs.

        Returns:
            List of job info dictionaries
        """
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "pending": job.pending,
            })
        return jobs
