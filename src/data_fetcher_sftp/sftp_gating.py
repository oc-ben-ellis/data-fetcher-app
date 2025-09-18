"""SFTP gating strategies.

This module defines SFTP-specific gating strategies used to control when
SFTP operations are permitted to execute.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from data_fetcher_core.strategy_types import GatingStrategy


@dataclass
class ScheduledDailyGate(GatingStrategy):
    """Gate that only allows execution at a specific time of day."""

    time_of_day: str  # Format: "HH:MM"
    tz: str = "UTC"
    startup_skip_if_already_today: bool = True

    def __post_init__(self) -> None:
        """Initialize the scheduled daily gate state."""
        self._last_execution_date: object = None

    async def wait_if_needed(self) -> None:
        """Wait until the next scheduled time if needed."""
        now = datetime.now(UTC)
        today = now.date()

        # Check if we already executed today
        if self.startup_skip_if_already_today and self._last_execution_date == today:
            return

        # Parse target time
        hour, minute = map(int, self.time_of_day.split(":"))
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If target time has passed today, wait until tomorrow
        if target_time <= now:
            target_time = target_time.replace(day=target_time.day + 1)

        # Wait until target time
        wait_seconds = (target_time - now).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        self._last_execution_date = today


@dataclass
class OncePerIntervalGate(GatingStrategy):
    """Gate that only allows execution once per interval."""

    interval_seconds: int
    jitter_seconds: int = 0

    def __post_init__(self) -> None:
        """Initialize the once per interval gate state."""
        self._last_execution_time = 0.0

    async def wait_if_needed(self) -> None:
        """Wait if the interval hasn't passed since last execution."""
        now = time.time()
        time_since_last = now - self._last_execution_time

        if time_since_last < self.interval_seconds:
            wait_time = self.interval_seconds - time_since_last

            # Add jitter
            if self.jitter_seconds > 0:
                import random  # noqa: PLC0415

                jitter = random.uniform(0, self.jitter_seconds)  # noqa: S311
                wait_time += jitter

            await asyncio.sleep(wait_time)

        self._last_execution_time = time.time()
