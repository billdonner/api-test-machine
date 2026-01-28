"""Orchestrator for coordinating scheduled test runs."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

import httpx

from agent.models import AgentState, ScheduleConfig, ScheduledTestRun
from agent.scheduler import TestScheduler
from agent.storage import AgentStorage

logger = logging.getLogger(__name__)


class TestOrchestrator:
    """Coordinates scheduled test execution.

    The orchestrator manages the lifecycle of scheduled tests:
    - Loading/saving state
    - Adding/removing schedules
    - Triggering test runs via the Control API
    - Recording run history
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        api_key: str | None = None,
        storage: AgentStorage | None = None,
    ):
        """Initialize the orchestrator.

        Args:
            api_url: Control API URL
            api_key: API key for authentication
            storage: AgentStorage instance (creates default if None)
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.storage = storage or AgentStorage()
        self.scheduler = TestScheduler()
        self.state: AgentState | None = None
        self._http_client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Start the orchestrator and scheduler."""
        # Load state
        self.state = self.storage.load()
        logger.info(f"Loaded {len(self.state.schedules)} schedules")

        # Create HTTP client
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        self._http_client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=headers,
            timeout=30.0,
        )

        # Start scheduler
        self.scheduler.start()

        # Restore schedules
        for config in self.state.schedules.values():
            self.scheduler.add_schedule(config, self._on_schedule_trigger)

    async def stop(self) -> None:
        """Stop the orchestrator and save state."""
        self.scheduler.stop()
        if self.state:
            self.storage.save(self.state)
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Orchestrator stopped")

    def _on_schedule_trigger(self, schedule_id: UUID) -> None:
        """Handle schedule trigger (called by scheduler).

        Args:
            schedule_id: ID of the triggered schedule
        """
        # Schedule async execution
        asyncio.create_task(self._execute_scheduled_test(schedule_id))

    async def _execute_scheduled_test(self, schedule_id: UUID) -> None:
        """Execute a scheduled test.

        Args:
            schedule_id: ID of the schedule to execute
        """
        if not self.state:
            return

        config = self.state.get_schedule(schedule_id)
        if not config:
            logger.warning(f"Schedule {schedule_id} not found")
            return

        # Check if max_runs limit has been reached
        if config.max_runs is not None and config.run_count >= config.max_runs:
            logger.info(f"Schedule {config.name} reached max_runs limit ({config.max_runs})")
            # Disable the schedule and remove from scheduler
            config.enabled = False
            self.scheduler.remove_schedule(schedule_id)
            self.storage.save(self.state)
            return

        # Increment run count
        config.run_count += 1
        config.updated_at = datetime.utcnow()

        # Create run record
        run_record = ScheduledTestRun(
            schedule_id=schedule_id,
            status="triggered",
        )
        self.state.add_run_record(run_record)

        logger.info(f"Executing scheduled test: {config.name} (run {config.run_count}/{config.max_runs or '∞'})")

        try:
            # Start test via API
            if not self._http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self._http_client.post(
                "/api/v1/runs",
                json={"spec": config.spec.model_dump(mode="json")},
            )

            if response.status_code == 202:
                data = response.json()
                run_record.run_id = UUID(data["id"])
                run_record.status = "started"
                logger.info(f"Test started: {run_record.run_id}")
            else:
                run_record.status = "failed"
                run_record.error = f"API error: {response.status_code} - {response.text}"
                logger.error(f"Failed to start test: {run_record.error}")

        except Exception as e:
            run_record.status = "failed"
            run_record.error = str(e)
            logger.error(f"Failed to execute scheduled test: {e}")

        # Save state
        self.storage.save(self.state)

    async def add_schedule(self, config: ScheduleConfig) -> None:
        """Add a new schedule.

        Args:
            config: Schedule configuration
        """
        if not self.state:
            self.state = AgentState()

        self.state.add_schedule(config)
        self.scheduler.add_schedule(config, self._on_schedule_trigger)
        self.storage.save(self.state)
        logger.info(f"Added schedule: {config.name}")

    async def remove_schedule(self, schedule_id: UUID) -> bool:
        """Remove a schedule.

        Args:
            schedule_id: Schedule ID to remove

        Returns:
            True if removed, False if not found
        """
        if not self.state:
            return False

        removed_from_state = self.state.remove_schedule(schedule_id)
        removed_from_scheduler = self.scheduler.remove_schedule(schedule_id)

        if removed_from_state:
            self.storage.save(self.state)

        return removed_from_state or removed_from_scheduler

    async def update_schedule(self, config: ScheduleConfig) -> None:
        """Update an existing schedule.

        Args:
            config: Updated schedule configuration
        """
        await self.add_schedule(config)  # add_schedule handles updates

    def get_schedule(self, schedule_id: UUID) -> ScheduleConfig | None:
        """Get a schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            ScheduleConfig or None
        """
        if not self.state:
            return None
        return self.state.get_schedule(schedule_id)

    def list_schedules(self) -> list[ScheduleConfig]:
        """List all schedules.

        Returns:
            List of schedule configurations
        """
        if not self.state:
            return []
        return list(self.state.schedules.values())

    def get_recent_runs(self, limit: int = 20) -> list[ScheduledTestRun]:
        """Get recent scheduled run records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of run records
        """
        if not self.state:
            return []
        return self.state.recent_runs[:limit]

    def get_schedule_status(self, schedule_id: UUID) -> dict | None:
        """Get status of a schedule including next run time.

        Args:
            schedule_id: Schedule ID

        Returns:
            Status dict or None if not found
        """
        if not self.state:
            return None

        config = self.state.get_schedule(schedule_id)
        if not config:
            return None

        next_run = self.scheduler.get_next_run_time(schedule_id)
        job = self.scheduler._scheduler.get_job(str(schedule_id))
        is_paused = job is not None and job.next_run_time is None

        return {
            "id": str(schedule_id),
            "name": config.name,
            "enabled": config.enabled,
            "paused": is_paused,
            "next_run_time": next_run.isoformat() if next_run else None,
            "trigger_type": config.trigger.type.value,
            "max_runs": config.max_runs,
            "run_count": config.run_count,
        }

    async def pause_schedule(self, schedule_id: UUID) -> bool:
        """Pause a schedule.

        Args:
            schedule_id: Schedule ID to pause

        Returns:
            True if paused, False if not found
        """
        if not self.state:
            return False

        config = self.state.get_schedule(schedule_id)
        if not config:
            return False

        paused = self.scheduler.pause_schedule(schedule_id)
        if paused:
            self.storage.save(self.state)
        return paused

    async def resume_schedule(self, schedule_id: UUID) -> bool:
        """Resume a paused schedule.

        Args:
            schedule_id: Schedule ID to resume

        Returns:
            True if resumed, False if not found
        """
        if not self.state:
            return False

        config = self.state.get_schedule(schedule_id)
        if not config:
            return False

        resumed = self.scheduler.resume_schedule(schedule_id)
        if resumed:
            self.storage.save(self.state)
        return resumed
