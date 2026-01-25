"""Pydantic models for the agent scheduler."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.models import TestSpec


class TriggerType(str, Enum):
    """Types of schedule triggers."""
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"


class CronTrigger(BaseModel):
    """Cron-style schedule trigger."""
    type: TriggerType = TriggerType.CRON
    minute: str = "*"
    hour: str = "*"
    day: str = "*"
    month: str = "*"
    day_of_week: str = "*"
    timezone: str = "UTC"


class IntervalTrigger(BaseModel):
    """Interval-based schedule trigger."""
    type: TriggerType = TriggerType.INTERVAL
    seconds: int | None = None
    minutes: int | None = None
    hours: int | None = None
    days: int | None = None


class DateTrigger(BaseModel):
    """One-time date trigger."""
    type: TriggerType = TriggerType.DATE
    run_date: datetime


class ScheduleConfig(BaseModel):
    """Configuration for a scheduled test."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1)
    description: str | None = None
    enabled: bool = True

    # Test to run
    spec: TestSpec

    # Schedule trigger (one of the trigger types)
    trigger: CronTrigger | IntervalTrigger | DateTrigger

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Tags for organization
    tags: list[str] = Field(default_factory=list)


class ScheduledTestRun(BaseModel):
    """Record of a scheduled test execution."""
    id: UUID = Field(default_factory=uuid4)
    schedule_id: UUID
    run_id: UUID | None = None
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "triggered"  # triggered, started, completed, failed
    error: str | None = None


class AgentState(BaseModel):
    """Persistent state for the agent."""
    schedules: dict[str, ScheduleConfig] = Field(default_factory=dict)
    recent_runs: list[ScheduledTestRun] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    def add_schedule(self, config: ScheduleConfig) -> None:
        """Add or update a schedule."""
        self.schedules[str(config.id)] = config
        self.last_updated = datetime.utcnow()

    def remove_schedule(self, schedule_id: UUID) -> bool:
        """Remove a schedule by ID."""
        key = str(schedule_id)
        if key in self.schedules:
            del self.schedules[key]
            self.last_updated = datetime.utcnow()
            return True
        return False

    def get_schedule(self, schedule_id: UUID) -> ScheduleConfig | None:
        """Get a schedule by ID."""
        return self.schedules.get(str(schedule_id))

    def add_run_record(self, run: ScheduledTestRun) -> None:
        """Add a run record, keeping only the most recent 100."""
        self.recent_runs.insert(0, run)
        self.recent_runs = self.recent_runs[:100]
        self.last_updated = datetime.utcnow()
