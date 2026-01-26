"""SQLite-based persistent storage for run results."""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence
from uuid import UUID

from sqlalchemy import case, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import DatabaseManager, RunRecord, TestConfig, get_sync_database_url
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

    async def get_detailed_stats(self) -> dict:
        """Get detailed storage statistics for status page.

        Returns:
            Comprehensive dictionary with storage stats
        """
        await self.init()

        # Get database file info
        db_path = None
        db_size = None
        db_size_human = None
        sqlite_version = None

        # Extract path from URL
        url = self.db.database_url
        if "sqlite" in url:
            # Extract path from sqlite:///path or sqlite+aiosqlite:///path
            path_part = url.split("///")[-1]
            db_path = path_part
            if os.path.exists(path_part):
                db_size = os.path.getsize(path_part)
                db_size_human = self._format_size(db_size)

            # Get SQLite version
            try:
                sqlite_version = sqlite3.sqlite_version
            except Exception:
                pass

        async with self.db.get_session() as session:
            # Total runs
            total_result = await session.execute(
                select(func.count(RunRecord.id))
            )
            total_runs = total_result.scalar() or 0

            # Runs by status
            runs_by_status = []
            for status in RunStatus:
                result = await session.execute(
                    select(func.count(RunRecord.id)).where(
                        RunRecord.status == status.value
                    )
                )
                count = result.scalar() or 0
                if count > 0:
                    runs_by_status.append({
                        "status": status.value,
                        "count": count
                    })

            # Runs by day (last 30 days)
            runs_by_day = []
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            # Get all runs from last 30 days grouped by date
            result = await session.execute(
                select(
                    func.date(RunRecord.created_at).label("date"),
                    func.count(RunRecord.id).label("count"),
                    func.sum(
                        case(
                            (RunRecord.passed == True, 1),
                            else_=0
                        )
                    ).label("passed"),
                    func.sum(
                        case(
                            (RunRecord.passed == False, 1),
                            else_=0
                        )
                    ).label("failed")
                ).where(
                    RunRecord.created_at >= thirty_days_ago
                ).group_by(
                    func.date(RunRecord.created_at)
                ).order_by(
                    func.date(RunRecord.created_at)
                )
            )
            for row in result:
                runs_by_day.append({
                    "date": str(row.date) if row.date else "",
                    "count": row.count or 0,
                    "passed": row.passed or 0,
                    "failed": row.failed or 0
                })

            # Total requests stored
            total_requests_result = await session.execute(
                select(func.sum(RunRecord.requests_completed))
            )
            total_requests = total_requests_result.scalar() or 0

            # Average requests per run
            avg_requests = total_requests / total_runs if total_runs > 0 else 0

            # Oldest and newest run dates
            oldest_result = await session.execute(
                select(func.min(RunRecord.created_at))
            )
            oldest_run_date = oldest_result.scalar()

            newest_result = await session.execute(
                select(func.max(RunRecord.created_at))
            )
            newest_run_date = newest_result.scalar()

            # Top tests by run count
            top_tests_result = await session.execute(
                select(
                    RunRecord.name,
                    func.count(RunRecord.id).label("run_count"),
                    func.sum(
                        case(
                            (RunRecord.passed == True, 1),
                            else_=0
                        )
                    ).label("passed"),
                    func.sum(
                        case(
                            (RunRecord.passed == False, 1),
                            else_=0
                        )
                    ).label("failed"),
                    func.max(RunRecord.created_at).label("last_run")
                ).group_by(
                    RunRecord.name
                ).order_by(
                    func.count(RunRecord.id).desc()
                ).limit(10)
            )
            top_tests = []
            for row in top_tests_result:
                top_tests.append({
                    "name": row.name,
                    "run_count": row.run_count,
                    "passed": row.passed or 0,
                    "failed": row.failed or 0,
                    "last_run": row.last_run.isoformat() if row.last_run else None
                })

            # Average run duration for completed runs
            avg_duration_result = await session.execute(
                select(
                    func.avg(
                        func.julianday(RunRecord.completed_at) -
                        func.julianday(RunRecord.started_at)
                    ) * 86400  # Convert days to seconds
                ).where(
                    RunRecord.status == "completed",
                    RunRecord.started_at.isnot(None),
                    RunRecord.completed_at.isnot(None)
                )
            )
            avg_duration = avg_duration_result.scalar()

            # Total data transferred (estimate from completed requests * avg response size)
            # This is a rough estimate
            total_data = total_requests * 1024  # Rough estimate: 1KB per request

            return {
                "storage_type": "sqlite",
                "database_path": db_path,
                "database_size_bytes": db_size,
                "database_size_human": db_size_human,
                "sqlite_version": sqlite_version,
                "total_runs": total_runs,
                "runs_by_status": runs_by_status,
                "runs_by_day": runs_by_day,
                "total_requests_stored": total_requests,
                "avg_requests_per_run": round(avg_requests, 1),
                "oldest_run_date": oldest_run_date,
                "newest_run_date": newest_run_date,
                "top_tests": top_tests,
                "avg_run_duration_seconds": round(avg_duration, 2) if avg_duration else None,
                "total_data_transferred_bytes": total_data,
            }

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    # Test config management methods

    async def save_test_config(self, name: str, spec: dict, enabled: bool = True) -> None:
        """Save or update a test configuration.

        Args:
            name: Test name (unique identifier)
            spec: Test specification as dict
            enabled: Whether the test is enabled for batch runs
        """
        await self.init()

        async with self.db.get_session() as session:
            existing = await session.get(TestConfig, name)

            if existing:
                existing.spec_json = spec
                existing.enabled = enabled
                existing.updated_at = datetime.utcnow()
            else:
                config = TestConfig(
                    name=name,
                    enabled=enabled,
                    spec_json=spec,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(config)

            await session.commit()

    async def get_test_config(self, name: str) -> dict | None:
        """Get a test configuration by name.

        Args:
            name: Test name

        Returns:
            Dict with name, enabled, spec_json or None
        """
        await self.init()

        async with self.db.get_session() as session:
            config = await session.get(TestConfig, name)
            if config:
                return {
                    "name": config.name,
                    "enabled": config.enabled,
                    "spec": config.spec_json,
                    "created_at": config.created_at,
                    "updated_at": config.updated_at,
                }
            return None

    async def set_test_enabled(self, name: str, enabled: bool) -> bool:
        """Set whether a test is enabled.

        Args:
            name: Test name
            enabled: Whether to enable the test

        Returns:
            True if updated, False if not found
        """
        await self.init()

        async with self.db.get_session() as session:
            config = await session.get(TestConfig, name)
            if config:
                config.enabled = enabled
                config.updated_at = datetime.utcnow()
                await session.commit()
                return True
            return False

    async def list_test_configs(self, enabled_only: bool = False) -> list[dict]:
        """List all test configurations.

        Args:
            enabled_only: If True, only return enabled tests

        Returns:
            List of test config dicts
        """
        await self.init()

        async with self.db.get_session() as session:
            query = select(TestConfig)
            if enabled_only:
                query = query.where(TestConfig.enabled == True)
            query = query.order_by(TestConfig.name)

            result = await session.execute(query)
            configs = result.scalars().all()

            return [
                {
                    "name": c.name,
                    "enabled": c.enabled,
                    "spec": c.spec_json,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in configs
            ]

    async def delete_test_config(self, name: str) -> bool:
        """Delete a test configuration.

        Args:
            name: Test name

        Returns:
            True if deleted, False if not found
        """
        await self.init()

        async with self.db.get_session() as session:
            result = await session.execute(
                delete(TestConfig).where(TestConfig.name == name)
            )
            await session.commit()
            return result.rowcount > 0

    async def sync_test_configs_from_runs(self) -> int:
        """Sync test configs from existing runs.

        Creates test configs for each unique test name in runs,
        using the most recent spec for each test.

        Returns:
            Number of configs created/updated
        """
        await self.init()

        async with self.db.get_session() as session:
            # Get distinct test names with their most recent spec
            from sqlalchemy import desc

            query = select(
                RunRecord.name,
                RunRecord.spec_json
            ).order_by(
                RunRecord.name,
                desc(RunRecord.created_at)
            ).distinct(RunRecord.name)

            result = await session.execute(query)
            rows = result.all()

            count = 0
            for row in rows:
                name, spec_json = row
                existing = await session.get(TestConfig, name)
                if not existing:
                    config = TestConfig(
                        name=name,
                        enabled=True,
                        spec_json=spec_json,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(config)
                    count += 1

            await session.commit()
            return count
