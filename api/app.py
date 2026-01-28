"""FastAPI application factory."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.orchestrator import TestOrchestrator
from api.routes import (
    health_router,
    init_dependencies,
    init_orchestrator,
    runs_router,
    schedules_router,
    storage_router,
    tests_router,
)
from api.storage_base import create_storage
from engine.executor import TestExecutor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Initializes and cleans up shared resources.
    """
    # Initialize dependencies
    executor = TestExecutor()
    storage = create_storage()

    # Initialize storage (creates tables if needed)
    await storage.init()

    init_dependencies(executor, storage)

    # Initialize scheduler/orchestrator
    api_key = os.environ.get("ATM_API_KEY")
    orchestrator = TestOrchestrator(
        api_url="http://localhost:8000",
        api_key=api_key,
    )
    await orchestrator.start()
    init_orchestrator(orchestrator)

    yield

    # Cleanup scheduler
    await orchestrator.stop()

    # Cleanup (cancel any active runs)
    for run in executor.get_active_runs():
        executor.cancel(run.id)

    # Close storage connections
    await storage.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="API Test Machine",
        description="REST API load testing system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(storage_router, prefix="/api/v1")
    app.include_router(tests_router, prefix="/api/v1")
    app.include_router(schedules_router, prefix="/api/v1")

    return app


# For direct uvicorn invocation
app = create_app()
