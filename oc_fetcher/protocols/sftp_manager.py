"""SFTP protocol manager and connection handling.

This module provides the SFTPManager class for managing SFTP connections,
including authentication, file operations, and connection management.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pysftp


@dataclass
class ScheduledDailyGate:
    """Gate that only allows execution at a specific time of day."""

    time_of_day: str  # Format: "HH:MM"
    tz: str = "UTC"
    startup_skip_if_already_today: bool = True

    def __post_init__(self) -> None:
        """Initialize the scheduled daily gate state."""
        self._last_execution_date: Any = None

    async def wait_if_needed(self) -> None:
        """Wait until the next scheduled time if needed."""
        now = datetime.now(timezone.utc)
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
class OncePerIntervalGate:
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
                import random

                jitter = random.uniform(0, self.jitter_seconds)
                wait_time += jitter

            await asyncio.sleep(wait_time)

        self._last_execution_time = time.time()


@dataclass
class SftpManager:
    """SFTP connection manager with scheduling and rate limiting."""

    credentials_provider: Any
    connect_timeout: float = 20.0
    daily_gate: ScheduledDailyGate | None = None
    interval_gate: OncePerIntervalGate | None = None
    rate_limit_requests_per_second: float = 5.0

    def __post_init__(self) -> None:
        """Initialize the SFTP manager with internal state and connection management."""
        self._last_request_time = 0.0
        self._rate_limit_lock = asyncio.Lock()
        self._connection: pysftp.Connection | None = None

    async def get_connection(self) -> pysftp.Connection:
        """Get or create SFTP connection."""
        if self._connection is None:
            credentials = await self.credentials_provider.get_credentials()

            # Configure connection options to allow unknown hosts
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None  # Disable host key checking for testing

            self._connection = pysftp.Connection(
                host=credentials.host,
                username=credentials.username,
                password=credentials.password,
                port=credentials.port,
                cnopts=cnopts,
            )
        return self._connection

    async def wait_for_gates(self) -> None:
        """Wait for all gates to allow execution."""
        if self.daily_gate:
            await self.daily_gate.wait_if_needed()

        if self.interval_gate:
            await self.interval_gate.wait_if_needed()

    async def request(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Make an SFTP request with rate limiting."""
        # Wait for gates
        await self.wait_for_gates()

        # Rate limiting
        async with self._rate_limit_lock:
            now = time.time()
            time_since_last = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit_requests_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self._last_request_time = time.time()

        # Execute operation
        conn = await self.get_connection()
        method = getattr(conn, operation)
        return method(*args, **kwargs)

    async def close(self) -> None:
        """Close the SFTP connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
