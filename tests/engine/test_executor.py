"""Tests for test executor."""

import asyncio

import httpx
import pytest

from engine.executor import TestExecutor
from engine.models import RunStatus, TestSpec


class MockTransport(httpx.AsyncBaseTransport):
    """Mock HTTP transport for testing."""

    def __init__(
        self,
        status_code: int = 200,
        content: bytes = b'{"status": "ok"}',
        delay: float = 0.0,
    ):
        self.status_code = status_code
        self.content = content
        self.delay = delay
        self.request_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return httpx.Response(self.status_code, content=self.content)


class TestTestExecutor:
    """Tests for TestExecutor."""

    @pytest.mark.asyncio
    async def test_successful_run(self):
        """Test a successful test run."""
        transport = MockTransport()
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Test",
            url="https://example.com/api",
            total_requests=10,
            concurrency=2,
        )

        result = await executor.run(spec)

        assert result.status == RunStatus.COMPLETED
        assert result.metrics.total_requests == 10
        assert result.metrics.successful_requests == 10
        assert result.passed is True
        assert transport.request_count == 10

        await client.aclose()

    @pytest.mark.asyncio
    async def test_run_with_failures(self):
        """Test run with some failures."""
        transport = MockTransport(status_code=500)
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Test",
            url="https://example.com/api",
            total_requests=5,
            concurrency=1,
            expected_status_codes=[200],
        )

        result = await executor.run(spec)

        assert result.status == RunStatus.COMPLETED
        assert result.metrics.total_requests == 5
        # All requests got 500, which counts as successful HTTP (but wrong status)
        assert result.metrics.successful_requests == 5
        assert result.passed is False  # Due to unexpected status code

        await client.aclose()

    @pytest.mark.asyncio
    async def test_cancellation(self):
        """Test run cancellation."""
        transport = MockTransport(delay=0.2)  # Slow responses
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Test",
            url="https://example.com/api",
            total_requests=100,
            concurrency=2,  # Low concurrency so cancellation can catch up
        )

        # Start run in background
        run_task = asyncio.create_task(executor.run(spec))

        # Wait for first batch to start, then cancel
        await asyncio.sleep(0.1)
        # Get the run ID from active runs
        active = executor.get_active_runs()
        if active:
            executor.cancel(active[0].id)

        result = await run_task

        assert result.status == RunStatus.CANCELLED
        # With concurrency=2 and delay=0.2, after 0.1s only ~2 requests complete
        # Remaining 98 should be cancelled
        assert result.metrics.errors_by_type.get("cancelled", 0) > 0

        await client.aclose()

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """Test progress callback is called."""
        transport = MockTransport()
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Test",
            url="https://example.com/api",
            total_requests=10,
            concurrency=1,
        )

        progress_updates = []

        def on_progress(completed: int, total: int):
            progress_updates.append((completed, total))

        result = await executor.run(spec, on_progress=on_progress)

        assert result.status == RunStatus.COMPLETED
        assert len(progress_updates) == 10
        assert progress_updates[-1] == (10, 10)

        await client.aclose()

    @pytest.mark.asyncio
    async def test_get_active_runs(self):
        """Test getting active runs."""
        transport = MockTransport(delay=0.1)
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Test",
            url="https://example.com/api",
            total_requests=50,
            concurrency=5,
        )

        # Start run in background
        run_task = asyncio.create_task(executor.run(spec))

        await asyncio.sleep(0.02)

        # Should have one active run
        active = executor.get_active_runs()
        assert len(active) == 1
        assert active[0].spec.name == "Test"

        # Cancel and wait
        executor.cancel(active[0].id)
        await run_task

        # Should have no active runs after completion
        assert len(executor.get_active_runs()) == 0

        await client.aclose()
