"""Tests for multi-endpoint functionality."""

import pytest

from engine.executor import EndpointSelector
from engine.metrics import EndpointMetricsCollector
from engine.models import (
    DistributionStrategy,
    EndpointMetrics,
    EndpointSpec,
    HttpMethod,
    RequestResult,
    TestSpec,
    Thresholds,
)


class TestEndpointSpec:
    """Tests for EndpointSpec model."""

    def test_default_values(self):
        """Test EndpointSpec default values."""
        spec = EndpointSpec(name="test", url="https://example.com")

        assert spec.method == HttpMethod.GET
        assert spec.headers == {}
        assert spec.body is None
        assert spec.weight == 1
        assert spec.expected_status_codes == [200, 201, 204]

    def test_custom_values(self):
        """Test EndpointSpec with custom values."""
        spec = EndpointSpec(
            name="create_user",
            url="https://api.example.com/users",
            method=HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body={"name": "test"},
            weight=3,
            expected_status_codes=[201],
        )

        assert spec.name == "create_user"
        assert spec.method == HttpMethod.POST
        assert spec.weight == 3


class TestTestSpecMultiEndpoint:
    """Tests for TestSpec multi-endpoint support."""

    def test_single_endpoint_legacy(self):
        """Test legacy single-endpoint spec."""
        spec = TestSpec(
            name="Single Test",
            url="https://example.com/api",
            method=HttpMethod.GET,
        )

        assert spec.is_multi_endpoint() is False
        endpoints = spec.get_endpoints()
        assert len(endpoints) == 1
        assert endpoints[0].name == "default"
        assert endpoints[0].url == "https://example.com/api"

    def test_multi_endpoint(self):
        """Test multi-endpoint spec."""
        spec = TestSpec(
            name="Multi Test",
            url="",  # Can be empty in multi-endpoint mode
            endpoints=[
                EndpointSpec(name="A", url="https://example.com/a"),
                EndpointSpec(name="B", url="https://example.com/b"),
                EndpointSpec(name="C", url="https://example.com/c"),
            ],
            distribution_strategy=DistributionStrategy.ROUND_ROBIN,
        )

        assert spec.is_multi_endpoint() is True
        endpoints = spec.get_endpoints()
        assert len(endpoints) == 3
        assert endpoints[0].name == "A"

    def test_get_endpoints_preserves_config(self):
        """Test that get_endpoints preserves endpoint configuration."""
        spec = TestSpec(
            name="Test",
            url="https://example.com",
            method=HttpMethod.POST,
            headers={"X-Custom": "value"},
            body={"key": "value"},
            expected_status_codes=[200, 201],
        )

        endpoints = spec.get_endpoints()
        assert len(endpoints) == 1
        ep = endpoints[0]

        assert ep.url == "https://example.com"
        assert ep.method == HttpMethod.POST
        assert ep.headers == {"X-Custom": "value"}
        assert ep.body == {"key": "value"}
        assert ep.expected_status_codes == [200, 201]


class TestEndpointSelector:
    """Tests for EndpointSelector distribution strategies."""

    def create_endpoints(self, count: int = 3) -> list[EndpointSpec]:
        """Create test endpoints."""
        return [
            EndpointSpec(name=f"EP{i}", url=f"https://example.com/{i}", weight=1)
            for i in range(count)
        ]

    def test_round_robin_distribution(self):
        """Test round-robin distribution cycles through endpoints."""
        endpoints = self.create_endpoints(3)
        selector = EndpointSelector(
            endpoints=endpoints,
            strategy=DistributionStrategy.ROUND_ROBIN,
            total_requests=9,
        )

        selections = [selector.select(i + 1).name for i in range(9)]

        # Should cycle: EP0, EP1, EP2, EP0, EP1, EP2, EP0, EP1, EP2
        assert selections == ["EP0", "EP1", "EP2", "EP0", "EP1", "EP2", "EP0", "EP1", "EP2"]

    def test_sequential_distribution(self):
        """Test sequential distribution completes each endpoint before moving on."""
        endpoints = self.create_endpoints(3)
        selector = EndpointSelector(
            endpoints=endpoints,
            strategy=DistributionStrategy.SEQUENTIAL,
            total_requests=9,
        )

        selections = [selector.select(i + 1).name for i in range(9)]

        # Should be: EP0, EP0, EP0, EP1, EP1, EP1, EP2, EP2, EP2
        assert selections[:3] == ["EP0", "EP0", "EP0"]
        assert selections[3:6] == ["EP1", "EP1", "EP1"]
        assert selections[6:9] == ["EP2", "EP2", "EP2"]

    def test_sequential_uneven_distribution(self):
        """Test sequential distribution with uneven request count."""
        endpoints = self.create_endpoints(3)
        selector = EndpointSelector(
            endpoints=endpoints,
            strategy=DistributionStrategy.SEQUENTIAL,
            total_requests=10,  # 10 requests for 3 endpoints
        )

        selections = [selector.select(i + 1).name for i in range(10)]

        # Should distribute 4, 3, 3 requests
        ep0_count = sum(1 for s in selections if s == "EP0")
        ep1_count = sum(1 for s in selections if s == "EP1")
        ep2_count = sum(1 for s in selections if s == "EP2")

        assert ep0_count == 4  # First endpoint gets the extra
        assert ep1_count == 3
        assert ep2_count == 3

    def test_weighted_distribution(self):
        """Test weighted distribution respects weights."""
        endpoints = [
            EndpointSpec(name="Heavy", url="https://example.com/heavy", weight=3),
            EndpointSpec(name="Light", url="https://example.com/light", weight=1),
        ]
        selector = EndpointSelector(
            endpoints=endpoints,
            strategy=DistributionStrategy.WEIGHTED,
            total_requests=1000,
        )

        # Run many selections
        selections = [selector.select(i + 1).name for i in range(1000)]
        heavy_count = sum(1 for s in selections if s == "Heavy")

        # Weight 3:1 should give roughly 75% to Heavy
        # Allow some variance since it's random
        ratio = heavy_count / 1000
        assert 0.65 <= ratio <= 0.85, f"Expected ~75% Heavy, got {ratio * 100:.1f}%"

    def test_single_endpoint(self):
        """Test selector with single endpoint."""
        endpoints = [EndpointSpec(name="Only", url="https://example.com")]
        selector = EndpointSelector(
            endpoints=endpoints,
            strategy=DistributionStrategy.ROUND_ROBIN,
            total_requests=10,
        )

        selections = [selector.select(i + 1).name for i in range(10)]
        assert all(s == "Only" for s in selections)


class TestEndpointMetricsCollector:
    """Tests for EndpointMetricsCollector."""

    def test_empty_collector(self):
        """Test computing metrics with no results."""
        collector = EndpointMetricsCollector(["A", "B"])
        collector.start()
        collector.stop()

        aggregate = collector.compute_aggregate_metrics()
        per_endpoint = collector.compute_endpoint_metrics()

        assert aggregate.total_requests == 0
        assert len(per_endpoint) == 2

    def test_routes_to_correct_endpoint(self):
        """Test results are routed to correct endpoint collectors."""
        collector = EndpointMetricsCollector(["A", "B"])
        collector.start()

        # Add results to endpoint A
        for i in range(5):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=50.0,
                endpoint_name="A",
            ))

        # Add results to endpoint B
        for i in range(3):
            collector.add_result(RequestResult(
                request_number=i + 6,
                status_code=200,
                latency_ms=100.0,
                endpoint_name="B",
            ))

        collector.stop()

        per_endpoint = collector.compute_endpoint_metrics()
        ep_a = next(ep for ep in per_endpoint if ep.endpoint_name == "A")
        ep_b = next(ep for ep in per_endpoint if ep.endpoint_name == "B")

        assert ep_a.metrics.total_requests == 5
        assert ep_b.metrics.total_requests == 3
        assert ep_a.metrics.latency_p50_ms == 50.0
        assert ep_b.metrics.latency_p50_ms == 100.0

    def test_aggregate_metrics(self):
        """Test aggregate metrics include all endpoints."""
        collector = EndpointMetricsCollector(["A", "B"])
        collector.start()

        for i in range(5):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=50.0,
                endpoint_name="A",
            ))

        for i in range(5):
            collector.add_result(RequestResult(
                request_number=i + 6,
                status_code=200,
                latency_ms=100.0,
                endpoint_name="B",
            ))

        collector.stop()

        aggregate = collector.compute_aggregate_metrics()

        assert aggregate.total_requests == 10
        assert aggregate.successful_requests == 10

    def test_check_thresholds_aggregate(self):
        """Test threshold checking uses aggregate metrics."""
        collector = EndpointMetricsCollector(["A", "B"])
        collector.start()

        # Add successful results
        for i in range(10):
            collector.add_result(RequestResult(
                request_number=i + 1,
                status_code=200,
                latency_ms=50.0,
                endpoint_name="A" if i < 5 else "B",
            ))

        collector.stop()

        thresholds = Thresholds(max_latency_p95_ms=100.0)
        passed, failures = collector.check_thresholds(thresholds, [200])

        assert passed is True
        assert len(failures) == 0

    def test_missing_endpoint_name_handled(self):
        """Test results without endpoint_name go to aggregate only."""
        collector = EndpointMetricsCollector(["A", "B"])
        collector.start()

        collector.add_result(RequestResult(
            request_number=1,
            status_code=200,
            latency_ms=50.0,
            endpoint_name=None,  # No endpoint name
        ))

        collector.stop()

        aggregate = collector.compute_aggregate_metrics()
        per_endpoint = collector.compute_endpoint_metrics()

        # Aggregate should have the result
        assert aggregate.total_requests == 1

        # Per-endpoint should have zero
        assert all(ep.metrics.total_requests == 0 for ep in per_endpoint)


class TestRequestResultEndpointName:
    """Tests for RequestResult endpoint_name field."""

    def test_endpoint_name_default(self):
        """Test endpoint_name defaults to None."""
        result = RequestResult(
            request_number=1,
            latency_ms=50.0,
        )
        assert result.endpoint_name is None

    def test_endpoint_name_set(self):
        """Test endpoint_name can be set."""
        result = RequestResult(
            request_number=1,
            latency_ms=50.0,
            endpoint_name="TestEndpoint",
        )
        assert result.endpoint_name == "TestEndpoint"
