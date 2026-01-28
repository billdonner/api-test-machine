"""Metrics collection and aggregation for test runs."""

import statistics
from datetime import UTC, datetime
from typing import Sequence

from engine.models import EndpointMetrics, Metrics, RequestResult, Thresholds


class MetricsCollector:
    """Collects and aggregates metrics from test requests.

    This class accumulates individual request results and computes
    aggregate statistics including latency percentiles, throughput,
    and error rates.
    """

    def __init__(self):
        """Initialize an empty metrics collector."""
        self._results: list[RequestResult] = []
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None

    def start(self) -> None:
        """Mark the start of metrics collection."""
        self._start_time = datetime.now(UTC)

    def stop(self) -> None:
        """Mark the end of metrics collection."""
        self._end_time = datetime.now(UTC)

    def add_result(self, result: RequestResult) -> None:
        """Add a request result to the collection.

        Args:
            result: The result of a single request
        """
        self._results.append(result)

    def add_results(self, results: Sequence[RequestResult]) -> None:
        """Add multiple request results.

        Args:
            results: Sequence of request results
        """
        self._results.extend(results)

    @property
    def count(self) -> int:
        """Return the number of collected results."""
        return len(self._results)

    def compute_metrics(self) -> Metrics:
        """Compute aggregate metrics from collected results.

        Returns:
            Metrics object with computed statistics
        """
        if not self._results:
            return Metrics()

        # Separate successful and failed requests
        successful = [r for r in self._results if r.error is None and r.status_code is not None]
        failed = [r for r in self._results if r.error is not None or r.status_code is None]

        # Collect latencies (all requests, even failed ones with latency)
        latencies = [r.latency_ms for r in self._results if r.latency_ms > 0]

        # Status code counts
        status_counts: dict[int, int] = {}
        for r in self._results:
            if r.status_code is not None:
                status_counts[r.status_code] = status_counts.get(r.status_code, 0) + 1

        # Error breakdown
        errors_by_type: dict[str, int] = {}
        for r in failed:
            error_type = r.error or "unknown"
            # Simplify error messages to types
            if "timeout" in error_type.lower():
                error_type = "timeout"
            elif "connection" in error_type.lower():
                error_type = "connection_error"
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1

        # Total bytes
        total_bytes = sum(r.response_size_bytes or 0 for r in successful)

        # Duration
        duration = None
        if self._start_time and self._end_time:
            duration = (self._end_time - self._start_time).total_seconds()

        # Throughput
        rps = None
        if duration and duration > 0:
            rps = len(self._results) / duration

        # Build metrics
        metrics = Metrics(
            total_requests=len(self._results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            status_code_counts=status_counts,
            errors_by_type=errors_by_type,
            total_bytes_received=total_bytes,
            duration_seconds=duration,
            requests_per_second=rps,
        )

        # Latency stats (only if we have latencies)
        if latencies:
            sorted_latencies = sorted(latencies)
            metrics.latency_min_ms = sorted_latencies[0]
            metrics.latency_max_ms = sorted_latencies[-1]
            metrics.latency_mean_ms = statistics.mean(latencies)
            metrics.latency_p50_ms = self._percentile(sorted_latencies, 50)
            metrics.latency_p90_ms = self._percentile(sorted_latencies, 90)
            metrics.latency_p95_ms = self._percentile(sorted_latencies, 95)
            metrics.latency_p99_ms = self._percentile(sorted_latencies, 99)

        # Error rate
        if metrics.total_requests > 0:
            metrics.error_rate = metrics.failed_requests / metrics.total_requests

        return metrics

    @staticmethod
    def _percentile(sorted_data: list[float], p: float) -> float:
        """Compute percentile from sorted data.

        Args:
            sorted_data: Sorted list of values
            p: Percentile (0-100)

        Returns:
            The percentile value
        """
        if not sorted_data:
            return 0.0

        n = len(sorted_data)
        if n == 1:
            return sorted_data[0]

        k = (n - 1) * (p / 100.0)
        f = int(k)
        c = f + 1 if f + 1 < n else f

        if f == c:
            return sorted_data[f]

        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)

    def check_thresholds(
        self,
        thresholds: Thresholds,
        expected_status_codes: list[int],
    ) -> tuple[bool, list[str]]:
        """Check if metrics pass the given thresholds.

        Args:
            thresholds: Threshold values to check against
            expected_status_codes: Status codes considered successful

        Returns:
            Tuple of (passed, failure_reasons)
        """
        metrics = self.compute_metrics()
        failures: list[str] = []

        # Any failed request causes the run to fail
        if metrics.failed_requests > 0:
            failures.append(
                f"{metrics.failed_requests} request(s) failed"
            )

        # Check latency thresholds
        if thresholds.max_latency_p50_ms is not None:
            if metrics.latency_p50_ms and metrics.latency_p50_ms > thresholds.max_latency_p50_ms:
                failures.append(
                    f"P50 latency {metrics.latency_p50_ms:.1f}ms exceeds threshold {thresholds.max_latency_p50_ms}ms"
                )

        if thresholds.max_latency_p95_ms is not None:
            if metrics.latency_p95_ms and metrics.latency_p95_ms > thresholds.max_latency_p95_ms:
                failures.append(
                    f"P95 latency {metrics.latency_p95_ms:.1f}ms exceeds threshold {thresholds.max_latency_p95_ms}ms"
                )

        if thresholds.max_latency_p99_ms is not None:
            if metrics.latency_p99_ms and metrics.latency_p99_ms > thresholds.max_latency_p99_ms:
                failures.append(
                    f"P99 latency {metrics.latency_p99_ms:.1f}ms exceeds threshold {thresholds.max_latency_p99_ms}ms"
                )

        # Check error rate
        if thresholds.max_error_rate is not None:
            if metrics.error_rate and metrics.error_rate > thresholds.max_error_rate:
                failures.append(
                    f"Error rate {metrics.error_rate:.1%} exceeds threshold {thresholds.max_error_rate:.1%}"
                )

        # Check throughput
        if thresholds.min_throughput_rps is not None:
            if metrics.requests_per_second is None or metrics.requests_per_second < thresholds.min_throughput_rps:
                actual = metrics.requests_per_second or 0
                failures.append(
                    f"Throughput {actual:.1f} rps below threshold {thresholds.min_throughput_rps} rps"
                )

        # Check for unexpected status codes
        for status, count in metrics.status_code_counts.items():
            if status not in expected_status_codes:
                failures.append(
                    f"Received {count} responses with unexpected status code {status}"
                )

        return len(failures) == 0, failures


class EndpointMetricsCollector:
    """Collects metrics for multi-endpoint tests.

    Maintains separate MetricsCollector instances for each endpoint
    plus an aggregate collector for overall metrics.
    """

    def __init__(self, endpoint_names: list[str]):
        """Initialize collectors for each endpoint.

        Args:
            endpoint_names: List of endpoint names to track
        """
        self._endpoint_collectors: dict[str, MetricsCollector] = {
            name: MetricsCollector() for name in endpoint_names
        }
        self._aggregate_collector = MetricsCollector()

    def start(self) -> None:
        """Mark the start of metrics collection for all collectors."""
        for collector in self._endpoint_collectors.values():
            collector.start()
        self._aggregate_collector.start()

    def stop(self) -> None:
        """Mark the end of metrics collection for all collectors."""
        for collector in self._endpoint_collectors.values():
            collector.stop()
        self._aggregate_collector.stop()

    def add_result(self, result: RequestResult) -> None:
        """Add a request result to the appropriate collectors.

        Args:
            result: The result of a single request (must have endpoint_name set)
        """
        # Add to aggregate
        self._aggregate_collector.add_result(result)

        # Add to endpoint-specific collector
        if result.endpoint_name and result.endpoint_name in self._endpoint_collectors:
            self._endpoint_collectors[result.endpoint_name].add_result(result)

    @property
    def count(self) -> int:
        """Return the total number of collected results."""
        return self._aggregate_collector.count

    def compute_aggregate_metrics(self) -> Metrics:
        """Compute aggregate metrics across all endpoints.

        Returns:
            Metrics object with computed statistics
        """
        return self._aggregate_collector.compute_metrics()

    def compute_endpoint_metrics(self) -> list[EndpointMetrics]:
        """Compute metrics for each endpoint.

        Returns:
            List of EndpointMetrics objects
        """
        return [
            EndpointMetrics(
                endpoint_name=name,
                metrics=collector.compute_metrics()
            )
            for name, collector in self._endpoint_collectors.items()
        ]

    def check_thresholds(
        self,
        thresholds: Thresholds,
        expected_status_codes: list[int],
    ) -> tuple[bool, list[str]]:
        """Check if aggregate metrics pass the given thresholds.

        Args:
            thresholds: Threshold values to check against
            expected_status_codes: Status codes considered successful

        Returns:
            Tuple of (passed, failure_reasons)
        """
        return self._aggregate_collector.check_thresholds(
            thresholds, expected_status_codes
        )
