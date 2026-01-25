"""Async test executor with cancellation support."""

import asyncio
import itertools
import json
import random
import time
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

import httpx

from engine.auth import AuthProvider
from engine.metrics import EndpointMetricsCollector, MetricsCollector
from engine.models import (
    DistributionStrategy,
    EndpointSpec,
    HttpMethod,
    Metrics,
    RequestResult,
    RunResult,
    RunStatus,
    TestSpec,
)
from engine.rate_limiter import NoopRateLimiter, TokenBucketRateLimiter
from engine.templating import TemplateEngine


class EndpointSelector:
    """Selects endpoints based on distribution strategy.

    Supports three strategies:
    - round_robin: Cycle through endpoints A, B, C, A, B, C...
    - weighted: Distribute based on weights (e.g., 3:1 = ~75%:25%)
    - sequential: All requests to A, then all to B, then C
    """

    def __init__(
        self,
        endpoints: list[EndpointSpec],
        strategy: DistributionStrategy,
        total_requests: int,
    ):
        """Initialize the endpoint selector.

        Args:
            endpoints: List of endpoints to distribute across
            strategy: Distribution strategy to use
            total_requests: Total number of requests (for sequential strategy)
        """
        self._endpoints = endpoints
        self._strategy = strategy
        self._total_requests = total_requests

        # For round robin
        self._rr_iterator = itertools.cycle(endpoints)

        # For weighted - build a weighted list
        self._weighted_list: list[EndpointSpec] = []
        for ep in endpoints:
            self._weighted_list.extend([ep] * ep.weight)

        # For sequential - precompute request ranges
        self._sequential_ranges: list[tuple[int, int, EndpointSpec]] = []
        if strategy == DistributionStrategy.SEQUENTIAL and len(endpoints) > 0:
            requests_per_endpoint = total_requests // len(endpoints)
            remainder = total_requests % len(endpoints)
            current = 0
            for i, ep in enumerate(endpoints):
                # Distribute remainder to first endpoints
                extra = 1 if i < remainder else 0
                count = requests_per_endpoint + extra
                self._sequential_ranges.append((current, current + count, ep))
                current += count

    def select(self, request_num: int) -> EndpointSpec:
        """Select an endpoint for the given request number.

        Args:
            request_num: 1-indexed request number

        Returns:
            The selected EndpointSpec
        """
        if len(self._endpoints) == 1:
            return self._endpoints[0]

        if self._strategy == DistributionStrategy.ROUND_ROBIN:
            return next(self._rr_iterator)

        elif self._strategy == DistributionStrategy.WEIGHTED:
            return random.choice(self._weighted_list)

        elif self._strategy == DistributionStrategy.SEQUENTIAL:
            # Find the endpoint for this request number
            for start, end, ep in self._sequential_ranges:
                if start < request_num <= end:
                    return ep
            # Fallback to last endpoint
            return self._endpoints[-1]

        return self._endpoints[0]


class TestExecutor:
    """Async HTTP load test executor.

    Executes load tests according to a TestSpec, supporting:
    - Concurrent request execution
    - Rate limiting
    - Template variable substitution
    - Cancellation via async Event
    - Progress callbacks

    Example:
        executor = TestExecutor()
        result = await executor.run(spec)
        print(f"Completed: {result.metrics.total_requests} requests")
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
    ):
        """Initialize the executor.

        Args:
            http_client: Optional httpx client (for testing/mocking)
        """
        self._external_client = http_client
        self._cancel_events: dict[UUID, asyncio.Event] = {}
        self._active_runs: dict[UUID, RunResult] = {}

    async def run(
        self,
        spec: TestSpec,
        run_id: UUID | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> RunResult:
        """Execute a load test according to the spec.

        Args:
            spec: Test specification
            run_id: Optional run ID (generated if not provided)
            on_progress: Optional callback(completed, total) for progress updates

        Returns:
            RunResult with metrics and pass/fail status
        """
        # Initialize run result
        result = RunResult(spec=spec, status=RunStatus.PENDING)
        if run_id:
            result.id = run_id

        # Set up cancellation
        cancel_event = asyncio.Event()
        self._cancel_events[result.id] = cancel_event
        self._active_runs[result.id] = result

        try:
            result.status = RunStatus.RUNNING
            result.started_at = datetime.utcnow()

            # Set up rate limiter
            if spec.requests_per_second:
                rate_limiter = TokenBucketRateLimiter(rate=spec.requests_per_second)
            else:
                rate_limiter = NoopRateLimiter()

            # Set up template engine
            template_engine = TemplateEngine(variables=spec.variables)

            # Set up auth headers (global auth applies to all endpoints)
            auth_headers: dict[str, str] = {}
            if spec.auth:
                auth_provider = AuthProvider(template_engine=template_engine)
                auth_headers = await auth_provider.get_headers(spec.auth)

            # Get endpoints and set up endpoint selector
            endpoints = spec.get_endpoints()
            endpoint_selector = EndpointSelector(
                endpoints=endpoints,
                strategy=spec.distribution_strategy,
                total_requests=spec.total_requests,
            )
            is_multi_endpoint = spec.is_multi_endpoint()

            # Set up metrics collector (use endpoint-aware collector for multi-endpoint)
            if is_multi_endpoint:
                endpoint_names = [ep.name for ep in endpoints]
                metrics_collector = EndpointMetricsCollector(endpoint_names)
            else:
                metrics_collector = MetricsCollector()
            metrics_collector.start()

            # Create or use provided HTTP client
            if self._external_client:
                client = self._external_client
                should_close = False
            else:
                client = httpx.AsyncClient(timeout=spec.timeout_seconds)
                should_close = True

            try:
                # Execute requests with concurrency control
                semaphore = asyncio.Semaphore(spec.concurrency)
                completed = 0
                completed_lock = asyncio.Lock()

                # Sampling config: capture first N requests and all failures
                max_sampled = 20
                sampled_results: list[RequestResult] = []
                sampled_lock = asyncio.Lock()

                # Capture run_result.id before defining inner function to avoid shadowing issues
                run_result_id = result.id

                async def execute_request(request_num: int) -> RequestResult:
                    nonlocal completed

                    # Select endpoint for this request
                    endpoint = endpoint_selector.select(request_num)
                    endpoint_name = endpoint.name if is_multi_endpoint else None

                    # Check for cancellation
                    if cancel_event.is_set():
                        cancelled_result = RequestResult(
                            request_number=request_num,
                            latency_ms=0,
                            error="cancelled",
                            endpoint_name=endpoint_name,
                        )
                        metrics_collector.add_result(cancelled_result)
                        return cancelled_result

                    async with semaphore:
                        # Rate limit
                        await rate_limiter.acquire()

                        # Check for cancellation again after waiting
                        if cancel_event.is_set():
                            cancelled_result = RequestResult(
                                request_number=request_num,
                                latency_ms=0,
                                error="cancelled",
                                endpoint_name=endpoint_name,
                            )
                            metrics_collector.add_result(cancelled_result)
                            return cancelled_result

                        # Build request from endpoint config
                        url = template_engine.substitute(endpoint.url, request_num)
                        headers = {**auth_headers}
                        # Merge endpoint-specific headers
                        headers.update(
                            template_engine.substitute_dict(endpoint.headers, request_num)
                        )

                        body = None
                        if endpoint.body:
                            if isinstance(endpoint.body, dict):
                                body = json.dumps(
                                    template_engine.substitute_dict(endpoint.body, request_num)
                                )
                                if "Content-Type" not in headers:
                                    headers["Content-Type"] = "application/json"
                            else:
                                body = template_engine.substitute(endpoint.body, request_num)

                        # Execute request
                        start_time = time.perf_counter()
                        try:
                            response = await client.request(
                                method=endpoint.method.value,
                                url=url,
                                headers=headers,
                                content=body,
                            )
                            elapsed_ms = (time.perf_counter() - start_time) * 1000

                            # Determine if we should capture full details
                            should_sample = False
                            async with sampled_lock:
                                if len(sampled_results) < max_sampled:
                                    should_sample = True

                            # Truncate response body for storage (max 10KB)
                            resp_body = None
                            resp_headers = None
                            if should_sample:
                                try:
                                    resp_body = response.text[:10240] if response.text else None
                                except Exception:
                                    resp_body = f"<binary: {len(response.content)} bytes>"
                                resp_headers = dict(response.headers)

                            req_result = RequestResult(
                                request_number=request_num,
                                status_code=response.status_code,
                                latency_ms=elapsed_ms,
                                response_size_bytes=len(response.content),
                                endpoint_name=endpoint_name,
                                request_url=url if should_sample else None,
                                request_method=endpoint.method.value if should_sample else None,
                                request_headers=headers if should_sample else None,
                                request_body=body if should_sample else None,
                                response_headers=resp_headers,
                                response_body=resp_body,
                            )

                            # Add to sampled results if applicable
                            if should_sample:
                                async with sampled_lock:
                                    if len(sampled_results) < max_sampled:
                                        sampled_results.append(req_result)

                            request_result = req_result
                        except httpx.TimeoutException:
                            elapsed_ms = (time.perf_counter() - start_time) * 1000
                            req_result = RequestResult(
                                request_number=request_num,
                                latency_ms=elapsed_ms,
                                error="timeout",
                                endpoint_name=endpoint_name,
                                request_url=url,
                                request_method=endpoint.method.value,
                                request_headers=headers,
                                request_body=body,
                            )
                            # Always capture failures
                            async with sampled_lock:
                                sampled_results.append(req_result)
                            request_result = req_result
                        except httpx.ConnectError as e:
                            elapsed_ms = (time.perf_counter() - start_time) * 1000
                            req_result = RequestResult(
                                request_number=request_num,
                                latency_ms=elapsed_ms,
                                error=f"connection_error: {e}",
                                endpoint_name=endpoint_name,
                                request_url=url,
                                request_method=endpoint.method.value,
                                request_headers=headers,
                                request_body=body,
                            )
                            async with sampled_lock:
                                sampled_results.append(req_result)
                            request_result = req_result
                        except Exception as e:
                            elapsed_ms = (time.perf_counter() - start_time) * 1000
                            req_result = RequestResult(
                                request_number=request_num,
                                latency_ms=elapsed_ms,
                                error=str(e),
                                endpoint_name=endpoint_name,
                                request_url=url,
                                request_method=endpoint.method.value,
                                request_headers=headers,
                                request_body=body,
                            )
                            async with sampled_lock:
                                sampled_results.append(req_result)
                            request_result = req_result

                        # Add result to metrics collector immediately
                        metrics_collector.add_result(request_result)

                        # Update progress and live stats
                        async with completed_lock:
                            completed += 1
                            # Update the active run with live data
                            active_run = self._active_runs.get(run_id or run_result_id)
                            if active_run:
                                active_run.requests_completed = completed
                                # Update sampled requests
                                async with sampled_lock:
                                    active_run.sampled_requests = sorted(
                                        sampled_results, key=lambda r: r.request_number
                                    )
                                # Compute live metrics every 5 requests or on last request
                                if completed % 5 == 0 or completed == spec.total_requests:
                                    active_run.metrics = metrics_collector.compute_metrics()

                            if on_progress:
                                on_progress(completed, spec.total_requests)

                        return request_result

                # Create all tasks
                tasks = [
                    asyncio.create_task(execute_request(i + 1))
                    for i in range(spec.total_requests)
                ]

                # Wait for all tasks
                await asyncio.gather(*tasks, return_exceptions=True)

            finally:
                if should_close:
                    await client.aclose()

            # Finalize metrics
            metrics_collector.stop()
            result.requests_completed = metrics_collector.count

            # Handle metrics based on collector type
            if is_multi_endpoint:
                result.metrics = metrics_collector.compute_aggregate_metrics()
                result.endpoint_metrics = metrics_collector.compute_endpoint_metrics()
            else:
                result.metrics = metrics_collector.compute_metrics()

            # Store sampled requests (sorted by request number)
            result.sampled_requests = sorted(sampled_results, key=lambda r: r.request_number)

            # Check thresholds
            passed, failures = metrics_collector.check_thresholds(
                spec.thresholds,
                spec.expected_status_codes,
            )
            result.passed = passed
            result.failure_reasons = failures

            # Set final status
            if cancel_event.is_set():
                result.status = RunStatus.CANCELLED
            else:
                result.status = RunStatus.COMPLETED

        except Exception as e:
            result.status = RunStatus.FAILED
            result.error_message = str(e)
            result.passed = False
        finally:
            result.completed_at = datetime.utcnow()
            # Clean up
            self._cancel_events.pop(result.id, None)
            self._active_runs.pop(result.id, None)

        return result

    def cancel(self, run_id: UUID) -> bool:
        """Cancel a running test.

        Args:
            run_id: ID of the run to cancel

        Returns:
            True if cancellation was signaled, False if run not found
        """
        event = self._cancel_events.get(run_id)
        if event:
            event.set()
            return True
        return False

    def get_active_run(self, run_id: UUID) -> RunResult | None:
        """Get an active run by ID.

        Args:
            run_id: Run ID to look up

        Returns:
            RunResult if active, None otherwise
        """
        return self._active_runs.get(run_id)

    def get_active_runs(self) -> list[RunResult]:
        """Get all active runs.

        Returns:
            List of active RunResults
        """
        return list(self._active_runs.values())
