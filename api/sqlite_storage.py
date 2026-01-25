"""SQLite-based persistent storage for run results."""

import os
from pathlib import Path
from typing import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import DatabaseManager, RunRecord
from engine.models import RunResult, RunStatus


class SQLiteStorage:
    """SQLite database storage for test run results.

    Provides the same interface as RunStorage but uses SQLAlchemy
    with SQLite for better querying and indexing.
    """

    def __init__(self, data_dir: str | Path | None = None):
        """Initialize SQLite storage.

        Args:
            data_dir: Directory for database file (default: ./data)
        """
        self.db = DatabaseManager(data_dir)
        self._initialized = False

    async def init(self) -> None:
        """Initialize the database (create tables if needed)."""
        if not self._initialized:
            await self.db.init_db()
            self._initialized = True

    async def close(self) -> None:
        """Close database connections."""
        await self.db.close()

    async def save(self, result: RunResult) -> None:
        """Save a run result to the database.

        Args:
            result: RunResult to save
        """
        await self.init()

        async with self.db.get_session() as session:
            # Check if record exists
            existing = await session.get(RunRecord, str(result.id))

            if existing:
                # Update existing record
                record = RunRecord.from_run_result(result)
                existing.name = record.name
                existing.url = record.url
                existing.method = record.method
                existing.total_requests = record.total_requests
                existing.concurrency = record.concurrency
                existing.status = record.status
                existing.started_at = record.started_at
                existing.completed_at = record.completed_at
                existing.passed = record.passed
                existing.requests_completed = record.requests_completed
                existing.error_message = record.error_message
                existing.spec_json = record.spec_json
                existing.metrics_json = record.metrics_json
                existing.failure_reasons_json = record.failure_reasons_json
                existing.endpoint_metrics_json = record.endpoint_metrics_json
                existing.sampled_requests_json = record.sampled_requests_json
            else:
                # Insert new record
                record = RunRecord.from_run_result(result)
                session.add(record)

            await session.commit()

    async def load(self, run_id: UUID) -> RunResult | None:
        """Load a run result from the database.

        Args:
            run_id: Run UUID to load

        Returns:
            RunResult if found, None otherwise
        """
        await self.init()

        async with self.db.get_session() as session:
            record = await session.get(RunRecord, str(run_id))
            if record:
                return record.to_run_result()
            return None

    async def delete(self, run_id: UUID) -> bool:
        """Delete a run from the database.

        Args:
            run_id: Run UUID to delete

        Returns:
            True if deleted, False if not found
        """
        await self.init()

        async with self.db.get_session() as session:
            result = await session.execute(
                delete(RunRecord).where(RunRecord.id == str(run_id))
            )
            await session.commit()
            return result.rowcount > 0

    async def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: RunStatus | None = None,
        name_filter: str | None = None,
    ) -> tuple[list[RunResult], int]:
        """List runs from the database.

        Args:
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            status_filter: Optional status to filter by
            name_filter: Optional name to filter by (exact match)

        Returns:
            Tuple of (runs, total_count)
        """
        await self.init()

        async with self.db.get_session() as session:
            # Build base query
            query = select(RunRecord)
            count_query = select(func.count(RunRecord.id))

            # Apply filters
            if status_filter:
                query = query.where(RunRecord.status == status_filter.value)
                count_query = count_query.where(
                    RunRecord.status == status_filter.value
                )

            if name_filter:
                query = query.where(RunRecord.name == name_filter)
                count_query = count_query.where(RunRecord.name == name_filter)

            # Get total count
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Get paginated results (newest first)
            query = query.order_by(RunRecord.created_at.desc())
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            records: Sequence[RunRecord] = result.scalars().all()

            runs = [record.to_run_result() for record in records]

            return runs, total

    async def exists(self, run_id: UUID) -> bool:
        """Check if a run exists in the database.

        Args:
            run_id: Run UUID to check

        Returns:
            True if exists, False otherwise
        """
        await self.init()

        async with self.db.get_session() as session:
            result = await session.execute(
                select(func.count(RunRecord.id)).where(
                    RunRecord.id == str(run_id)
                )
            )
            count = result.scalar() or 0
            return count > 0

    async def get_runs_by_name(
        self, name: str, limit: int = 10
    ) -> list[RunResult]:
        """Get runs by test name.

        Args:
            name: Test name to search for
            limit: Maximum runs to return

        Returns:
            List of matching RunResults
        """
        runs, _ = await self.list_runs(
            limit=limit,
            name_filter=name,
        )
        return runs

    async def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        await self.init()

        async with self.db.get_session() as session:
            # Total runs
            total_result = await session.execute(
                select(func.count(RunRecord.id))
            )
            total = total_result.scalar() or 0

            # By status
            status_counts = {}
            for status in RunStatus:
                result = await session.execute(
                    select(func.count(RunRecord.id)).where(
                        RunRecord.status == status.value
                    )
                )
                count = result.scalar() or 0
                if count > 0:
                    status_counts[status.value] = count

            return {
                "total_runs": total,
                "by_status": status_counts,
                "storage_type": "sqlite",
                "database_url": self.db.database_url,
            }
