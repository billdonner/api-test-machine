"""Base storage interface and factory."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import UUID

from engine.models import RunResult, RunStatus


class StorageInterface(Protocol):
    """Protocol defining the storage interface."""

    async def init(self) -> None:
        """Initialize storage (create tables, directories, etc.)."""
        ...

    async def close(self) -> None:
        """Close storage connections."""
        ...

    async def save(self, result: RunResult) -> None:
        """Save a run result."""
        ...

    async def load(self, run_id: UUID) -> RunResult | None:
        """Load a run result by ID."""
        ...

    async def delete(self, run_id: UUID) -> bool:
        """Delete a run by ID. Returns True if deleted."""
        ...

    async def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: RunStatus | None = None,
        name_filter: str | None = None,
    ) -> tuple[list[RunResult], int]:
        """List runs with optional filters. Returns (runs, total_count)."""
        ...

    async def exists(self, run_id: UUID) -> bool:
        """Check if a run exists."""
        ...

    async def get_detailed_stats(self) -> dict:
        """Get detailed storage statistics."""
        ...

    async def save_test_config(self, name: str, spec: dict, enabled: bool = True) -> None:
        """Save or update a test configuration."""
        ...

    async def get_test_config(self, name: str) -> dict | None:
        """Get a test configuration by name."""
        ...

    async def set_test_enabled(self, name: str, enabled: bool) -> bool:
        """Set whether a test is enabled."""
        ...

    async def list_test_configs(self, enabled_only: bool = False) -> list[dict]:
        """List all test configurations."""
        ...

    async def delete_test_config(self, name: str) -> bool:
        """Delete a test configuration."""
        ...

    async def sync_test_configs_from_runs(self) -> int:
        """Sync test configs from existing runs."""
        ...


class AsyncJSONStorage:
    """Async wrapper around the synchronous JSON file storage.

    Provides the same interface as SQLiteStorage but uses JSON files.
    """

    def __init__(self, data_dir: str | Path | None = None):
        """Initialize with a data directory."""
        from api.storage import RunStorage
        self._storage = RunStorage(data_dir)

    async def init(self) -> None:
        """No initialization needed for JSON storage."""
        pass

    async def close(self) -> None:
        """No cleanup needed for JSON storage."""
        pass

    async def save(self, result: RunResult) -> None:
        """Save a run result to JSON file."""
        self._storage.save(result)

    async def load(self, run_id: UUID) -> RunResult | None:
        """Load a run result from JSON file."""
        return self._storage.load(run_id)

    async def delete(self, run_id: UUID) -> bool:
        """Delete a run's JSON file."""
        return self._storage.delete(run_id)

    async def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: RunStatus | None = None,
        name_filter: str | None = None,
    ) -> tuple[list[RunResult], int]:
        """List runs from JSON files."""
        runs, total = self._storage.list_runs(
            limit=limit,
            offset=offset,
            status_filter=status_filter,
        )
        # Apply name filter if specified
        if name_filter:
            runs = [r for r in runs if r.spec.name == name_filter]
            total = len(runs)
        return runs, total

    async def exists(self, run_id: UUID) -> bool:
        """Check if a JSON file exists for this run."""
        return self._storage.exists(run_id)

    async def get_detailed_stats(self) -> dict:
        """Get detailed storage statistics for JSON storage."""
        runs, total = self._storage.list_runs(limit=1000)

        # Calculate stats from runs
        runs_by_status = {}
        runs_by_day = {}
        total_requests = 0
        oldest_date = None
        newest_date = None
        test_counts = {}

        for run in runs:
            # By status
            status = run.status.value
            runs_by_status[status] = runs_by_status.get(status, 0) + 1

            # By day
            if run.created_at:
                day = run.created_at.strftime("%Y-%m-%d")
                if day not in runs_by_day:
                    runs_by_day[day] = {"count": 0, "passed": 0, "failed": 0}
                runs_by_day[day]["count"] += 1
                if run.passed is True:
                    runs_by_day[day]["passed"] += 1
                elif run.passed is False:
                    runs_by_day[day]["failed"] += 1

                # Track dates
                if oldest_date is None or run.created_at < oldest_date:
                    oldest_date = run.created_at
                if newest_date is None or run.created_at > newest_date:
                    newest_date = run.created_at

            # Total requests
            total_requests += run.requests_completed

            # Test counts
            name = run.spec.name
            if name not in test_counts:
                test_counts[name] = {"run_count": 0, "passed": 0, "failed": 0, "last_run": None}
            test_counts[name]["run_count"] += 1
            if run.passed is True:
                test_counts[name]["passed"] += 1
            elif run.passed is False:
                test_counts[name]["failed"] += 1
            if run.created_at:
                if test_counts[name]["last_run"] is None or run.created_at > datetime.fromisoformat(test_counts[name]["last_run"]):
                    test_counts[name]["last_run"] = run.created_at.isoformat()

        # Format runs by status
        status_list = [{"status": k, "count": v} for k, v in runs_by_status.items()]

        # Format runs by day (last 30 days only)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        day_list = [
            {"date": k, "count": v["count"], "passed": v["passed"], "failed": v["failed"]}
            for k, v in sorted(runs_by_day.items())
            if k >= thirty_days_ago
        ]

        # Top tests
        top_tests = sorted(
            [{"name": k, **v} for k, v in test_counts.items()],
            key=lambda x: x["run_count"],
            reverse=True
        )[:10]

        # Calculate total size of JSON files
        total_size = 0
        runs_dir = self._storage.runs_dir
        if runs_dir.exists():
            for f in runs_dir.glob("*.json"):
                total_size += f.stat().st_size

        return {
            "storage_type": "json",
            "database_path": str(runs_dir),
            "database_size_bytes": total_size,
            "database_size_human": self._format_size(total_size),
            "sqlite_version": None,
            "total_runs": total,
            "runs_by_status": status_list,
            "runs_by_day": day_list,
            "total_requests_stored": total_requests,
            "avg_requests_per_run": round(total_requests / total, 1) if total > 0 else 0,
            "oldest_run_date": oldest_date,
            "newest_run_date": newest_date,
            "top_tests": top_tests,
            "avg_run_duration_seconds": None,
            "total_data_transferred_bytes": total_requests * 1024,
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _get_configs_file(self) -> Path:
        """Get path to test configs JSON file."""
        return self._storage.data_dir / "test_configs.json"

    def _load_configs(self) -> dict:
        """Load test configs from JSON file."""
        configs_file = self._get_configs_file()
        if configs_file.exists():
            import json
            with open(configs_file) as f:
                return json.load(f)
        return {}

    def _save_configs(self, configs: dict) -> None:
        """Save test configs to JSON file."""
        import json
        configs_file = self._get_configs_file()
        with open(configs_file, "w") as f:
            json.dump(configs, f, indent=2, default=str)

    async def save_test_config(self, name: str, spec: dict, enabled: bool = True) -> None:
        """Save or update a test configuration."""
        configs = self._load_configs()
        now = datetime.utcnow().isoformat()
        if name in configs:
            configs[name]["spec"] = spec
            configs[name]["enabled"] = enabled
            configs[name]["updated_at"] = now
        else:
            configs[name] = {
                "name": name,
                "enabled": enabled,
                "spec": spec,
                "created_at": now,
                "updated_at": now,
            }
        self._save_configs(configs)

    async def get_test_config(self, name: str) -> dict | None:
        """Get a test configuration by name."""
        configs = self._load_configs()
        return configs.get(name)

    async def set_test_enabled(self, name: str, enabled: bool) -> bool:
        """Set whether a test is enabled."""
        configs = self._load_configs()
        if name in configs:
            configs[name]["enabled"] = enabled
            configs[name]["updated_at"] = datetime.utcnow().isoformat()
            self._save_configs(configs)
            return True
        return False

    async def list_test_configs(self, enabled_only: bool = False) -> list[dict]:
        """List all test configurations."""
        configs = self._load_configs()
        result = []
        for name, config in sorted(configs.items()):
            if enabled_only and not config.get("enabled", True):
                continue
            result.append(config)
        return result

    async def delete_test_config(self, name: str) -> bool:
        """Delete a test configuration."""
        configs = self._load_configs()
        if name in configs:
            del configs[name]
            self._save_configs(configs)
            return True
        return False

    async def sync_test_configs_from_runs(self) -> int:
        """Sync test configs from existing runs."""
        configs = self._load_configs()
        runs, _ = self._storage.list_runs(limit=1000)

        # Group by name and get most recent
        by_name = {}
        for run in runs:
            name = run.spec.name
            if name not in by_name or (run.created_at and run.created_at > by_name[name].created_at):
                by_name[name] = run

        count = 0
        now = datetime.utcnow().isoformat()
        for name, run in by_name.items():
            if name not in configs:
                configs[name] = {
                    "name": name,
                    "enabled": True,
                    "spec": run.spec.model_dump(mode="json"),
                    "created_at": now,
                    "updated_at": now,
                }
                count += 1

        if count > 0:
            self._save_configs(configs)
        return count


def create_storage(data_dir: str | Path | None = None) -> StorageInterface:
    """Create the appropriate storage backend based on configuration.

    Configuration options (in order of precedence):
    1. ATM_DATABASE_URL env var - use SQLite/PostgreSQL
    2. ATM_STORAGE_TYPE env var - "sqlite" or "json"
    3. Default: SQLite

    Args:
        data_dir: Directory for data files

    Returns:
        Storage instance implementing StorageInterface
    """
    storage_type = os.environ.get("ATM_STORAGE_TYPE", "sqlite").lower()

    # If explicit database URL is set, use SQLite
    if os.environ.get("ATM_DATABASE_URL"):
        storage_type = "sqlite"

    if storage_type == "json":
        return AsyncJSONStorage(data_dir)
    else:
        from api.sqlite_storage import SQLiteStorage
        return SQLiteStorage(data_dir)
