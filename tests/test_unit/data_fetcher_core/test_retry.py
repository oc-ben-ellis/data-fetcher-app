"""Tests for the unified retry engine."""

import pytest

from data_fetcher_core.utils.retry import (
    RetryConfig,
    RetryEngine,
    async_retry_with_backoff,
    create_aggressive_retry_engine,
    create_connection_retry_engine,
    create_operation_retry_engine,
    create_retry_engine,
    sync_retry_with_backoff,
)


class TestRetryConfig:
    """Test RetryConfig validation."""

    def test_valid_config(self) -> None:
        """Test valid configuration creation."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=True,
            jitter_range=(0.3, 1.7),
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is True
        assert config.jitter_range == (0.3, 1.7)

    def test_invalid_max_retries(self) -> None:
        """Test invalid max_retries validation."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryConfig(max_retries=-1)

    def test_invalid_base_delay(self) -> None:
        """Test invalid base_delay validation."""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryConfig(base_delay=0)

    def test_invalid_max_delay(self) -> None:
        """Test invalid max_delay validation."""
        with pytest.raises(ValueError, match="max_delay must be positive"):
            RetryConfig(max_delay=-1)

    def test_invalid_exponential_base(self) -> None:
        """Test invalid exponential_base validation."""
        with pytest.raises(ValueError, match="exponential_base must be greater than 1"):
            RetryConfig(exponential_base=1.0)

    def test_invalid_jitter_range(self) -> None:
        """Test invalid jitter_range validation."""
        with pytest.raises(ValueError, match="jitter_range must be"):
            RetryConfig(jitter_range=(1.0, 0.5))


class TestRetryEngine:
    """Test RetryEngine functionality."""

    def test_calculate_delay_no_jitter(self) -> None:
        """Test delay calculation without jitter."""
        config = RetryConfig(jitter=False)
        engine = RetryEngine(config)

        # Test exponential backoff
        assert engine.calculate_delay(0) == 1.0  # base_delay
        assert engine.calculate_delay(1) == 2.0  # base_delay * exponential_base
        assert engine.calculate_delay(2) == 4.0  # base_delay * exponential_base^2
        assert engine.calculate_delay(3) == 8.0  # base_delay * exponential_base^3

    def test_calculate_delay_with_jitter(self) -> None:
        """Test delay calculation with jitter."""
        config = RetryConfig(jitter=True)
        engine = RetryEngine(config)

        # Jitter should be within expected range
        delay = engine.calculate_delay(1)
        assert 1.0 <= delay <= 3.0  # base_delay * exponential_base * jitter_range

    def test_calculate_delay_max_cap(self) -> None:
        """Test delay calculation respects max_delay cap."""
        config = RetryConfig(max_delay=5.0, jitter=False)
        engine = RetryEngine(config)

        # Should cap at max_delay for high attempt numbers
        # For attempt 10: base_delay * (exponential_base^10) = 1 * (2^10) = 1024
        # But should be capped at max_delay = 5.0
        assert engine.calculate_delay(10) == 5.0

        # For attempt 2: base_delay * (exponential_base^2) = 1 * (2^2) = 4
        # Should not be capped
        assert engine.calculate_delay(2) == 4.0

    @pytest.mark.asyncio
    async def test_execute_with_retry_async_success_first_try(self) -> None:
        """Test async retry execution succeeds on first try."""
        config = RetryConfig(max_retries=3)
        engine = RetryEngine(config)

        call_count = 0

        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await engine.execute_with_retry_async(success_func)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_async_success_after_retries(self) -> None:
        """Test async retry execution succeeds after some retries."""
        config = RetryConfig(max_retries=3, base_delay=0.01)  # Fast for testing
        engine = RetryEngine(config)

        call_count = 0

        async def retry_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        result = await engine.execute_with_retry_async(retry_func)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_async_all_retries_fail(self) -> None:
        """Test async retry execution fails after all retries."""
        config = RetryConfig(max_retries=2, base_delay=0.01)  # Fast for testing
        engine = RetryEngine(config)

        call_count = 0

        async def always_fail_func() -> str:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Persistent failure")

        with pytest.raises(RuntimeError, match="Persistent failure"):
            await engine.execute_with_retry_async(always_fail_func)

        assert call_count == 3  # Initial + 2 retries

    def test_execute_with_retry_sync_success_first_try(self) -> None:
        """Test sync retry execution succeeds on first try."""
        config = RetryConfig(max_retries=3)
        engine = RetryEngine(config)

        call_count = 0

        def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = engine.execute_with_retry_sync(success_func)
        assert result == "success"
        assert call_count == 1

    def test_execute_with_retry_sync_success_after_retries(self) -> None:
        """Test sync retry execution succeeds after some retries."""
        config = RetryConfig(max_retries=3, base_delay=0.01)  # Fast for testing
        engine = RetryEngine(config)

        call_count = 0

        def retry_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        result = engine.execute_with_retry_sync(retry_func)
        assert result == "success"
        assert call_count == 3


class TestRetryEngineFactories:
    """Test retry engine factory functions."""

    def test_create_retry_engine(self) -> None:
        """Test create_retry_engine with custom parameters."""
        engine = create_retry_engine(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert engine.config.max_retries == 5
        assert engine.config.base_delay == 2.0
        assert engine.config.max_delay == 120.0
        assert engine.config.exponential_base == 3.0
        assert engine.config.jitter is False

    def test_create_connection_retry_engine(self) -> None:
        """Test create_connection_retry_engine."""
        engine = create_connection_retry_engine()

        assert engine.config.max_retries == 3
        assert engine.config.base_delay == 1.0
        assert engine.config.max_delay == 60.0
        assert engine.config.exponential_base == 2.0
        assert engine.config.jitter is True

    def test_create_operation_retry_engine(self) -> None:
        """Test create_operation_retry_engine."""
        engine = create_operation_retry_engine()

        assert engine.config.max_retries == 3
        assert engine.config.base_delay == 0.5
        assert engine.config.max_delay == 30.0
        assert engine.config.exponential_base == 2.0
        assert engine.config.jitter is True

    def test_create_aggressive_retry_engine(self) -> None:
        """Test create_aggressive_retry_engine."""
        engine = create_aggressive_retry_engine()

        assert engine.config.max_retries == 5
        assert engine.config.base_delay == 0.1
        assert engine.config.max_delay == 120.0
        assert engine.config.exponential_base == 3.0
        assert engine.config.jitter is True


class TestRetryDecorators:
    """Test retry decorators."""

    @pytest.mark.asyncio
    async def test_async_retry_with_backoff(self) -> None:
        """Test async_retry_with_backoff decorator."""
        call_count = 0

        @async_retry_with_backoff(max_retries=2, base_delay=0.01)
        async def retry_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        result = await retry_func()
        assert result == "success"
        assert call_count == 3

    def test_sync_retry_with_backoff(self) -> None:
        """Test sync_retry_with_backoff decorator."""
        call_count = 0

        @sync_retry_with_backoff(max_retries=2, base_delay=0.01)
        def retry_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        result = retry_func()
        assert result == "success"
        assert call_count == 3
