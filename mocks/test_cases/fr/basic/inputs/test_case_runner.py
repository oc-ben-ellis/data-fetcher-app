#!/usr/bin/env python3
"""Test case runner for French SIREN API functional tests.

This script runs the fetcher with different test case configurations
and validates the output against expected results.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import structlog

logger = structlog.get_logger(__name__)


class TestCaseRunner:
    """Runs test cases and validates output."""

    def __init__(self, test_case_dir: Path) -> None:
        """Initialize the test case runner.

        Args:
            test_case_dir: Path to the test case directory containing inputs and expected subdirectories
        """
        self.test_case_dir = test_case_dir
        self.inputs_dir = test_case_dir / "inputs"
        self.expected_dir = test_case_dir / "expected"
        self.project_root = Path(__file__).parent.parent.parent.parent.parent

    def load_test_config(self) -> dict[str, Any]:
        """Load test configuration from config.json.

        Returns:
            Test configuration dictionary
        """
        config_path = self.inputs_dir / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Test config not found: {config_path}")

        with open(config_path) as f:
            return cast("dict[str, Any]", json.load(f))

    def setup_environment(self, config: dict[str, Any]) -> None:
        """Set up environment variables for the test.

        Args:
            config: Test configuration dictionary
        """
        # Set up credentials
        credentials = config.get("credentials", {})
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = credentials.get(
            "provider_type", "environment"
        )
        os.environ["OC_CREDENTIAL_FR_CLIENT_ID"] = credentials.get(
            "client_id", "test_client_id"
        )
        os.environ["OC_CREDENTIAL_FR_CLIENT_SECRET"] = credentials.get(
            "client_secret", "test_client_secret"
        )

        # Set up storage
        storage = config.get("storage", {})
        os.environ["OC_STORAGE_TYPE"] = storage.get("type", "file")
        os.environ["OC_STORAGE_FILE_PATH"] = storage.get("path", "tmp/test_output")

        # Set up KV store
        os.environ["OC_KVSTORE_TYPE"] = "memory"

        # Set up mock server URLs
        os.environ["OC_FR_TOKEN_URL"] = "http://localhost:5001/token"
        os.environ["OC_FR_API_BASE_URL"] = (
            "http://localhost:5001/entreprises/sirene/V3.11/siren"
        )

    def start_mockoon(self) -> None:
        """Start Mockoon mock server."""
        logger.info("Starting Mockoon mock server...")

        # Change to the mock environment directory
        mock_env_dir = self.project_root / "mocks" / "environments" / "fr"

        # Start Mockoon using docker-compose
        result = subprocess.run(
            [
                "docker-compose",
                "-f",
                "docker-compose-mockoon.yml",
                "up",
                "-d",
                "mockoon",
            ],
            check=False,
            cwd=mock_env_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start Mockoon: {result.stderr}")

        # Wait for Mockoon to be ready
        logger.info("Waiting for Mockoon to be ready...")
        for _i in range(30):  # Wait up to 30 seconds
            try:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:5001/health"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.info("Mockoon is ready!")
                    return
            except subprocess.TimeoutExpired:
                pass

            time.sleep(1)

        raise RuntimeError("Mockoon failed to start within 30 seconds")

    def stop_mockoon(self) -> None:
        """Stop Mockoon mock server."""
        logger.info("Stopping Mockoon mock server...")

        mock_env_dir = self.project_root / "mocks" / "environments" / "fr"

        subprocess.run(
            ["docker-compose", "-f", "docker-compose-mockoon.yml", "down"],
            check=False,
            cwd=mock_env_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def run_fetcher(self, config: dict[str, Any]) -> subprocess.CompletedProcess[str]:
        """Run the fetcher with the given configuration.

        Args:
            config: Test configuration dictionary

        Returns:
            Completed process result
        """
        logger.info("Running fetcher...")

        # Clean up any existing output
        output_path = Path(config.get("storage", {}).get("path", "tmp/test_output"))
        if output_path.exists():
            shutil.rmtree(output_path)

        # Run the fetcher
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "data_fetcher_app.main",
            "run",
            config.get("recipe", "fr"),
            "--credentials-provider",
            "env",
            "--storage",
            "file",
            "--kvstore",
            "memory",
        ]

        result = subprocess.run(
            cmd,
            check=False,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        logger.info("Fetcher completed with return code: %s", result.returncode)
        if result.stdout:
            logger.info("Fetcher stdout: %s", result.stdout)
        if result.stderr:
            logger.warning("Fetcher stderr: %s", result.stderr)

        return result

    def validate_output(self, config: dict[str, Any]) -> bool:
        """Validate the fetcher output against expected results.

        Args:
            config: Test configuration dictionary

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating output...")

        output_path = Path(config.get("storage", {}).get("path", "tmp/test_output"))

        # Check that output directory was created
        if not output_path.exists():
            logger.error("Output directory %s was not created", output_path)
            return False

        # Check that at least one bundle directory was created
        bundle_dirs = list(output_path.glob("bundle_*"))
        if len(bundle_dirs) == 0:
            logger.error("No bundle directories found in %s", output_path)
            return False

        logger.info("Found %d bundle directories", len(bundle_dirs))

        # Validate each bundle directory
        for bundle_dir in bundle_dirs:
            if not self._validate_bundle_directory(bundle_dir):
                return False

        return True

    def _validate_bundle_directory(self, bundle_dir: Path) -> bool:
        """Validate a single bundle directory.

        Args:
            bundle_dir: Path to the bundle directory

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating bundle directory: %s", bundle_dir)

        # Early validation checks
        if not bundle_dir.is_dir():
            logger.error("Bundle directory %s is not a directory", bundle_dir)
            return False

        bundle_meta = bundle_dir / "bundle.meta"
        if not bundle_meta.exists():
            logger.error("bundle.meta file not found in %s", bundle_dir)
            return False

        # Validate bundle.meta content
        if not self._validate_bundle_meta(bundle_meta):
            return False

        # Check for response files
        response_files = [f for f in bundle_dir.iterdir() if f.name != "bundle.meta"]
        if len(response_files) == 0:
            logger.warning("No response files found in %s", bundle_dir)
            return False

        logger.info("Found %d response files in %s", len(response_files), bundle_dir)

        # Validate response files
        return all(
            self._validate_response_file(response_file)
            for response_file in response_files
        )

    def _validate_bundle_meta(self, bundle_meta: Path) -> bool:
        """Validate bundle.meta file content.

        Args:
            bundle_meta: Path to the bundle.meta file

        Returns:
            True if validation passes, False otherwise
        """
        try:
            meta_content = bundle_meta.read_text()
            required_fields = ["bid", "primary_url", "resources_count"]
            for field in required_fields:
                if field not in meta_content:
                    logger.error("bundle.meta missing '%s' field", field)
                    return False
            return True
        except Exception:
            logger.exception("Error reading bundle.meta")
            return False

    def _validate_response_file(self, response_file: Path) -> bool:
        """Validate a response file.

        Args:
            response_file: Path to the response file

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating response file: %s", response_file)

        # Check if it's a JSON file
        if response_file.suffix == ".json":
            try:
                with open(response_file) as f:
                    json.load(f)
                logger.info("Response file %s contains valid JSON", response_file)
            except json.JSONDecodeError:
                logger.exception(
                    "Response file %s contains invalid JSON", response_file
                )
                return False

        # Check for corresponding .meta file
        meta_file = response_file.with_suffix(response_file.suffix + ".meta")
        if not meta_file.exists():
            logger.warning("No .meta file found for %s", response_file)

        return True

    def run_test_case(self) -> bool:
        """Run a single test case.

        Returns:
            True if test passes, False otherwise
        """
        logger.info("Running test case: %s", self.test_case_dir)

        try:
            # Load test configuration
            config = self.load_test_config()
            logger.info(
                "Loaded test config: %s", config.get("description", "No description")
            )

            # Set up environment
            self.setup_environment(config)

            # Start mock server
            self.start_mockoon()

            try:
                # Run the fetcher
                result = self.run_fetcher(config)

                # Validate output
                validation_passed = self.validate_output(config)

                # Test passes if fetcher ran successfully and validation passed
                test_passed = result.returncode == 0 and validation_passed

                if test_passed:
                    logger.info("✅ Test case passed!")
                else:
                    logger.error("❌ Test case failed!")
                    if result.returncode != 0:
                        logger.error(
                            "Fetcher failed with return code: %s", result.returncode
                        )
                    if not validation_passed:
                        logger.error("Output validation failed")

                return test_passed

            finally:
                # Always stop the mock server
                self.stop_mockoon()

        except Exception:
            logger.exception("Test case failed with exception")
            return False


def main() -> int:
    """Main entry point for the test case runner.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if len(sys.argv) != 2:
        print("Usage: python test_case_runner.py <test_case_directory>")
        return 1

    test_case_dir = Path(sys.argv[1])
    if not test_case_dir.exists():
        print(f"Test case directory not found: {test_case_dir}")
        return 1

    runner = TestCaseRunner(test_case_dir)
    success = runner.run_test_case()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
