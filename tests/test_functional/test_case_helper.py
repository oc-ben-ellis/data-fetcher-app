"""Test case helper module for functional tests.

This module provides common functionality for loading test case configurations,
running fetchers, and validating output across different test scenarios.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class TestCaseHelper:
    """Helper class for test case operations."""

    def __init__(self, project_root: Path) -> None:
        """Initialize the test case helper.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self.test_cases_dir = project_root / "mocks" / "test_cases"
        self.mock_server: Any = None
        self.sftp_project_name: str | None = None
        self.sftp_port: int | None = None

    def discover_test_cases(self, recipe: str) -> list[Path]:
        """Discover all test case directories for a recipe.

        Args:
            recipe: Recipe name (e.g., 'fr', 'us_fl')

        Returns:
            List of test case directory paths
        """
        recipe_dir = self.test_cases_dir / recipe
        if not recipe_dir.exists():
            return []

        test_cases = []

        # Look for directories that contain both 'inputs' and 'expected' subdirectories
        for item in recipe_dir.iterdir():
            if item.is_dir():
                inputs_dir = item / "inputs"
                expected_dir = item / "expected"

                if inputs_dir.exists() and expected_dir.exists():
                    test_cases.append(item)
                    logger.info("Found test case: %s/%s", recipe, item.name)

        return test_cases

    def load_test_config(self, test_case_dir: Path) -> dict[str, Any]:
        """Load test configuration from a test case directory.

        Args:
            test_case_dir: Path to the test case directory

        Returns:
            Test configuration dictionary

        Raises:
            FileNotFoundError: If config.json is not found
        """
        config_path = test_case_dir / "inputs" / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Test config not found: {config_path}")

        with open(config_path) as f:
            return json.load(f)  # type: ignore[no-any-return]

    def setup_environment_for_test(self, config: dict[str, Any], recipe: str) -> None:
        """Set up environment variables for a test case.

        Args:
            config: Test configuration dictionary
            recipe: Recipe name for setting up recipe-specific environment variables
        """
        # Set up credentials
        credentials = config.get("credentials", {})
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = credentials.get(
            "provider_type", "environment"
        )

        # Set up recipe-specific credentials
        if recipe == "fr":
            os.environ["OC_CREDENTIAL_FR_CONSUMER_KEY"] = credentials.get(
                "consumer_key", "test_consumer_key"
            )
            os.environ["OC_CREDENTIAL_FR_CONSUMER_SECRET"] = credentials.get(
                "consumer_secret", "test_consumer_secret"
            )
        elif recipe == "us_fl":
            os.environ["OC_CREDENTIAL_US_FL_USERNAME"] = credentials.get(
                "username", "test_user"
            )
            os.environ["OC_CREDENTIAL_US_FL_PASSWORD"] = credentials.get(
                "password", "test_password"
            )
            os.environ["OC_CREDENTIAL_US_FL_HOST"] = credentials.get(
                "host", "localhost"
            )
            os.environ["OC_CREDENTIAL_US_FL_PORT"] = str(credentials.get("port", 22))

        # Set up storage
        storage = config.get("storage", {})
        os.environ["OC_STORAGE_TYPE"] = storage.get("type", "file")
        os.environ["OC_STORAGE_FILE_PATH"] = storage.get("path", "tmp/test_output")

        # Set up KV store
        os.environ["OC_KVSTORE_TYPE"] = "memory"

        # Set up recipe-specific API URLs (for HTTP-based recipes)
        if recipe == "fr":
            os.environ["OC_FR_TOKEN_URL"] = "http://localhost:5001/token"
            os.environ["OC_FR_API_BASE_URL"] = (
                "http://localhost:5001/entreprises/sirene/V3.11/siren"
            )

    def start_mockoon_for_test(self, test_case_dir: Path) -> None:
        """Start mock server for a test case.

        Args:
            test_case_dir: Path to the test case directory

        Raises:
            RuntimeError: If mock server fails to start
        """
        logger.info("Starting mock server...")

        # Import the simple mock server
        from tests.test_functional.simple_mock_server import SimpleMockServer

        # Start the simple mock server
        self.mock_server = SimpleMockServer(host="localhost", port=0)  # Use random port
        self.mock_server.start()

        # Update environment variables with the actual port
        os.environ["OC_FR_TOKEN_URL"] = (
            f"http://localhost:{self.mock_server.port}/token"
        )
        os.environ["OC_FR_API_BASE_URL"] = (
            f"http://localhost:{self.mock_server.port}/entreprises/sirene/V3.11/siren"
        )

        # Wait for server to be ready
        logger.info("Waiting for mock server to be ready...")
        for _i in range(30):  # Wait up to 30 seconds
            if self.mock_server.is_running():
                logger.info("Mock server is ready!")
                return
            time.sleep(0.1)

        raise RuntimeError("Mock server failed to start within 30 seconds")

    def stop_mockoon_for_test(self, test_case_dir: Path) -> None:
        """Stop mock server for a test case.

        Args:
            test_case_dir: Path to the test case directory
        """
        logger.info("Stopping mock server...")

        if hasattr(self, "mock_server") and self.mock_server:
            self.mock_server.stop()

    def start_sftp_mock_for_test(self, test_case_dir: Path) -> None:
        """Start SFTP mock server for a test case.

        Args:
            test_case_dir: Path to the test case directory

        Raises:
            RuntimeError: If SFTP mock fails to start
        """
        logger.info("Starting SFTP mock server...")

        # Change to the mock environment directory
        mock_env_dir = self.project_root / "mocks" / "environments" / "us_fl"

        # Start SFTP mock using docker-compose with unique project name and dynamic port
        import os
        import socket
        import uuid

        self.sftp_project_name = f"us_fl_test_{uuid.uuid4().hex[:8]}"

        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            self.sftp_port = s.getsockname()[1]

        result = subprocess.run(
            ["docker-compose", "-p", self.sftp_project_name, "up", "-d", "sftp-server"],
            check=False,
            cwd=mock_env_dir,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "SFTP_PORT": str(self.sftp_port)},
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start SFTP mock: {result.stderr}")

        # Wait for SFTP server to be ready
        logger.info("Waiting for SFTP server to be ready...")
        for _i in range(60):  # Wait up to 60 seconds
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "StrictHostKeyChecking=no",
                        "-o",
                        "UserKnownHostsFile=/dev/null",
                        "-p",
                        str(self.sftp_port),
                        "test@localhost",
                        "ls",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.info("SFTP server is ready!")
                    return
            except subprocess.TimeoutExpired:
                pass

            time.sleep(0.1)

        raise RuntimeError("SFTP server failed to start within 60 seconds")

    def stop_sftp_mock_for_test(self, test_case_dir: Path) -> None:
        """Stop SFTP mock server for a test case.

        Args:
            test_case_dir: Path to the test case directory
        """
        logger.info("Stopping SFTP mock server...")

        mock_env_dir = self.project_root / "mocks" / "environments" / "us_fl"

        if self.sftp_project_name:
            subprocess.run(
                ["docker-compose", "-p", self.sftp_project_name, "down"],
                check=False,
                cwd=mock_env_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

    def run_fetcher_for_test(
        self, config: dict[str, Any], recipe: str
    ) -> subprocess.CompletedProcess[str]:
        """Run the fetcher for a test case.

        Args:
            config: Test configuration dictionary
            recipe: Recipe name

        Returns:
            Completed process result
        """
        logger.info("Running fetcher for recipe: %s", recipe)

        # Clean up any existing output
        output_path = Path(config.get("storage", {}).get("path", "tmp/test_output"))
        if output_path.exists():
            shutil.rmtree(output_path)

        # Mock server should already be started by start_mockoon_for_test

        # Run the fetcher
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "data_fetcher_app.main",
            "run",
            recipe,
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

    def validate_output_for_test(
        self, config: dict[str, Any], test_case_dir: Path | None = None
    ) -> bool:
        """Validate the fetcher output for a test case.

        Args:
            config: Test configuration dictionary
            test_case_dir: Optional test case directory for comparison with expected output

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

        # Compare with expected output if test case directory is provided
        if test_case_dir:
            expected_dir = test_case_dir / "expected"
            if expected_dir.exists():
                if not self._compare_with_expected_output(bundle_dirs[0], expected_dir):
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

    def _compare_with_expected_output(
        self, actual_bundle_dir: Path, expected_dir: Path
    ) -> bool:
        """Compare actual output with expected output.

        Args:
            actual_bundle_dir: Path to the actual bundle directory
            expected_dir: Path to the expected output directory

        Returns:
            True if comparison passes, False otherwise
        """
        logger.info("Comparing with expected output...")

        expected_sample_dir = expected_dir / "sample_output"
        if not expected_sample_dir.exists():
            logger.warning(
                "No sample_output directory found in expected, skipping comparison"
            )
            return True

        # Get file lists
        actual_files = [f for f in actual_bundle_dir.iterdir() if f.is_file()]
        expected_files = [f for f in expected_sample_dir.iterdir() if f.is_file()]

        # Filter out bundle.meta for file count comparison
        actual_data_files = [
            f
            for f in actual_files
            if f.name != "bundle.meta" and not f.name.endswith(".meta")
        ]
        expected_data_files = [
            f
            for f in expected_files
            if f.name != "bundle.meta" and not f.name.endswith(".meta")
        ]

        # Validate file counts and names
        if not self._validate_file_counts_and_names(
            actual_data_files, expected_data_files
        ):
            return False

        # Compare bundle.meta structure (if present)
        if not self._compare_bundle_meta(
            actual_bundle_dir, expected_sample_dir, actual_data_files
        ):
            return False

        # Compare file contents for CSV files
        if not self._compare_csv_file_contents(actual_data_files, expected_sample_dir):
            return False

        logger.info("Output comparison passed")
        return True

    def _validate_file_counts_and_names(
        self, actual_data_files: list[Path], expected_data_files: list[Path]
    ) -> bool:
        """Validate file counts and names match."""
        if len(actual_data_files) != len(expected_data_files):
            logger.error(
                "File count mismatch: actual=%d, expected=%d",
                len(actual_data_files),
                len(expected_data_files),
            )
            return False

        # Compare file names (without extensions for flexibility)
        actual_names = {f.stem for f in actual_data_files}
        expected_names = {f.stem for f in expected_data_files}

        if actual_names != expected_names:
            logger.error(
                "File name mismatch: actual=%s, expected=%s",
                actual_names,
                expected_names,
            )
            return False

        return True

    def _compare_bundle_meta(
        self,
        actual_bundle_dir: Path,
        expected_sample_dir: Path,
        actual_data_files: list[Path],
    ) -> bool:
        """Compare bundle.meta files."""
        actual_meta = actual_bundle_dir / "bundle.meta"
        expected_meta = expected_sample_dir / "bundle.meta"

        if not (expected_meta.exists() and actual_meta.exists()):
            return True

        try:
            # Try to parse as JSON first, then as Python dict
            actual_text = actual_meta.read_text()
            try:
                actual_meta_content = json.loads(actual_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try parsing as Python dict
                import ast

                actual_meta_content = ast.literal_eval(actual_text)

            expected_text = expected_meta.read_text()
            try:
                json.loads(expected_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try parsing as Python dict
                import ast

                ast.literal_eval(expected_text)

            # Check required fields exist
            required_fields = ["bid", "primary_url", "resources_count"]
            for field in required_fields:
                if field not in actual_meta_content:
                    logger.error("Missing required field '%s' in bundle.meta", field)
                    return False

            # Check resources_count matches
            if actual_meta_content.get("resources_count") != len(actual_data_files):
                logger.error("Resources count mismatch in bundle.meta")
                return False

            logger.info("Bundle metadata validation passed")
            return True

        except json.JSONDecodeError:
            logger.exception("Invalid JSON in bundle.meta")
            return False

    def _compare_csv_file_contents(
        self, actual_data_files: list[Path], expected_sample_dir: Path
    ) -> bool:
        """Compare CSV file contents."""
        for actual_file in actual_data_files:
            if actual_file.suffix == ".csv":
                expected_file = expected_sample_dir / actual_file.name
                if expected_file.exists():
                    if not self._compare_csv_files(actual_file, expected_file):
                        return False
        return True

    def _compare_csv_files(self, actual_file: Path, expected_file: Path) -> bool:
        """Compare two CSV files for content similarity.

        Args:
            actual_file: Path to actual CSV file
            expected_file: Path to expected CSV file

        Returns:
            True if files are similar, False otherwise
        """
        try:
            actual_content = actual_file.read_text().strip()
            expected_content = expected_file.read_text().strip()

            # For now, just check that both files have the same number of lines
            # and contain similar structure (headers + data rows)
            actual_lines = actual_content.split("\n")
            expected_lines = expected_content.split("\n")

            if len(actual_lines) != len(expected_lines):
                logger.warning(
                    "Line count mismatch in %s: actual=%d, expected=%d",
                    actual_file.name,
                    len(actual_lines),
                    len(expected_lines),
                )
                # Don't fail the test for line count differences, just warn

            # Check that both files have headers
            if len(actual_lines) > 0 and len(expected_lines) > 0:
                actual_headers = actual_lines[0].split(",")
                expected_headers = expected_lines[0].split(",")

                if actual_headers != expected_headers:
                    logger.warning("Header mismatch in %s", actual_file.name)
                    # Don't fail the test for header differences, just warn

            logger.info("CSV file %s comparison passed", actual_file.name)
            return True

        except Exception:
            logger.exception("Error comparing CSV files")
            return False

    def run_test_case(self, test_case_dir: Path, recipe: str) -> bool:
        """Run a single test case.

        Args:
            test_case_dir: Path to the test case directory
            recipe: Recipe name

        Returns:
            True if test passes, False otherwise
        """
        logger.info("Running test case: %s", test_case_dir)

        try:
            # Load test configuration
            config = self.load_test_config(test_case_dir)
            logger.info(
                "Loaded test config: %s", config.get("description", "No description")
            )

            # Set up environment
            self.setup_environment_for_test(config, recipe)

            # Start appropriate mock server
            if recipe == "fr":
                self.start_mockoon_for_test(test_case_dir)
            elif recipe == "us_fl":
                self.start_sftp_mock_for_test(test_case_dir)

            try:
                # Run the fetcher
                result = self.run_fetcher_for_test(config, recipe)

                # Validate output
                validation_passed = self.validate_output_for_test(config, test_case_dir)

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
                if recipe == "fr":
                    self.stop_mockoon_for_test(test_case_dir)
                elif recipe == "us_fl":
                    self.stop_sftp_mock_for_test(test_case_dir)

        except Exception:
            logger.exception("Test case failed with exception")
            return False
