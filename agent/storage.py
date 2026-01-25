"""State persistence for the agent."""

import json
import os
from pathlib import Path

from agent.models import AgentState


class AgentStorage:
    """JSON file-based storage for agent state."""

    def __init__(self, data_dir: str | Path | None = None):
        """Initialize storage with a data directory.

        Args:
            data_dir: Directory for storing state (default: ./data)
        """
        if data_dir is None:
            data_dir = os.environ.get("ATM_DATA_DIR", "./data")
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "state.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure storage directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AgentState:
        """Load agent state from disk.

        Returns:
            AgentState (empty if file doesn't exist)
        """
        if not self.state_file.exists():
            return AgentState()

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            return AgentState.model_validate(data)
        except (json.JSONDecodeError, Exception):
            # Return empty state on error
            return AgentState()

    def save(self, state: AgentState) -> None:
        """Save agent state to disk.

        Args:
            state: AgentState to save
        """
        data = state.model_dump(mode="json")
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def delete(self) -> None:
        """Delete state file."""
        if self.state_file.exists():
            self.state_file.unlink()
