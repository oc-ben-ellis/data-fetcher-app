"""Helper functions for running functional tests with docker-compose app-runner.

This module provides utilities for executing the data fetcher application
via docker-compose instead of calling the code directly, while maintaining
test containers for test-specific dependencies.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


class DockerComposeRunner:
    """Helper class for running the app via docker-compose."""

    def __init__(self, project_root: Path):
        """Initialize the docker-compose runner.

        Args:
            project_root: Path to the project root directory.
        """
        self.project_root = project_root
        self.docker_compose_file = project_root / "docker-compose.yml"

    async def run_fetcher(
        self,
        config_name: str,
        environment_vars: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess[str]:
        """Run the fetcher via docker-compose app-runner.

        Args:
            config_name: The configuration name to run.
            environment_vars: Additional environment variables to set.
            timeout: Timeout in seconds for the command.

        Returns:
            CompletedProcess result from the docker-compose command.

        Raises:
            subprocess.TimeoutExpired: If the command times out.
            subprocess.CalledProcessError: If the command fails.
        """
        # Prepare environment variables
        env = os.environ.copy()
        if environment_vars:
            env.update(environment_vars)

        # Set the configuration ID
        env["OC_CONFIG_ID"] = config_name

        # Build the docker-compose command
        cmd = [
            "docker-compose",
            "-f",
            str(self.docker_compose_file),
            "run",
            "--rm",
            "app-runner",
            "poetry",
            "run",
            "python",
            "-m",
            "data_fetcher.main",
            config_name,
        ]

        print(f"Running command: {' '.join(cmd)}")
        print(f"Environment: {dict(env)}")

        # Run the command
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return subprocess.CompletedProcess[str](
                args=cmd,
                returncode=result.returncode or 0,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
            )

        except TimeoutError:
            # Kill the process if it times out
            if result.returncode is None:
                result.kill()
                await result.wait()
            raise subprocess.TimeoutExpired(cmd, timeout) from None

    def get_container_network_info(self) -> dict[str, Any]:
        """Get information about the docker-compose network.

        Returns:
            Dictionary containing network information.
        """
        try:
            # Get the network name from docker-compose
            result = subprocess.run(
                ["docker-compose", "-f", str(self.docker_compose_file), "ps", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            container_ids = result.stdout.strip().split("\n")
            network_info = {}

            for container_id in container_ids:
                if container_id:
                    # Get network info for each container
                    network_result = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            container_id,
                            "--format",
                            "{{json .NetworkSettings.Networks}}",
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                    networks = json.loads(network_result.stdout)
                    network_info[container_id] = networks

            return network_info

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Warning: Could not get network info: {e}")
            return {}


@pytest.fixture
def docker_compose_runner() -> DockerComposeRunner:
    """Fixture providing a DockerComposeRunner instance.

    Returns:
        DockerComposeRunner instance configured for the project.
    """
    project_root = Path(__file__).parent.parent.parent
    return DockerComposeRunner(project_root)


@pytest.fixture
def test_environment_vars() -> dict[str, str]:
    """Fixture providing common test environment variables.

    Returns:
        Dictionary of environment variables for testing.
    """
    return {
        "OC_CREDENTIAL_PROVIDER_TYPE": "aws",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "us-east-1",
    }
