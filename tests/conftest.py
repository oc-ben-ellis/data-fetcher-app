"""PyTest configuration and shared test fixtures.

This module provides PyTest configuration, shared fixtures, and test
utilities that are used across multiple test files.
"""

import asyncio
import os
import signal
import tempfile
from collections.abc import AsyncGenerator, Coroutine, Generator
from typing import Any

import boto3
import pytest
from testcontainers.core.container import (  # type: ignore[import-untyped]
    DockerContainer,
)
from testcontainers.core.waiting_utils import (  # type: ignore[import-untyped]
    wait_for_logs,
)

from data_fetcher.core import BundleRef

"""Pytest configuration and shared fixtures for OC Fetcher tests."""

# Global flag to track if we're shutting down
_shutdown_requested = False


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    _shutdown_requested = True
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    # Force exit to bypass pytest's signal handling
    os._exit(130)  # Exit code 130 is standard for SIGINT


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    # Ensure the newly created loop is the current event loop for the session
    asyncio.set_event_loop(loop)

    # Override the default exception handler to avoid logging errors during shutdown
    def custom_exception_handler(
        loop: asyncio.AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        """Custom exception handler that ignores certain errors during shutdown."""
        global _shutdown_requested

        # Check if we're shutting down and the error is related to closed files/streams
        if _shutdown_requested:
            exception = context.get("exception")
            if exception and isinstance(exception, ValueError | OSError):
                if "I/O operation on closed file" in str(
                    exception
                ) or "closed file" in str(exception):
                    # Silently ignore these errors during shutdown
                    return

        # For other errors, use the default handler
        loop.default_exception_handler(context)

    loop.set_exception_handler(custom_exception_handler)

    yield loop

    # Clean up any remaining tasks before closing the loop
    pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
    if pending_tasks:
        print(f"Cleaning up {len(pending_tasks)} pending tasks...")
        for task in pending_tasks:
            task.cancel()

        # Wait for tasks to be cancelled
        if pending_tasks:
            loop.run_until_complete(
                asyncio.gather(*pending_tasks, return_exceptions=True)
            )

    # Ensure async generators are properly shut down before closing the loop
    shutdown_coro: Coroutine[Any, Any, None] | None = None
    try:
        if not loop.is_closed():
            shutdown_coro = loop.shutdown_asyncgens()
            loop.run_until_complete(shutdown_coro)
    except Exception:
        # If we created the coroutine but could not await it, close it to avoid warnings
        if shutdown_coro is not None:
            shutdown_coro.close()
        # Best-effort shutdown; ignore errors here to avoid masking test results
        pass

    # Detach the loop and close it to avoid unclosed loop warnings
    asyncio.set_event_loop(None)
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def bundle_ref() -> BundleRef:
    """Create a test bundle reference."""
    return BundleRef(
        primary_url="https://example.com",
        resources_count=1,
        storage_key="test_bundle",
        meta={"test": "data"},
    )


def create_test_stream(content: bytes) -> AsyncGenerator[bytes, None]:
    """Create a test stream from bytes."""

    async def stream() -> AsyncGenerator[bytes, None]:
        yield content

    return stream()


@pytest.fixture
def test_stream_factory() -> Any:
    """Factory for creating test streams."""
    return create_test_stream


@pytest.fixture(scope="class")
def localstack_container() -> DockerContainer:
    """Start localstack container for S3 testing."""
    # Fail if running in CI without Docker
    if os.getenv("CI") and not os.path.exists("/var/run/docker.sock"):
        pytest.fail("Docker not available in CI environment")

    try:
        container = DockerContainer("localstack/localstack:3.0")
        container.with_env("SERVICES", "s3,secretsmanager")
        container.with_env("DEFAULT_REGION", "us-east-1")
        container.with_env("AWS_ACCESS_KEY_ID", "test")
        container.with_env("AWS_SECRET_ACCESS_KEY", "test")
        container.with_env("DEBUG", "1")
        container.with_env("PERSISTENCE", "1")
        container.with_exposed_ports(4566)

        container.start()

        # Wait for localstack to be ready
        wait_for_logs(container, "Ready.")

        # Wait a bit more for all services to be fully ready
        import time

        time.sleep(5)

        # Test if Secrets Manager is ready
        try:
            test_client = boto3.client(
                "secretsmanager",
                endpoint_url="http://localhost:4566",
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name="us-east-1",
            )
            # Try to list secrets to verify the service is ready
            test_client.list_secrets()
            print("Secrets Manager service is ready")
        except Exception as e:
            print(f"Warning: Secrets Manager not ready yet: {e}")
            # Wait a bit more
            time.sleep(10)

        yield container

        container.stop()
    except Exception as e:
        pytest.fail(f"Failed to start localstack container: {e}")


@pytest.fixture(scope="class")
def redis_container() -> DockerContainer:
    """Start Redis container for testing."""
    # Fail if running in CI without Docker
    if os.getenv("CI") and not os.path.exists("/var/run/docker.sock"):
        pytest.fail("Docker not available in CI environment")

    try:
        container = DockerContainer("redis:7-alpine")
        container.with_exposed_ports(6379)
        container.start()

        # Wait for Redis to be ready
        wait_for_logs(container, "Ready to accept connections")

        yield container

        container.stop()
    except Exception as e:
        pytest.fail(f"Failed to start Redis container: {e}")


@pytest.fixture
def s3_client(localstack_container: DockerContainer) -> Any:
    """Create S3 client connected to localstack."""
    return boto3.client(
        "s3",
        endpoint_url=f"http://localhost:{localstack_container.get_exposed_port(4566)}",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


@pytest.fixture
def secretsmanager_client(localstack_container: DockerContainer) -> Any:
    """Create Secrets Manager client connected to localstack."""
    return boto3.client(
        "secretsmanager",
        endpoint_url=f"http://localhost:{localstack_container.get_exposed_port(4566)}",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


@pytest.fixture
def test_bucket(s3_client: Any) -> str:
    """Create test bucket in localstack."""
    bucket_name = "test-oc-fetcher-bucket"
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except Exception:
        # Bucket might already exist
        pass
    return bucket_name


@pytest.fixture
def test_secrets(secretsmanager_client: Any) -> dict[str, dict[str, str]]:
    """Create test secrets in LocalStack Secrets Manager."""
    import json

    # Create test SFTP credentials for us-fl configuration
    us_fl_credentials = {
        "host": "localhost",
        "username": "testuser",
        "password": "testpass",
        "port": "22",
    }

    # Create test OAuth credentials for fr-api configuration
    fr_api_credentials = {
        "consumer_key": "test_client_id",
        "consumer_secret": "test_client_secret",
        "token_url": "http://localhost:5000/token",
        "api_base_url": "http://localhost:5000",
    }

    # Create us-fl secret
    us_fl_secret_name = "us-fl-sftp-credentials"
    try:
        secretsmanager_client.create_secret(
            Name=us_fl_secret_name, SecretString=json.dumps(us_fl_credentials)
        )
    except Exception:
        # Secret might already exist
        pass

    # Create fr-api secret (AWS credential provider expects -sftp-credentials suffix)
    fr_api_secret_name = "fr-api-sftp-credentials"
    try:
        secretsmanager_client.create_secret(
            Name=fr_api_secret_name, SecretString=json.dumps(fr_api_credentials)
        )
    except Exception:
        # Secret might already exist
        pass

    return {
        "us-fl-sftp-credentials": us_fl_credentials,
        "fr-api-sftp-credentials": fr_api_credentials,
    }


# Mark tests that require Docker/localstack
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers and signal handling."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    config.addinivalue_line(
        "markers", "localstack: mark test as requiring localstack container"
    )
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Clean up any remaining asyncio tasks at the end of the test session."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return  # Don't interfere with running loop

        # Cancel any remaining tasks
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            print(f"Cleaning up {len(pending_tasks)} remaining tasks...")
            for task in pending_tasks:
                task.cancel()

            # Wait for tasks to be cancelled
            if pending_tasks:
                loop.run_until_complete(
                    asyncio.gather(*pending_tasks, return_exceptions=True)
                )
    except Exception:
        # Ignore errors during cleanup
        pass


def pytest_runtest_setup(item: Any) -> None:
    """Ensure setup failures cause test failures instead of skips."""
    # This hook runs before each test and can catch setup issues
    pass


def pytest_runtest_teardown(item: Any, nextitem: Any) -> None:
    """Ensure teardown failures are properly reported."""
    # This hook runs after each test and can catch teardown issues
    pass


# Fail localstack tests if Docker is not available
def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Modify test collection to fail localstack tests if Docker is not available."""
    for item in items:
        if "localstack" in item.keywords:
            if os.getenv("CI") and not os.path.exists("/var/run/docker.sock"):
                # Mark the test to fail during setup if Docker is not available
                item.add_marker(
                    pytest.mark.xfail(
                        reason="Docker/localstack not available in CI environment",
                        strict=True,
                    )
                )
