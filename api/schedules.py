"""Schedule API route handlers."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agent.models import (
    CronTrigger,
    DateTrigger,
    IntervalTrigger,
    ScheduleConfig,
    TriggerType,
)
from agent.orchestrator import TestOrchestrator
from api.auth import ApiKeyDep
from api.models import ErrorResponse
from engine.models import TestSpec

# Router
schedules_router = APIRouter(prefix="/schedules", tags=["schedules"])

# Shared orchestrator (initialized in app lifespan)
orchestrator: TestOrchestrator | None = None


def get_orchestrator() -> TestOrchestrator:
    """Get the orchestrator instance."""
    if orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return orchestrator


def init_orchestrator(orch: TestOrchestrator) -> None:
    """Initialize the shared orchestrator.

    Args:
        orch: TestOrchestrator instance
    """
    global orchestrator
    orchestrator = orch


# Request/Response Models


class IntervalTriggerRequest(BaseModel):
    """Interval trigger for schedule creation."""
    type: str = "interval"
    seconds: int | None = None
    minutes: int | None = None
    hours: int | None = None
    days: int | None = None


class CronTriggerRequest(BaseModel):
    """Cron trigger for schedule creation."""
    type: str = "cron"
    minute: str = "*"
    hour: str = "*"
    day: str = "*"
    month: str = "*"
    day_of_week: str = "*"
    timezone: str = "UTC"


class DateTriggerRequest(BaseModel):
    """One-time date trigger for schedule creation."""
    type: str = "date"
    run_date: datetime


class CreateScheduleRequest(BaseModel):
    """Request to create a new schedule."""
    name: str = Field(..., min_length=1)
    description: str | None = None
    test_name: str = Field(..., min_length=1, description="Name of the test configuration to run")
    spec: TestSpec | None = Field(None, description="Full test spec (if not using test_name lookup)")
    trigger: IntervalTriggerRequest | CronTriggerRequest | DateTriggerRequest
    max_runs: int | None = Field(None, description="Maximum number of runs (null = indefinite)")
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    """Response for a single schedule."""
    id: str
    name: str
    description: str | None
    test_name: str
    trigger_type: str
    trigger: dict
    max_runs: int | None
    run_count: int
    enabled: bool
    paused: bool
    next_run_time: str | None
    created_at: datetime
    updated_at: datetime
    tags: list[str]


class ScheduleListResponse(BaseModel):
    """Response for listing schedules."""
    schedules: list[ScheduleResponse]
    total: int


class ScheduleActionResponse(BaseModel):
    """Response for schedule actions (pause, resume, delete)."""
    id: str
    action: str
    success: bool
    message: str


def _build_trigger(trigger_req: IntervalTriggerRequest | CronTriggerRequest | DateTriggerRequest):
    """Build a trigger model from request."""
    if isinstance(trigger_req, DateTriggerRequest) or trigger_req.type == "date":
        return DateTrigger(run_date=trigger_req.run_date)  # type: ignore
    elif isinstance(trigger_req, CronTriggerRequest) or trigger_req.type == "cron":
        return CronTrigger(
            minute=trigger_req.minute,  # type: ignore
            hour=trigger_req.hour,  # type: ignore
            day=trigger_req.day,  # type: ignore
            month=trigger_req.month,  # type: ignore
            day_of_week=trigger_req.day_of_week,  # type: ignore
            timezone=trigger_req.timezone,  # type: ignore
        )
    else:  # interval
        return IntervalTrigger(
            seconds=trigger_req.seconds,  # type: ignore
            minutes=trigger_req.minutes,  # type: ignore
            hours=trigger_req.hours,  # type: ignore
            days=trigger_req.days,  # type: ignore
        )


def _schedule_to_response(config: ScheduleConfig, orch: TestOrchestrator) -> ScheduleResponse:
    """Convert a ScheduleConfig to a ScheduleResponse."""
    status_info = orch.get_schedule_status(config.id)
    next_run = status_info.get("next_run_time") if status_info else None
    is_paused = status_info.get("paused", False) if status_info else False

    trigger_dict = config.trigger.model_dump()

    return ScheduleResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        test_name=config.spec.name,
        trigger_type=config.trigger.type.value,
        trigger=trigger_dict,
        max_runs=config.max_runs,
        run_count=config.run_count,
        enabled=config.enabled,
        paused=is_paused,
        next_run_time=next_run,
        created_at=config.created_at,
        updated_at=config.updated_at,
        tags=config.tags,
    )


# Endpoints


@schedules_router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def create_schedule(
    request: CreateScheduleRequest,
    api_key: ApiKeyDep,
) -> ScheduleResponse:
    """Create a new scheduled test.

    Either provide a full `spec` or use `test_name` to reference an existing test.
    """
    orch = get_orchestrator()

    # Get or build the test spec
    if request.spec:
        spec = request.spec
    else:
        # Look up test config by name
        from api.routes import get_storage
        store = get_storage()
        configs = await store.list_test_configs()
        matching = [c for c in configs if c["name"] == request.test_name]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Test '{request.test_name}' not found",
            )
        spec = TestSpec.model_validate(matching[0]["spec"])

    # Build trigger
    trigger = _build_trigger(request.trigger)

    # Create schedule config
    config = ScheduleConfig(
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        spec=spec,
        trigger=trigger,
        max_runs=request.max_runs,
        tags=request.tags,
    )

    # Add to orchestrator
    await orch.add_schedule(config)

    return _schedule_to_response(config, orch)


@schedules_router.get(
    "",
    response_model=ScheduleListResponse,
    responses={401: {"model": ErrorResponse}},
)
async def list_schedules(
    api_key: ApiKeyDep,
) -> ScheduleListResponse:
    """List all schedules."""
    orch = get_orchestrator()
    schedules = orch.list_schedules()

    responses = [_schedule_to_response(s, orch) for s in schedules]

    return ScheduleListResponse(schedules=responses, total=len(responses))


@schedules_router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_schedule(
    schedule_id: UUID,
    api_key: ApiKeyDep,
) -> ScheduleResponse:
    """Get a schedule by ID."""
    orch = get_orchestrator()
    config = orch.get_schedule(schedule_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    return _schedule_to_response(config, orch)


@schedules_router.delete(
    "/{schedule_id}",
    response_model=ScheduleActionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_schedule(
    schedule_id: UUID,
    api_key: ApiKeyDep,
) -> ScheduleActionResponse:
    """Delete (cancel) a schedule."""
    orch = get_orchestrator()

    removed = await orch.remove_schedule(schedule_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    return ScheduleActionResponse(
        id=str(schedule_id),
        action="delete",
        success=True,
        message="Schedule deleted",
    )


@schedules_router.post(
    "/{schedule_id}/pause",
    response_model=ScheduleActionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def pause_schedule(
    schedule_id: UUID,
    api_key: ApiKeyDep,
) -> ScheduleActionResponse:
    """Pause a schedule."""
    orch = get_orchestrator()

    paused = await orch.pause_schedule(schedule_id)

    if not paused:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found or not running",
        )

    return ScheduleActionResponse(
        id=str(schedule_id),
        action="pause",
        success=True,
        message="Schedule paused",
    )


@schedules_router.post(
    "/{schedule_id}/resume",
    response_model=ScheduleActionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def resume_schedule(
    schedule_id: UUID,
    api_key: ApiKeyDep,
) -> ScheduleActionResponse:
    """Resume a paused schedule."""
    orch = get_orchestrator()

    resumed = await orch.resume_schedule(schedule_id)

    if not resumed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found or not paused",
        )

    return ScheduleActionResponse(
        id=str(schedule_id),
        action="resume",
        success=True,
        message="Schedule resumed",
    )
