"""REST API routes for the Control API."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.auth import ApiKeyDep
from api.models import (
    BatchRunRequest,
    BatchRunResponse,
    BatchRunResult,
    CancelRunResponse,
    CreateRunRequest,
    CreateRunResponse,
    DeleteRunResponse,
    ErrorResponse,
    HealthResponse,
    RequestDetail,
    RequestSummary,
    RunDetail,
    RunListResponse,
    RunSummary,
    SetEnabledRequest,
    SetEnabledResponse,
    StorageStatusResponse,
    TestConfigListResponse,
    TestConfigResponse,
)
from api.storage_base import StorageInterface
from engine.executor import TestExecutor
from engine.models import RunResult, RunStatus

from datetime import datetime
from uuid import uuid4

# Create routers
health_router = APIRouter(tags=["health"])
runs_router = APIRouter(prefix="/runs", tags=["runs"])
storage_router = APIRouter(prefix="/storage", tags=["storage"])
tests_router = APIRouter(prefix="/tests", tags=["tests"])

# Shared state (initialized in app lifespan)
executor: TestExecutor | None = None
storage: StorageInterface | None = None


def get_executor() -> TestExecutor:
    """Get the test executor instance."""
    if executor is None:
        raise RuntimeError("Executor not initialized")
    return executor


def get_storage() -> StorageInterface:
    """Get the storage instance."""
    if storage is None:
        raise RuntimeError("Storage not initialized")
    return storage


def init_dependencies(exec: TestExecutor, store: StorageInterface) -> None:
    """Initialize shared dependencies.

    Args:
        exec: TestExecutor instance
        store: Storage instance (SQLite or JSON)
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
    await store.save(result)

    # Define background task
    async def run_test():
        try:
            final_result = await exec.run(request.spec, run_id=result.id)
            await store.save(final_result)
            # Update test config with latest spec
            await store.save_test_config(
                request.spec.name,
                request.spec.model_dump(mode="json"),
                enabled=True,
            )
        except Exception as e:
            # Update with failure
            result.status = RunStatus.FAILED
            result.error_message = str(e)
            await store.save(result)

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
    exec = get_executor()
    runs, total = await store.list_runs(limit=limit, offset=offset, status_filter=status_filter)

    # Build summaries, checking active runs for live status
    summaries = []
    for r in runs:
        # Check if this run is currently active (for live progress)
        active = exec.get_active_run(r.id)
        if active:
            summaries.append(RunSummary(
                id=active.id,
                name=active.spec.name,
                status=active.status,
                started_at=active.started_at,
                completed_at=active.completed_at,
                total_requests=active.spec.total_requests,
                requests_completed=active.requests_completed,
                passed=active.passed,
            ))
        else:
            summaries.append(RunSummary(
                id=r.id,
                name=r.spec.name,
                status=r.status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                total_requests=r.spec.total_requests,
                requests_completed=r.requests_completed,
                passed=r.passed,
            ))

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
        sampled = [
            RequestSummary(
                request_number=r.request_number,
                status_code=r.status_code,
                latency_ms=r.latency_ms,
                error=r.error,
                timestamp=r.timestamp,
                response_size_bytes=r.response_size_bytes,
            )
            for r in active.sampled_requests
        ]
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
            sampled_requests=sampled,
        )

    # Load from storage
    result = await store.load(run_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    sampled = [
        RequestSummary(
            request_number=r.request_number,
            status_code=r.status_code,
            latency_ms=r.latency_ms,
            error=r.error,
            timestamp=r.timestamp,
            response_size_bytes=r.response_size_bytes,
        )
        for r in result.sampled_requests
    ]

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
        sampled_requests=sampled,
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
    result = await store.load(run_id)
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


@runs_router.get(
    "/{run_id}/requests/{request_number}",
    response_model=RequestDetail,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_request_detail(
    run_id: UUID,
    request_number: int,
    api_key: ApiKeyDep,
) -> RequestDetail:
    """Get full details of a specific request including headers and body."""
    store = get_storage()
    exec = get_executor()

    # Check active runs first
    active = exec.get_active_run(run_id)
    sampled_requests = []
    if active:
        sampled_requests = active.sampled_requests
    else:
        result = await store.load(run_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found",
            )
        sampled_requests = result.sampled_requests

    # Find the specific request
    for req in sampled_requests:
        if req.request_number == request_number:
            return RequestDetail(
                request_number=req.request_number,
                status_code=req.status_code,
                latency_ms=req.latency_ms,
                error=req.error,
                timestamp=req.timestamp,
                response_size_bytes=req.response_size_bytes,
                request_url=req.request_url,
                request_method=req.request_method,
                request_headers=req.request_headers,
                request_body=req.request_body,
                response_headers=req.response_headers,
                response_body=req.response_body,
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Request {request_number} not found in sampled requests for run {run_id}",
    )


@runs_router.delete(
    "/{run_id}",
    response_model=DeleteRunResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def delete_run(
    run_id: UUID,
    api_key: ApiKeyDep,
) -> DeleteRunResponse:
    """Delete a test run and its results.

    Cannot delete a currently running test - cancel it first.
    """
    exec = get_executor()
    store = get_storage()

    # Check if run is currently active
    if exec.get_active_run(run_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run {run_id} is currently running. Cancel it first.",
        )

    # Try to delete from storage
    deleted = await store.delete(run_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return DeleteRunResponse(id=run_id)


# Storage status endpoint
@storage_router.get(
    "/status",
    response_model=StorageStatusResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_storage_status(
    api_key: ApiKeyDep,
) -> StorageStatusResponse:
    """Get detailed storage status and statistics."""
    store = get_storage()
    stats = await store.get_detailed_stats()
    return StorageStatusResponse(**stats)


# Test configuration endpoints
@tests_router.get(
    "",
    response_model=TestConfigListResponse,
    responses={401: {"model": ErrorResponse}},
)
async def list_test_configs(
    api_key: ApiKeyDep,
    enabled_only: bool = Query(default=False),
) -> TestConfigListResponse:
    """List all saved test configurations."""
    store = get_storage()
    configs = await store.list_test_configs(enabled_only=enabled_only)

    from engine.models import TestSpec

    config_responses = []
    for c in configs:
        try:
            spec = TestSpec.model_validate(c["spec"])
            config_responses.append(TestConfigResponse(
                name=c["name"],
                enabled=c["enabled"],
                spec=spec,
                created_at=c.get("created_at"),
                updated_at=c.get("updated_at"),
                run_count=c.get("run_count", 0),
            ))
        except Exception:
            # Skip invalid configs
            continue

    return TestConfigListResponse(configs=config_responses, total=len(config_responses))


@tests_router.post(
    "/{name}/enabled",
    response_model=SetEnabledResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def set_test_enabled(
    name: str,
    request: SetEnabledRequest,
    api_key: ApiKeyDep,
) -> SetEnabledResponse:
    """Enable or disable a test for batch runs."""
    store = get_storage()

    # Try to update existing config
    updated = await store.set_test_enabled(name, request.enabled)

    if not updated:
        # Config doesn't exist - try to create from most recent run
        runs, _ = await store.list_runs(limit=1000, name_filter=name)
        if not runs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test '{name}' not found",
            )

        # Create config from most recent run
        latest_run = runs[0]
        await store.save_test_config(
            name=name,
            spec=latest_run.spec.model_dump(mode="json"),
            enabled=request.enabled,
        )

    return SetEnabledResponse(
        name=name,
        enabled=request.enabled,
        message=f"Test '{name}' {'enabled' if request.enabled else 'disabled'}",
    )


@tests_router.post(
    "/sync",
    responses={401: {"model": ErrorResponse}},
)
async def sync_test_configs(
    api_key: ApiKeyDep,
) -> dict:
    """Sync test configs from existing runs.

    Creates test configs for all unique test names that don't have one yet.
    """
    store = get_storage()
    count = await store.sync_test_configs_from_runs()
    return {"message": f"Synced {count} test configs", "synced": count}


class RunAllRequest(BaseModel):
    """Request body for run-all endpoint."""
    repetitions: int = Field(default=1, ge=0, le=100, description="Number of times to run each test (0 = run once as specified)")
    max_concurrency: int = Field(default=0, ge=0, le=100, description="Max concurrency for all tests (0 = use test's specified concurrency)")


class BatchStartResponse(BaseModel):
    """Response for starting a batch run (async)."""
    batch_id: str
    total_tests: int
    run_ids: list[UUID]
    message: str


@tests_router.post(
    "/run-all",
    response_model=BatchStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={401: {"model": ErrorResponse}},
)
async def run_all_enabled_tests(
    api_key: ApiKeyDep,
    request: RunAllRequest | None = None,
) -> BatchStartResponse:
    """Run all enabled tests asynchronously.

    Tests are launched in the background. Use GET /runs to monitor progress.
    """
    store = get_storage()
    exec = get_executor()

    repetitions = request.repetitions if request else 1
    max_concurrency = request.max_concurrency if request else 0
    # Treat 0 as 1 (run once as specified)
    if repetitions == 0:
        repetitions = 1

    # Get all enabled test configs
    configs = await store.list_test_configs(enabled_only=True)

    if not configs:
        return BatchStartResponse(
            batch_id=str(uuid4()),
            total_tests=0,
            run_ids=[],
            message="No enabled tests to run",
        )

    batch_id = str(uuid4())
    run_ids: list[UUID] = []

    from engine.models import TestSpec

    # Create all runs and launch them asynchronously
    for rep in range(repetitions):
        for config in configs:
            try:
                spec = TestSpec.model_validate(config["spec"])

                # Apply max concurrency override if specified
                if max_concurrency > 0 and spec.concurrency > max_concurrency:
                    spec.concurrency = max_concurrency

                # Create initial result
                result = RunResult(spec=spec, status=RunStatus.PENDING)
                await store.save(result)
                run_ids.append(result.id)

                # Define background task for this test
                async def run_test(run_result: RunResult, test_spec: TestSpec, config_name: str):
                    try:
                        final_result = await exec.run(test_spec, run_id=run_result.id)
                        await store.save(final_result)
                    except Exception as e:
                        run_result.status = RunStatus.FAILED
                        run_result.error_message = str(e)
                        await store.save(run_result)

                # Schedule background execution (fire and forget)
                asyncio.create_task(run_test(result, spec, config["name"]))

            except Exception as e:
                # Invalid spec - create a failed result
                failed_result = RunResult(
                    spec=TestSpec(name=config["name"], url="invalid"),
                    status=RunStatus.FAILED,
                )
                failed_result.error_message = f"Invalid spec: {e}"
                await store.save(failed_result)
                run_ids.append(failed_result.id)

    return BatchStartResponse(
        batch_id=batch_id,
        total_tests=len(run_ids),
        run_ids=run_ids,
        message=f"Started {len(run_ids)} test(s) in background",
    )


@tests_router.get(
    "/report",
    responses={401: {"model": ErrorResponse}},
)
async def get_test_report(
    api_key: ApiKeyDep,
    enabled_only: bool = Query(default=False),
) -> Response:
    """Generate a PDF report of all test configurations.

    Returns a PDF document with:
    - Summary page with test counts
    - Detailed section for each test with configuration and thresholds
    """
    from api.reports import generate_test_report_pdf

    store = get_storage()
    configs = await store.list_test_configs(enabled_only=enabled_only)

    # Convert to list of dicts for the PDF generator
    config_dicts = []
    for c in configs:
        config_dicts.append({
            "name": c["name"],
            "enabled": c["enabled"],
            "spec": c["spec"],
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
            "run_count": c.get("run_count", 0),
        })

    pdf_bytes = generate_test_report_pdf(config_dicts)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=test-report.pdf"
        }
    )
