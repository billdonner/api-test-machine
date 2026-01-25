"""REST API routes for the Control API."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from api.auth import ApiKeyDep
from api.models import (
    CancelRunResponse,
    CreateRunRequest,
    CreateRunResponse,
    ErrorResponse,
    HealthResponse,
    RunDetail,
    RunListResponse,
    RunSummary,
)
from api.storage import RunStorage
from engine.executor import TestExecutor
from engine.models import RunResult, RunStatus

# Create routers
health_router = APIRouter(tags=["health"])
runs_router = APIRouter(prefix="/runs", tags=["runs"])

# Shared state (initialized in app lifespan)
executor: TestExecutor | None = None
storage: RunStorage | None = None


def get_executor() -> TestExecutor:
    """Get the test executor instance."""
    if executor is None:
        raise RuntimeError("Executor not initialized")
    return executor


def get_storage() -> RunStorage:
    """Get the storage instance."""
    if storage is None:
        raise RuntimeError("Storage not initialized")
    return storage


def init_dependencies(exec: TestExecutor, store: RunStorage) -> None:
    """Initialize shared dependencies.

    Args:
        exec: TestExecutor instance
        store: RunStorage instance
    """
    global executor, storage
    executor = exec
    storage = store


# Health endpoint (no auth required)
@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    return HealthResponse()


# Runs endpoints (auth required)
@runs_router.post(
    "",
    response_model=CreateRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={401: {"model": ErrorResponse}},
)
async def create_run(
    request: CreateRunRequest,
    api_key: ApiKeyDep,
) -> CreateRunResponse:
    """Start a new test run.

    The test runs in the background. Use GET /runs/{id} to check status.
    """
    exec = get_executor()
    store = get_storage()

    # Create initial result
    result = RunResult(spec=request.spec, status=RunStatus.PENDING)

    # Save initial state
    store.save(result)

    # Define background task
    async def run_test():
        try:
            final_result = await exec.run(request.spec, run_id=result.id)
            store.save(final_result)
        except Exception as e:
            # Update with failure
            result.status = RunStatus.FAILED
            result.error_message = str(e)
            store.save(result)

    # Schedule background execution (fire and forget)
    asyncio.create_task(run_test())

    return CreateRunResponse(
        id=result.id,
        status=RunStatus.PENDING,
        message="Run started",
    )


@runs_router.get(
    "",
    response_model=RunListResponse,
    responses={401: {"model": ErrorResponse}},
)
async def list_runs(
    api_key: ApiKeyDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: RunStatus | None = Query(default=None, alias="status"),
) -> RunListResponse:
    """List recent test runs."""
    store = get_storage()
    runs, total = store.list_runs(limit=limit, offset=offset, status_filter=status_filter)

    summaries = [
        RunSummary(
            id=r.id,
            name=r.spec.name,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            total_requests=r.spec.total_requests,
            requests_completed=r.requests_completed,
            passed=r.passed,
        )
        for r in runs
    ]

    return RunListResponse(runs=summaries, total=total)


@runs_router.get(
    "/{run_id}",
    response_model=RunDetail,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_run(
    run_id: UUID,
    api_key: ApiKeyDep,
) -> RunDetail:
    """Get details of a specific test run."""
    store = get_storage()
    exec = get_executor()

    # Check active runs first (for live progress)
    active = exec.get_active_run(run_id)
    if active:
        return RunDetail(
            id=active.id,
            spec=active.spec,
            status=active.status,
            started_at=active.started_at,
            completed_at=active.completed_at,
            metrics=active.metrics,
            passed=active.passed,
            failure_reasons=active.failure_reasons,
            requests_completed=active.requests_completed,
            error_message=active.error_message,
        )

    # Load from storage
    result = store.load(run_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return RunDetail(
        id=result.id,
        spec=result.spec,
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        metrics=result.metrics,
        passed=result.passed,
        failure_reasons=result.failure_reasons,
        requests_completed=result.requests_completed,
        error_message=result.error_message,
    )


@runs_router.post(
    "/{run_id}/cancel",
    response_model=CancelRunResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def cancel_run(
    run_id: UUID,
    api_key: ApiKeyDep,
) -> CancelRunResponse:
    """Cancel a running test."""
    exec = get_executor()
    store = get_storage()

    # Try to cancel
    cancelled = exec.cancel(run_id)

    if cancelled:
        return CancelRunResponse(
            id=run_id,
            status=RunStatus.CANCELLED,
            message="Cancellation requested",
        )

    # Check if run exists but is not active
    result = store.load(run_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if result.status in (RunStatus.COMPLETED, RunStatus.CANCELLED, RunStatus.FAILED):
        return CancelRunResponse(
            id=run_id,
            status=result.status,
            message=f"Run already {result.status.value}",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Run {run_id} not found or not running",
    )
