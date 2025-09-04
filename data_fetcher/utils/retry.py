"""Unified retry engine for the data_fetcher framework.

This module provides a common retry implementation that all protocol managers
and components can use, ensuring consistent retry behavior across the application.
"""

import asyncio
import functools
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

# Type variables for generic retry functions
T = TypeVar("T")
AsyncFunc = Callable[..., Any]
SyncFunc = Callable[..., Any]


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple[float, float] = (0.5, 1.5)

    def __post_init__(self) -> None:
        """Validate retry configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")  # noqa: TRY003
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")  # noqa: TRY003
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")  # noqa: TRY003
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be greater than 1")  # noqa: TRY003
        if self.jitter_range[0] >= self.jitter_range[1]:
            raise ValueError(  # noqa: TRY003
                "jitter_range must be (min, max) where min < max"
            )


class RetryEngine:
    """Core retry engine that handles retry logic and backoff calculations."""

    def __init__(self, config: RetryConfig) -> None:
        """Initialize the retry engine with configuration.

        Args:
            config: Retry configuration parameters.
        """
        self.config = config

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a specific retry attempt.

        Args:
            attempt: The retry attempt number (0-based).

        Returns:
            Delay in seconds before the next retry.
        """
        # Calculate exponential backoff
        delay = min(
            self.config.base_delay * (self.config.exponential_base**attempt),
            self.config.max_delay,
        )

        # Add jitter if enabled
        if self.config.jitter:
            jitter_factor = random.uniform(*self.config.jitter_range)  # noqa: S311
            delay *= jitter_factor

        return delay

    async def execute_with_retry_async(
        self, func: AsyncFunc, *args: object, **kwargs: object
    ) -> object:
        """Execute an async function with retry logic.

        Args:
            func: The async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function execution.

        Raises:
            The last exception encountered if all retries fail.
        """
        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == self.config.max_retries:
                    # Final attempt failed, re-raise the exception
                    raise last_exception from e

                # Calculate delay and wait before retrying
                delay = self.calculate_delay(attempt)
                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception from last_exception
        raise RuntimeError("Retry execution failed unexpectedly")  # noqa: TRY003

    def execute_with_retry_sync(
        self, func: SyncFunc, *args: object, **kwargs: object
    ) -> object:
        """Execute a sync function with retry logic.

        Args:
            func: The sync function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function execution.

        Raises:
            The last exception encountered if all retries fail.
        """
        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == self.config.max_retries:
                    # Final attempt failed, re-raise the exception
                    raise last_exception from e

                # Calculate delay and wait before retrying
                delay = self.calculate_delay(attempt)
                time.sleep(delay)

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception from last_exception
        raise RuntimeError("Retry execution failed unexpectedly")  # noqa: TRY003


def create_retry_engine(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    *,
    jitter: bool = True,
    jitter_range: tuple[float, float] = (0.5, 1.5),
) -> RetryEngine:
    """Create a retry engine with the specified configuration.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        jitter_range: Range for jitter factor (min, max).

    Returns:
        Configured RetryEngine instance.
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        jitter_range=jitter_range,
    )
    return RetryEngine(config)


def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    *,
    jitter: bool = True,
    jitter_range: tuple[float, float] = (0.5, 1.5),
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),  # noqa: ARG001
) -> Callable[[AsyncFunc], AsyncFunc]:
    """Decorator for async functions with exponential backoff retry logic.

    This is a thin wrapper around the RetryEngine for backward compatibility
    and convenience when using decorators.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        jitter_range: Range for jitter factor (min, max).
        retry_exceptions: Tuple of exception types to retry on.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: AsyncFunc) -> AsyncFunc:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object:
            # Create retry engine for this function
            retry_engine = create_retry_engine(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                jitter_range=jitter_range,
            )

            # Execute with retry logic
            return await retry_engine.execute_with_retry_async(func, *args, **kwargs)

        return wrapper

    return decorator


def sync_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    *,
    jitter: bool = True,
    jitter_range: tuple[float, float] = (0.5, 1.5),
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),  # noqa: ARG001
) -> Callable[[SyncFunc], SyncFunc]:
    """Decorator for sync functions with exponential backoff retry logic.

    This is a thin wrapper around the RetryEngine for backward compatibility
    and convenience when using decorators.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        jitter_range: Range for jitter factor (min, max).
        retry_exceptions: Tuple of exception types to retry on.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: SyncFunc) -> SyncFunc:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            # Create retry engine for this function
            retry_engine = create_retry_engine(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                jitter_range=jitter_range,
            )

            # Execute with retry logic
            return retry_engine.execute_with_retry_sync(func, *args, **kwargs)

        return wrapper

    return decorator


# Convenience functions for common retry scenarios
def create_connection_retry_engine() -> RetryEngine:
    """Create a retry engine optimized for connection operations."""
    return create_retry_engine(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
    )


def create_operation_retry_engine() -> RetryEngine:
    """Create a retry engine optimized for general operations."""
    return create_retry_engine(
        max_retries=3,
        base_delay=0.5,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
    )


def create_aggressive_retry_engine() -> RetryEngine:
    """Create a retry engine for critical operations that need more retries."""
    return create_retry_engine(
        max_retries=5,
        base_delay=0.1,
        max_delay=120.0,
        exponential_base=3.0,
        jitter=True,
    )
