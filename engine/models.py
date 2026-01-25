"""Pydantic models for the test engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engine.auth import AuthConfig, HttpUrl


class HttpMethod(str, Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class DistributionStrategy(str, Enum):
    """Strategy for distributing requests across multiple endpoints."""
    ROUND_ROBIN = "round_robin"  # Cycle through endpoints: A, B, C, A, B, C...
    WEIGHTED = "weighted"  # Distribute based on weights
    SEQUENTIAL = "sequential"  # All requests to A, then B, then C


class RunStatus(str, Enum):
    """Test run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Thresholds(BaseModel):
    """Pass/fail thresholds for test metrics."""
    max_latency_p50_ms: float | None = None
    max_latency_p95_ms: float | None = None
    max_latency_p99_ms: float | None = None
    max_error_rate: float | None = Field(None, ge=0.0, le=1.0)
    min_throughput_rps: float | None = None


class EndpointSpec(BaseModel):
    """Specification for a single endpoint in a multi-endpoint test."""
    name: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., description="Target URL for this endpoint")
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | dict[str, Any] | None = None
    weight: int = Field(default=1, ge=1, le=100, description="Weight for weighted distribution")
    expected_status_codes: list[int] = Field(default_factory=lambda: [200, 201, 204])


class TestSpec(BaseModel):
    """Specification for a load test."""
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None

    # Target configuration (single endpoint - for backward compatibility)
    url: str = Field(default="", description="Target URL (supports template variables)")
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | dict[str, Any] | None = None

    # Multi-endpoint configuration (optional)
    endpoints: list[EndpointSpec] | None = Field(
        default=None,
        description="List of endpoints for multi-endpoint tests"
    )
    distribution_strategy: DistributionStrategy = Field(
        default=DistributionStrategy.ROUND_ROBIN,
        description="Strategy for distributing requests across endpoints"
    )

    # Load configuration
    total_requests: int = Field(default=100, ge=1, le=1_000_000)
    concurrency: int = Field(default=10, ge=1, le=1000)
    requests_per_second: float | None = Field(None, ge=0.1, le=10000)

    # Timing
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)

    # Success criteria
    thresholds: Thresholds = Field(default_factory=Thresholds)
    expected_status_codes: list[int] = Field(default_factory=lambda: [200, 201, 204])

    # Template variables (user-provided values)
    variables: dict[str, str] = Field(default_factory=dict)

    # Authentication configuration
    auth: "AuthConfig | None" = Field(
        default=None,
        description="Authentication configuration for requests"
    )

    def get_endpoints(self) -> list[EndpointSpec]:
        """Get endpoints list, creating one from single-URL config if needed.

        This provides unified handling for both single-URL and multi-endpoint specs.

        Returns:
            List of EndpointSpec objects
        """
        if self.endpoints:
            return self.endpoints

        # Create a single endpoint from the legacy single-URL config
        return [
            EndpointSpec(
                name="default",
                url=self.url,
                method=self.method,
                headers=self.headers,
                body=self.body,
                weight=1,
                expected_status_codes=self.expected_status_codes,
            )
        ]

    def is_multi_endpoint(self) -> bool:
        """Check if this is a multi-endpoint test."""
        return self.endpoints is not None and len(self.endpoints) > 0


class RequestResult(BaseModel):
    """Result of a single HTTP request."""
    request_number: int
    status_code: int | None = None
    latency_ms: float
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_size_bytes: int | None = None

    # Multi-endpoint tracking
    endpoint_name: str | None = None

    # Detailed request/response data (optional, for sampling)
    request_url: str | None = None
    request_method: str | None = None
    request_headers: dict[str, str] | None = None
    request_body: str | None = None
    response_headers: dict[str, str] | None = None
    response_body: str | None = None


class Metrics(BaseModel):
    """Aggregated metrics for a test run."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Latency percentiles (milliseconds)
    latency_min_ms: float | None = None
    latency_max_ms: float | None = None
    latency_mean_ms: float | None = None
    latency_p50_ms: float | None = None
    latency_p90_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None

    # Throughput
    requests_per_second: float | None = None
    duration_seconds: float | None = None

    # Error breakdown
    error_rate: float | None = None
    errors_by_type: dict[str, int] = Field(default_factory=dict)
    status_code_counts: dict[int, int] = Field(default_factory=dict)

    # Data transfer
    total_bytes_received: int = 0


class EndpointMetrics(BaseModel):
    """Metrics for a specific endpoint in a multi-endpoint test."""
    endpoint_name: str
    metrics: "Metrics"


class RunResult(BaseModel):
    """Complete result of a test run."""
    id: UUID = Field(default_factory=uuid4)
    spec: TestSpec
    status: RunStatus = RunStatus.PENDING

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    metrics: Metrics = Field(default_factory=Metrics)
    passed: bool | None = None
    failure_reasons: list[str] = Field(default_factory=list)

    # Per-endpoint metrics (for multi-endpoint tests)
    endpoint_metrics: list[EndpointMetrics] = Field(default_factory=list)

    # Progress
    requests_completed: int = 0

    # Error message if status is FAILED
    error_message: str | None = None

    # Sampled request/response data (stores first N and any failures)
    sampled_requests: list[RequestResult] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        """Ensure id is always set."""
        if self.id is None:
            self.id = uuid4()
