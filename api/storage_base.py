"""Base storage interface and factory."""

import os
from abc import ABC, abstractmethod
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
