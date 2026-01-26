"""SQLAlchemy database models and connection management."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from engine.models import (
    EndpointMetrics,
    Metrics,
    RequestResult,
    RunResult,
    RunStatus,
    TestSpec,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class TestConfig(Base):
    """Database model for saved test configurations."""

    __tablename__ = "test_configs"

    # Primary key is the test name
    name = Column(String(256), primary_key=True)

    # Enabled flag for "Run All" functionality
    enabled = Column(Boolean, default=True, nullable=False)

    # Latest test specification
    spec_json = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RunRecord(Base):
    """Database model for test runs."""

    __tablename__ = "runs"

    # Primary key
    id = Column(String(36), primary_key=True)

    # Test spec info (denormalized for querying)
    name = Column(String(256), nullable=False, index=True)
    url = Column(Text)
    method = Column(String(10))
    total_requests = Column(Integer)
    concurrency = Column(Integer)

    # Status and timing
    status = Column(String(20), nullable=False, index=True)
    started_at = Column(DateTime, index=True)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Results
    passed = Column(Boolean)
    requests_completed = Column(Integer, default=0)
    error_message = Column(Text)

    # JSON blobs for complex data
    spec_json = Column(JSON, nullable=False)
    metrics_json = Column(JSON)
    failure_reasons_json = Column(JSON)
    endpoint_metrics_json = Column(JSON)
    sampled_requests_json = Column(JSON)

    def to_run_result(self) -> RunResult:
        """Convert database record to RunResult model.

        Returns:
            RunResult Pydantic model
        """
        # Parse spec
        spec = TestSpec.model_validate(self.spec_json)

        # Parse metrics
        metrics = Metrics()
        if self.metrics_json:
            metrics = Metrics.model_validate(self.metrics_json)

        # Parse endpoint metrics
        endpoint_metrics = []
        if self.endpoint_metrics_json:
            for em in self.endpoint_metrics_json:
                endpoint_metrics.append(EndpointMetrics.model_validate(em))

        # Parse sampled requests
        sampled_requests = []
        if self.sampled_requests_json:
            for sr in self.sampled_requests_json:
                sampled_requests.append(RequestResult.model_validate(sr))

        # Parse failure reasons
        failure_reasons = self.failure_reasons_json or []

        return RunResult(
            id=UUID(self.id),
            spec=spec,
            status=RunStatus(self.status),
            started_at=self.started_at,
            completed_at=self.completed_at,
            metrics=metrics,
            passed=self.passed,
            failure_reasons=failure_reasons,
            endpoint_metrics=endpoint_metrics,
            requests_completed=self.requests_completed,
            error_message=self.error_message,
            sampled_requests=sampled_requests,
        )

    @classmethod
    def from_run_result(cls, result: RunResult) -> "RunRecord":
        """Create database record from RunResult model.

        Args:
            result: RunResult Pydantic model

        Returns:
            RunRecord database model
        """
        # Get URL from spec (handle multi-endpoint)
        url = result.spec.url
        if result.spec.endpoints and len(result.spec.endpoints) > 0:
            url = result.spec.endpoints[0].url

        return cls(
            id=str(result.id),
            name=result.spec.name,
            url=url,
            method=result.spec.method.value,
            total_requests=result.spec.total_requests,
            concurrency=result.spec.concurrency,
            status=result.status.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            passed=result.passed,
            requests_completed=result.requests_completed,
            error_message=result.error_message,
            spec_json=result.spec.model_dump(mode="json"),
            metrics_json=result.metrics.model_dump(mode="json"),
            failure_reasons_json=result.failure_reasons,
            endpoint_metrics_json=[
                em.model_dump(mode="json") for em in result.endpoint_metrics
            ],
            sampled_requests_json=[
                sr.model_dump(mode="json") for sr in result.sampled_requests
            ],
        )


def get_database_url(data_dir: str | Path | None = None) -> str:
    """Get the database URL based on configuration.

    Args:
        data_dir: Data directory (default: from env or ./data)

    Returns:
        SQLAlchemy database URL
    """
    # Check for explicit database URL
    db_url = os.environ.get("ATM_DATABASE_URL")
    if db_url:
        return db_url

    # Default to SQLite in data directory
    if data_dir is None:
        data_dir = os.environ.get("ATM_DATA_DIR", "./data")
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    db_path = data_path / "atm.db"
    return f"sqlite+aiosqlite:///{db_path}"


def get_sync_database_url(data_dir: str | Path | None = None) -> str:
    """Get synchronous database URL for migrations.

    Args:
        data_dir: Data directory

    Returns:
        SQLAlchemy sync database URL
    """
    async_url = get_database_url(data_dir)
    # Convert async URL to sync
    return async_url.replace("+aiosqlite", "").replace("+asyncpg", "")


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, data_dir: str | Path | None = None):
        """Initialize database manager.

        Args:
            data_dir: Data directory for SQLite database
        """
        self.database_url = get_database_url(data_dir)
        self.engine = create_async_engine(
            self.database_url,
            echo=os.environ.get("ATM_DB_ECHO", "").lower() == "true",
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def init_db(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """Get a new database session.

        Returns:
            AsyncSession for database operations
        """
        return self.async_session()
