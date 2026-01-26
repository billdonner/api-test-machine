"""Request/response Pydantic schemas for the API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from engine.models import (
    DistributionStrategy,
    EndpointMetrics,
    EndpointSpec,
    HttpMethod,
    Metrics,
    RequestResult,
    RunStatus,
    TestSpec,
    Thresholds,
)


# Request models
class CreateRunRequest(BaseModel):
    """Request to start a new test run."""
    spec: TestSpec


class CancelRunRequest(BaseModel):
    """Request to cancel a running test."""
    pass  # No body needed, run_id comes from path


# Response models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RunSummary(BaseModel):
    """Summary of a test run for list views."""
    id: UUID
    name: str
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    total_requests: int
    requests_completed: int
    passed: bool | None


class RequestSummary(BaseModel):
    """Summary of a single request for list views."""
    request_number: int
    status_code: int | None
    latency_ms: float
    error: str | None
    timestamp: datetime
    response_size_bytes: int | None
    endpoint_name: str | None = None


class RequestDetail(BaseModel):
    """Full details of a single request."""
    request_number: int
    status_code: int | None
    latency_ms: float
    error: str | None
    timestamp: datetime
    response_size_bytes: int | None
    endpoint_name: str | None = None
    request_url: str | None
    request_method: str | None
    request_headers: dict[str, str] | None
    request_body: str | None
    response_headers: dict[str, str] | None
    response_body: str | None


class RunDetail(BaseModel):
    """Full details of a test run."""
    id: UUID
    spec: TestSpec
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    metrics: Metrics
    passed: bool | None
    failure_reasons: list[str]
    requests_completed: int
    error_message: str | None
    sampled_requests: list[RequestSummary] = Field(default_factory=list)
    endpoint_metrics: list[EndpointMetrics] = Field(default_factory=list)


class RunListResponse(BaseModel):
    """Response for listing runs."""
    runs: list[RunSummary]
    total: int


class CreateRunResponse(BaseModel):
    """Response when creating a new run."""
    id: UUID
    status: RunStatus
    message: str = "Run started"


class CancelRunResponse(BaseModel):
    """Response when cancelling a run."""
    id: UUID
    status: RunStatus
    message: str


class DeleteRunResponse(BaseModel):
    """Response when deleting a run."""
    id: UUID
    message: str = "Run deleted"


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None


# Storage status models
class RunsByDay(BaseModel):
    """Runs count by day."""
    date: str
    count: int
    passed: int
    failed: int


class RunsByStatus(BaseModel):
    """Runs grouped by status."""
    status: str
    count: int


class TestConfigResponse(BaseModel):
    """Test configuration with enabled status."""
    name: str
    enabled: bool
    spec: TestSpec
    created_at: datetime | None
    updated_at: datetime | None


class TestConfigListResponse(BaseModel):
    """List of test configurations."""
    configs: list[TestConfigResponse]
    total: int


class SetEnabledRequest(BaseModel):
    """Request to set test enabled status."""
    enabled: bool


class SetEnabledResponse(BaseModel):
    """Response after setting enabled status."""
    name: str
    enabled: bool
    message: str


class BatchRunRequest(BaseModel):
    """Request to run all enabled tests."""
    pass  # No body needed


class BatchRunResult(BaseModel):
    """Result of a single test in a batch run."""
    name: str
    run_id: UUID
    status: RunStatus
    passed: bool | None = None
    error_message: str | None = None
    latency_p95_ms: float | None = None
    requests_completed: int = 0
    total_requests: int = 0


class BatchRunResponse(BaseModel):
    """Response from batch run."""
    batch_id: str
    total_tests: int
    started_at: datetime
    completed_at: datetime | None = None
    results: list[BatchRunResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class StorageStatusResponse(BaseModel):
    """Detailed storage status response."""
    storage_type: str
    database_path: str | None
    database_size_bytes: int | None
    database_size_human: str | None
    sqlite_version: str | None

    # Counts
    total_runs: int
    runs_by_status: list[RunsByStatus]
    runs_by_day: list[RunsByDay]

    # Storage metrics
    total_requests_stored: int
    avg_requests_per_run: float
    oldest_run_date: datetime | None
    newest_run_date: datetime | None

    # Top tests by run count
    top_tests: list[dict]

    # Performance metrics
    avg_run_duration_seconds: float | None
    total_data_transferred_bytes: int
