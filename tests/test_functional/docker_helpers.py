"""Helper functions for running functional tests with mock environments.

This module provides utilities for executing the data fetcher application
using the mock environment docker-compose setups, following the documented
steps exactly as a user would.
"""

import asyncio
import os
import subprocess
from pathlib import Path

import pytest


class MockEnvironmentRunner:
    """Helper class for running tests with mock environments."""

    def __init__(self, environment_name: str, project_root: Path):
        """Initialize the mock environment runner.

        Args:
            environment_name: Name of the mock environment (us_fl or fr).
            project_root: Path to the project root directory.
        """
        self.environment_name = environment_name
        self.project_root = project_root
        self.mock_env_dir = project_root / "mocks" / "environments" / environment_name

    async def start_environment(
        self, timeout: int = 120
    ) -> subprocess.CompletedProcess[str]:
        """Start the mock environment using docker-compose.

        Args:
            timeout: Timeout in seconds for the command.

        Returns:
            CompletedProcess result from the docker-compose command.

        Raises:
            subprocess.TimeoutExpired: If the command times out.
            subprocess.CalledProcessError: If the command fails.
        """
        # Change to the mock environment directory
        original_cwd = Path.cwd()
        try:
            os.chdir(self.mock_env_dir)

            # Run docker-compose up -d
            result = await asyncio.create_subprocess_exec(
                "docker-compose",
                "up",
                "-d",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return subprocess.CompletedProcess[str](
                args=["docker-compose", "up", "-d"],
                returncode=result.returncode or 0,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
            )

        finally:
            os.chdir(original_cwd)

    async def stop_environment(
        self, timeout: int = 60
    ) -> subprocess.CompletedProcess[str]:
        """Stop the mock environment using docker-compose.

        Args:
            timeout: Timeout in seconds for the command.

        Returns:
            CompletedProcess result from the docker-compose command.
        """
        # Change to the mock environment directory
        original_cwd = Path.cwd()
        try:
            os.chdir(self.mock_env_dir)

            # Run docker-compose down
            result = await asyncio.create_subprocess_exec(
                "docker-compose",
                "down",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return subprocess.CompletedProcess[str](
                args=["docker-compose", "down"],
                returncode=result.returncode or 0,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
            )

        finally:
            os.chdir(original_cwd)

    async def setup_mock_data(
        self, timeout: int = 60
    ) -> subprocess.CompletedProcess[str]:
        """Run the setup script for mock data.

        Args:
            timeout: Timeout in seconds for the command.

        Returns:
            CompletedProcess result from the setup script.
        """
        # Change to the mock environment directory
        original_cwd = Path.cwd()
        try:
            os.chdir(self.mock_env_dir)

            # Run the setup script
            result = await asyncio.create_subprocess_exec(
                "./setup-mock-data.sh",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return subprocess.CompletedProcess[str](
                args=["./setup-mock-data.sh"],
                returncode=result.returncode or 0,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
            )

        finally:
            os.chdir(original_cwd)

    async def run_fetcher(
        self,
        config_name: str,
        environment_vars: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess[str]:
        """Run the fetcher from the project root.

        Args:
            config_name: The configuration name to run.
            environment_vars: Additional environment variables to set.
            timeout: Timeout in seconds for the command.

        Returns:
            CompletedProcess result from the fetcher command.
        """
        # Prepare environment variables
        env = os.environ.copy()
        if environment_vars:
            env.update(environment_vars)

        # Run the fetcher
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "data_fetcher_app.main",
            "run",
            config_name,
            "--credentials-provider",
            "env",
        ]

        result = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.project_root,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout)

        return subprocess.CompletedProcess[str](
            args=cmd,
            returncode=result.returncode or 0,
            stdout=stdout.decode("utf-8"),
            stderr=stderr.decode("utf-8"),
        )

    def get_environment_status(self) -> subprocess.CompletedProcess[str]:
        """Get the status of the mock environment containers.

        Returns:
            CompletedProcess result from docker-compose ps.
        """
        # Change to the mock environment directory
        original_cwd = Path.cwd()
        try:
            os.chdir(self.mock_env_dir)

            return subprocess.run(
                ["docker-compose", "ps"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        finally:
            os.chdir(original_cwd)


@pytest.fixture
def us_fl_runner() -> MockEnvironmentRunner:
    """Fixture providing a MockEnvironmentRunner for US_FL environment.

    Returns:
        MockEnvironmentRunner instance configured for US_FL environment.
    """
    project_root = Path(__file__).parent.parent.parent
    return MockEnvironmentRunner("us_fl", project_root)


@pytest.fixture
def fr_runner() -> MockEnvironmentRunner:
    """Fixture providing a MockEnvironmentRunner for FR environment.

    Returns:
        MockEnvironmentRunner instance configured for FR environment.
    """
    project_root = Path(__file__).parent.parent.parent
    return MockEnvironmentRunner("fr", project_root)


@pytest.fixture
def test_environment_vars() -> dict[str, str]:
    """Fixture providing common test environment variables.

    Returns:
        Dictionary of environment variables for testing.
    """
    return {
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "us-east-1",
    }
