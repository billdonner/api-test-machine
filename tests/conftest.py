"""Pytest configuration and fixtures."""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator

import httpx
import pytest
from fastapi import FastAPI

# Ensure we're not using any existing API key in tests
os.environ.pop("API_TEST_MACHINE_API_KEY", None)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["ATM_DATA_DIR"] = tmpdir
        yield Path(tmpdir)
        os.environ.pop("ATM_DATA_DIR", None)


@pytest.fixture
async def async_client(temp_data_dir: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client for testing with proper lifespan handling."""
    from api.app import create_app
    from api.routes import init_dependencies
    from api.storage_base import AsyncJSONStorage
    from engine.executor import TestExecutor

    # Create app
    app = create_app()

    # Manually initialize dependencies (simulating lifespan)
    # Use JSON storage for tests (simpler, no database setup)
    executor = TestExecutor()
    storage = AsyncJSONStorage(data_dir=temp_data_dir)
    await storage.init()
    init_dependencies(executor, storage)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    # Cleanup
    for run in executor.get_active_runs():
        executor.cancel(run.id)
    await storage.close()


@pytest.fixture
def sample_test_spec() -> dict:
    """Sample test specification for tests."""
    return {
        "name": "Test API",
        "url": "https://httpbin.org/get",
        "method": "GET",
        "total_requests": 10,
        "concurrency": 2,
        "timeout_seconds": 10,
        "headers": {},
        "thresholds": {},
        "expected_status_codes": [200],
        "variables": {},
    }


@pytest.fixture
def mock_http_transport():
    """Create a mock HTTP transport for testing."""
    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self, responses: list[tuple[int, bytes]] | None = None):
            self.responses = responses or [(200, b'{"status": "ok"}')]
            self.request_count = 0

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if self.request_count < len(self.responses):
                status, content = self.responses[self.request_count]
            else:
                status, content = self.responses[-1]
            self.request_count += 1
            return httpx.Response(status, content=content)

    return MockTransport
