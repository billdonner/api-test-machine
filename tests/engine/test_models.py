"""Tests for engine models."""

import pytest
from pydantic import ValidationError

from engine.models import (
    HttpMethod,
    Metrics,
    RequestResult,
    RunResult,
    RunStatus,
    TestSpec,
    Thresholds,
)


class TestTestSpec:
    """Tests for TestSpec model."""

    def test_minimal_spec(self):
        """Test creating a spec with minimal required fields."""
        spec = TestSpec(name="Test", url="https://example.com")
        assert spec.name == "Test"
        assert spec.url == "https://example.com"
        assert spec.method == HttpMethod.GET
        assert spec.total_requests == 100
        assert spec.concurrency == 10

    def test_full_spec(self):
        """Test creating a spec with all fields."""
        spec = TestSpec(
            name="Full Test",
            description="A complete test",
            url="https://api.example.com/test",
            method=HttpMethod.POST,
            headers={"Authorization": "Bearer token"},
            body={"key": "value"},
            total_requests=1000,
            concurrency=50,
            requests_per_second=100.0,
            timeout_seconds=60.0,
            thresholds=Thresholds(max_latency_p95_ms=500.0),
            expected_status_codes=[200, 201],
            variables={"api_key": "secret"},
        )
        assert spec.total_requests == 1000
        assert spec.thresholds.max_latency_p95_ms == 500.0

    def test_invalid_total_requests(self):
        """Test validation rejects invalid total_requests."""
        with pytest.raises(ValidationError):
            TestSpec(name="Test", url="https://example.com", total_requests=0)

    def test_invalid_concurrency(self):
        """Test validation rejects invalid concurrency."""
        with pytest.raises(ValidationError):
            TestSpec(name="Test", url="https://example.com", concurrency=0)


class TestThresholds:
    """Tests for Thresholds model."""

    def test_empty_thresholds(self):
        """Test creating empty thresholds."""
        thresholds = Thresholds()
        assert thresholds.max_latency_p50_ms is None
        assert thresholds.max_error_rate is None

    def test_valid_thresholds(self):
        """Test creating valid thresholds."""
        thresholds = Thresholds(
            max_latency_p95_ms=500.0,
            max_error_rate=0.01,
        )
        assert thresholds.max_latency_p95_ms == 500.0
        assert thresholds.max_error_rate == 0.01

    def test_invalid_error_rate(self):
        """Test validation rejects error rate > 1."""
        with pytest.raises(ValidationError):
            Thresholds(max_error_rate=1.5)


class TestMetrics:
    """Tests for Metrics model."""

    def test_empty_metrics(self):
        """Test creating empty metrics."""
        metrics = Metrics()
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0

    def test_metrics_with_values(self):
        """Test creating metrics with values."""
        metrics = Metrics(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            latency_p50_ms=50.0,
            latency_p95_ms=150.0,
            requests_per_second=50.0,
            error_rate=0.05,
        )
        assert metrics.error_rate == 0.05


class TestRunResult:
    """Tests for RunResult model."""

    def test_new_run_result(self):
        """Test creating a new run result."""
        spec = TestSpec(name="Test", url="https://example.com")
        result = RunResult(spec=spec)
        assert result.status == RunStatus.PENDING
        assert result.id is not None
        assert result.requests_completed == 0

    def test_completed_run_result(self):
        """Test a completed run result."""
        spec = TestSpec(name="Test", url="https://example.com")
        result = RunResult(
            spec=spec,
            status=RunStatus.COMPLETED,
            passed=True,
            metrics=Metrics(total_requests=100, successful_requests=100),
        )
        assert result.status == RunStatus.COMPLETED
        assert result.passed is True
