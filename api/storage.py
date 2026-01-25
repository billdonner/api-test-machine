"""JSON file persistence for run results."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.models import RunResult, RunStatus


class RunStorage:
    """JSON file-based storage for test run results.

    Each run is stored as a separate JSON file in the runs directory.
    This allows for easy inspection and simple concurrency.
    """

    def __init__(self, data_dir: str | Path | None = None):
        """Initialize storage with a data directory.

        Args:
            data_dir: Directory for storing run data (default: ./data)
        """
        if data_dir is None:
            data_dir = os.environ.get("ATM_DATA_DIR", "./data")
        self.data_dir = Path(data_dir)
        self.runs_dir = self.data_dir / "runs"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure storage directories exist."""
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: UUID) -> Path:
        """Get the file path for a run.

        Args:
            run_id: Run UUID

        Returns:
            Path to the run's JSON file
        """
        return self.runs_dir / f"{run_id}.json"

    def save(self, result: RunResult) -> None:
        """Save a run result to storage.

        Args:
            result: RunResult to save
        """
        path = self._run_path(result.id)
        data = result.model_dump(mode="json")
        # Convert UUID to string for JSON
        data["id"] = str(result.id)

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load(self, run_id: UUID) -> RunResult | None:
        """Load a run result from storage.

        Args:
            run_id: Run UUID to load

        Returns:
            RunResult if found, None otherwise
        """
        path = self._run_path(run_id)
        if not path.exists():
            return None

        with open(path, "r") as f:
            data = json.load(f)

        return RunResult.model_validate(data)

    def delete(self, run_id: UUID) -> bool:
        """Delete a run from storage.

        Args:
            run_id: Run UUID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._run_path(run_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: RunStatus | None = None,
    ) -> tuple[list[RunResult], int]:
        """List runs from storage.

        Args:
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            status_filter: Optional status to filter by

        Returns:
            Tuple of (runs, total_count)
        """
        # Get all run files sorted by modification time (newest first)
        run_files = sorted(
            self.runs_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        results: list[RunResult] = []
        for path in run_files:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                result = RunResult.model_validate(data)

                # Apply status filter
                if status_filter and result.status != status_filter:
                    continue

                results.append(result)
            except (json.JSONDecodeError, Exception):
                # Skip corrupted files
                continue

        total = len(results)
        paginated = results[offset : offset + limit]

        return paginated, total

    def exists(self, run_id: UUID) -> bool:
        """Check if a run exists in storage.

        Args:
            run_id: Run UUID to check

        Returns:
            True if exists, False otherwise
        """
        return self._run_path(run_id).exists()
