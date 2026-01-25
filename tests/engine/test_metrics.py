"""Tests for metrics collector."""

import pytest

from engine.metrics import MetricsCollector
from engine.models import RequestResult, Thresholds


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_empty_collector(self):
        """Test computing metrics with no results."""
        collector = MetricsCollector()
        metrics = collector.compute_metrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0

    def test_single_successful_request(self):
        """Test metrics with a single successful request."""
        collector = MetricsCollector()
        collector.add_result(RequestResult(
            request_number=1,
            status_code=200,
            latency_ms=50.0,
            response_size_bytes=100,
        ))

        metrics = collector.compute_metrics()

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.latency_p50_ms == 50.0

    def test_mixed_results(self):
        """Test metrics with mixed success and failure."""
        collector = MetricsCollector()

        # Add successful requests
        for i in range(8):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=50.0 + i * 10,
            ))

        # Add failed requests
        collector.add_result(RequestResult(
            request_number=9,
            latency_ms=100.0,
            error="timeout",
        ))
        collector.add_result(RequestResult(
            request_number=10,
            latency_ms=100.0,
            error="connection_error",
        ))

        metrics = collector.compute_metrics()

        assert metrics.total_requests == 10
        assert metrics.successful_requests == 8
        assert metrics.failed_requests == 2
        assert metrics.error_rate == 0.2

    def test_latency_percentiles(self):
        """Test latency percentile calculations."""
        collector = MetricsCollector()

        # Add 100 requests with increasing latency
        for i in range(100):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=float(i + 1),  # 1ms to 100ms
            ))

        metrics = collector.compute_metrics()

        assert metrics.latency_min_ms == 1.0
        assert metrics.latency_max_ms == 100.0
        assert metrics.latency_p50_ms == pytest.approx(50.0, abs=1.0)
        assert metrics.latency_p95_ms == pytest.approx(95.0, abs=1.0)
        assert metrics.latency_p99_ms == pytest.approx(99.0, abs=1.0)

    def test_status_code_counts(self):
        """Test status code counting."""
        collector = MetricsCollector()

        for _ in range(5):
            collector.add_result(RequestResult(
                request_number=1,
                status_code=200,
                latency_ms=10.0,
            ))
        for _ in range(3):
            collector.add_result(RequestResult(
                request_number=1,
                status_code=404,
                latency_ms=10.0,
            ))

        metrics = collector.compute_metrics()

        assert metrics.status_code_counts[200] == 5
        assert metrics.status_code_counts[404] == 3

    def test_check_thresholds_pass(self):
        """Test threshold checking when passing."""
        collector = MetricsCollector()

        for i in range(10):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=50.0,
            ))

        thresholds = Thresholds(
            max_latency_p95_ms=100.0,
            max_error_rate=0.1,
        )

        passed, failures = collector.check_thresholds(thresholds, [200])

        assert passed is True
        assert len(failures) == 0

    def test_check_thresholds_fail_latency(self):
        """Test threshold checking fails on latency."""
        collector = MetricsCollector()

        for i in range(10):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=200.0,
            ))

        thresholds = Thresholds(max_latency_p95_ms=100.0)

        passed, failures = collector.check_thresholds(thresholds, [200])

        assert passed is False
        assert any("P95 latency" in f for f in failures)

    def test_check_thresholds_fail_error_rate(self):
        """Test threshold checking fails on error rate."""
        collector = MetricsCollector()

        for i in range(5):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=10.0,
            ))
        for i in range(5):
            collector.add_result(RequestResult(
                request_number=i + 6,
                latency_ms=10.0,
                error="error",
            ))

        thresholds = Thresholds(max_error_rate=0.1)

        passed, failures = collector.check_thresholds(thresholds, [200])

        assert passed is False
        assert any("Error rate" in f for f in failures)

    def test_check_thresholds_unexpected_status(self):
        """Test threshold checking detects unexpected status codes."""
        collector = MetricsCollector()

        collector.add_result(RequestResult(
            request_number=1,
            status_code=500,
            latency_ms=10.0,
        ))

        thresholds = Thresholds()

        passed, failures = collector.check_thresholds(thresholds, [200])

        assert passed is False
        assert any("unexpected status code 500" in f for f in failures)
