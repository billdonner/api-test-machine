"""Agent main entry point."""

import asyncio
import logging
import os
import signal
import sys

from agent.orchestrator import TestOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for the agent."""
    api_url = os.environ.get("ATM_API_URL", "http://localhost:8000")
    api_key = os.environ.get("ATM_API_KEY")

    orchestrator = TestOrchestrator(api_url=api_url, api_key=api_key)

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await orchestrator.start()
        logger.info("Agent started, waiting for shutdown signal...")

        # Wait for shutdown
        await shutdown_event.wait()

    finally:
        await orchestrator.stop()
        logger.info("Agent shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
