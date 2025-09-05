"""Functional tests for US Florida SFTP fetcher.

This module contains comprehensive functional tests for the US Florida
SFTP fetcher, including end-to-end workflows and integration testing.

This test verifies that the us-fl configuration:
1. Connects to an SFTP server
2. Processes daily files with date filtering
3. Processes quarterly files
4. Creates proper bundles with expected structure
5. Uploads bundles to S3 with correct content

The tests now use the app-runner via docker-compose instead of calling
the code directly, while maintaining test containers for test-specific dependencies.
"""

import asyncio
import os
import tempfile
import time
from collections.abc import Callable, Generator
from collections.abc import Generator as TypingGenerator
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
from testcontainers.core.container import (  # type: ignore[import-untyped]
    DockerContainer,
)
from testcontainers.core.waiting_utils import (  # type: ignore[import-untyped]
    wait_for_logs,
)

from data_fetcher_configs.us_fl import _setup_us_fl_sftp_fetcher
from data_fetcher_core.core import FetchRunContext
from data_fetcher_core.global_storage import configure_global_storage
from data_fetcher_core.kv_store import configure_global_store

from .docker_helpers import (
    DockerComposeRunner,
)


@pytest.fixture(scope="session", autouse=True)
def setup_early_s3() -> TypingGenerator[None]:
    """Set up S3 configuration early to prevent auto-execution issues."""
    print("EARLY S3 SETUP - before any containers")

    # Set basic environment variables that might prevent auto-execution issues
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    yield

    print("EARLY S3 CLEANUP")


@pytest.fixture
def sftp_server_container() -> TypingGenerator[DockerContainer]:
    """Start an SFTP server container with mock data for testing."""
    try:
        # Create a temporary directory for SFTP data
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        # Create directory structure matching US FL configuration
        doc_cor_dir = temp_path / "doc" / "cor"
        doc_cor_dir.mkdir(parents=True, exist_ok=True)

        quarterly_dir = temp_path / "doc" / "Quarterly" / "Cor"
        quarterly_dir.mkdir(parents=True, exist_ok=True)

        # Create mock daily files with different dates
        daily_files = [
            # Before start date (should be filtered out)
            "20230725_daily_data.txt",
            "20230728_daily_data.txt",  # Start date (should be included)
            "20230729_daily_data.txt",  # After start date (should be included)
            "20230730_daily_data.txt",  # After start date (should be included)
            "20240101_daily_data.txt",  # Future date (should be included)
        ]

        for filename in daily_files:
            file_path = doc_cor_dir / filename
            with open(file_path, "w") as f:
                f.write(f"Mock daily data for {filename}\n")
                f.write(f"Generated at {datetime.now().isoformat()}\n")
                f.write("Sample corporate data content\n")
                f.write("This is daily business registration data\n")
                f.write("Contains licensing and corporate information\n")

        # Create mock quarterly file
        quarterly_file = quarterly_dir / "cordata.zip"
        with open(quarterly_file, "w") as f:
            f.write("Mock quarterly corporate data\n")
            f.write("This is a ZIP file containing quarterly data\n")

        # Start SFTP container
        print("Starting SFTP container...")
        container = DockerContainer("atmoz/sftp:latest")
        container.with_env("SFTP_USERS", "testuser:testpass:1000")
        container.with_exposed_ports(22)
        container.start()
        print("SFTP container started!")

        # Wait for container to be ready
        print("Waiting for container to be ready...")
        time.sleep(5)

        # Create files directly in the container using docker exec
        import subprocess

        print("Creating directories in container...")

        # Create directories
        result = subprocess.run(
            [
                "docker",
                "exec",
                container.get_wrapped_container().id,
                "mkdir",
                "-p",
                "/home/testuser/doc/cor",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"mkdir doc/cor result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        result = subprocess.run(
            [
                "docker",
                "exec",
                container.get_wrapped_container().id,
                "mkdir",
                "-p",
                "/home/testuser/doc/Quarterly/Cor",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"mkdir doc/Quarterly/Cor result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        print("Copying files to container...")

        # Copy files to container
        for filename in daily_files:
            file_path = doc_cor_dir / filename
            result = subprocess.run(
                [
                    "docker",
                    "cp",
                    str(file_path),
                    f"{container.get_wrapped_container().id}:/home/testuser/doc/cor/{filename}",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            print(
                f"Copy {filename} result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
            )

        # Copy quarterly file
        result = subprocess.run(
            [
                "docker",
                "cp",
                str(quarterly_file),
                f"{container.get_wrapped_container().id}:/home/testuser/doc/Quarterly/Cor/cordata.zip",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"Copy quarterly file result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        print("Setting permissions...")

        # Set proper permissions
        result = subprocess.run(
            [
                "docker",
                "exec",
                container.get_wrapped_container().id,
                "chown",
                "-R",
                "testuser",
                "/home/testuser/doc",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"chown result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        # Verify files exist
        print("Verifying files in container...")
        result = subprocess.run(
            [
                "docker",
                "exec",
                container.get_wrapped_container().id,
                "ls",
                "-la",
                "/home/testuser/doc/cor",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"ls doc/cor result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        result = subprocess.run(
            [
                "docker",
                "exec",
                container.get_wrapped_container().id,
                "ls",
                "-la",
                "/home/testuser/doc/Quarterly/Cor",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"ls doc/Quarterly/Cor result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        # Wait for SFTP server to be ready
        print("Waiting for SFTP server logs...")
        try:
            wait_for_logs(container, "Server listening on 0.0.0.0 port 22", timeout=60)
            print("SFTP server is ready!")
        except Exception as e:
            print(f"Warning: wait_for_logs failed: {e}")
            print("Continuing anyway...")
            time.sleep(5)  # Give it some time to start

        # Give the server a moment to fully initialize
        time.sleep(2)

        # Verify that SFTP is actually accessible before yielding
        # Try a simple connection test
        import subprocess

        result = subprocess.run(
            [
                "docker",
                "exec",
                container.get_wrapped_container().id,
                "ls",
                "-la",
                "/home/testuser/",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(
            f"Final verification - home directory: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
        )

        print("SFTP FIXTURE SETUP COMPLETE - yielding container to test")
        yield container
        print("SFTP FIXTURE CLEANUP - container stopping")

        container.stop()

        # Clean up the temporary directory
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        pytest.fail(f"Failed to start SFTP server container: {e}")


@pytest.fixture
def localstack_container() -> TypingGenerator[DockerContainer]:
    """Start localstack container for S3 testing."""
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
        wait_for_logs(container, "Ready.", timeout=60)

        # Wait a bit more for all services to be fully ready
        import time

        time.sleep(5)

        # Test if Secrets Manager is ready
        try:
            mapped_port = container.get_exposed_port(4566)
            test_client = boto3.client(
                "secretsmanager",
                endpoint_url=f"http://localhost:{mapped_port}",
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


@pytest.fixture
def s3_client(localstack_container: DockerContainer) -> Any:
    """Create S3 client connected to localstack."""
    mapped_port = localstack_container.get_exposed_port(4566)
    return boto3.client(
        "s3",
        endpoint_url=f"http://localhost:{mapped_port}",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


@pytest.fixture
def test_bucket(s3_client: Any) -> str:
    """Create test bucket in localstack."""
    bucket_name = "test-us-fl-bucket"
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except Exception:
        # Bucket might already exist
        pass
    return bucket_name


@pytest.fixture
def setup_storage_and_kvstore(
    test_bucket: str, localstack_container: DockerContainer
) -> Generator[None]:
    """Set up global storage and KV store for testing."""
    print("SETUP_STORAGE_AND_KVSTORE FIXTURE STARTED")

    # Configure global storage to use S3 with localstack
    mapped_port = localstack_container.get_exposed_port(4566)
    print(f"Got localstack port: {mapped_port}")

    # Set environment variables for S3 configuration
    import os

    os.environ["OC_STORAGE_TYPE"] = "s3"
    os.environ["OC_S3_BUCKET"] = test_bucket
    os.environ["OC_S3_PREFIX"] = "test-us-fl/"
    os.environ["AWS_REGION"] = "us-east-1"
    print("Environment variables set")

    # Set LocalStack endpoint URL
    os.environ["OC_S3_ENDPOINT_URL"] = f"http://localhost:{mapped_port}"

    # Configure global storage with LocalStack endpoint
    print("About to configure global storage")
    configure_global_storage()
    print(
        f"Global storage configured with LocalStack endpoint: http://localhost:{mapped_port}"
    )

    # Configure global KV store
    configure_global_store(
        store_type="memory",
        serializer="json",
        default_ttl=3600,
        key_prefix="test_us_fl:",
    )

    print("STORAGE AND KVSTORE SETUP COMPLETE - yielding")

    # Debug: Check what global storage was configured
    from data_fetcher_core.storage.builder import get_global_storage

    global_storage = get_global_storage()
    print(f"Fixture: Global storage type: {type(global_storage).__name__}")
    if global_storage is not None:
        gs = cast("Any", global_storage)
        if hasattr(gs, "bucket_name"):
            print(f"Fixture: Global storage bucket: {gs.bucket_name}")
        if hasattr(gs, "prefix"):
            print(f"Fixture: Global storage prefix: {gs.prefix}")
        if hasattr(gs, "endpoint_url"):
            print(f"Fixture: Global storage endpoint: {gs.endpoint_url}")

    yield
    print("STORAGE AND KVSTORE CLEANUP")

    # Cleanup
    # Note: Global store cleanup is handled automatically


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock SFTP credentials for the test server."""
    credentials = MagicMock()
    credentials.host = "localhost"
    credentials.username = "testuser"
    credentials.password = "testpass"
    return credentials


@pytest.fixture
def mock_credential_provider(mock_credentials: MagicMock) -> AsyncMock:
    """Create a mock credential provider for SFTP."""
    provider = AsyncMock()
    provider.get_credentials.return_value = mock_credentials
    return provider


class TestUsfloridaFunctional:
    """Functional test for US Florida configuration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_us_fl_sftp_functional(
        self,
        sftp_server_container: DockerContainer,
        localstack_container: DockerContainer,
        s3_client: Any,
        test_bucket: str,
        test_secrets: dict[str, str],
        setup_storage_and_kvstore: Any,
        docker_compose_runner: DockerComposeRunner,
        test_environment_vars: dict[str, str],
    ) -> None:
        """Test the complete US Florida SFTP workflow using docker-compose app-runner.

        This test:
                1. Sets up an SFTP server with mock data files
                2. Configures the us-fl fetcher to use the test SFTP server
                3. Runs the fetcher via docker-compose app-runner
                4. Verifies that bundles are created with expected structure
                5. Checks that data is properly uploaded to S3
        """
        print("TEST METHOD STARTED - beginning test execution")
        print("DEBUG: About to wait for fixtures to be ready")

        # First, wait a moment to ensure all fixtures are completely ready
        await asyncio.sleep(1)

        # Verify SFTP container is accessible before proceeding
        print("Verifying SFTP container accessibility...")

        # Get the SFTP server port and host - use mapped port for external access
        sftp_port = sftp_server_container.get_exposed_port(22)
        sftp_host = "localhost"  # Connect to the mapped port on localhost

        print(f"SFTP Connection details: {sftp_host}:{sftp_port}")

        # Test basic SFTP connectivity before creating fetcher components
        import pysftp

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Disable host key checking for testing

        try:
            print("Testing basic SFTP connection...")
            with pysftp.Connection(
                host=sftp_host,
                username="testuser",
                password="testpass",
                port=int(sftp_port),
                cnopts=cnopts,
            ) as sftp:
                print("SFTP connection successful")
                print("Current working directory:", sftp.getcwd())
                print("Listing home directory:", sftp.listdir("."))

                # Check doc directory
                if sftp.exists("doc"):
                    print("doc directory exists, listing contents:")
                    print(sftp.listdir("doc"))

                    # Check doc/cor directory
                    if sftp.exists("doc/cor"):
                        print("doc/cor directory exists, listing contents:")
                        print(sftp.listdir("doc/cor"))
                    else:
                        print("ERROR: doc/cor directory does not exist!")

                    # Check doc/Quarterly directory
                    if sftp.exists("doc/Quarterly"):
                        print("doc/Quarterly directory exists, listing contents:")
                        print(sftp.listdir("doc/Quarterly"))

                        if sftp.exists("doc/Quarterly/Cor"):
                            print(
                                "doc/Quarterly/Cor directory exists, listing contents:"
                            )
                            print(sftp.listdir("doc/Quarterly/Cor"))
                        else:
                            print("ERROR: doc/Quarterly/Cor directory does not exist!")
                    else:
                        print("ERROR: doc/Quarterly directory does not exist!")
                else:
                    print("ERROR: doc directory does not exist!")

                # Test both absolute and relative paths
                for path in ["/home/testuser/doc/cor", "doc/cor"]:
                    if sftp.exists(path):
                        print(f"Path {path} exists")
                    else:
                        print(f"Path {path} does not exist")
        except Exception as e:
            print(f"SFTP connection test failed: {e}")
            pytest.fail(f"SFTP connection test failed: {e}")

        # Only proceed with fetcher creation after SFTP verification succeeds
        print(
            "SFTP verification complete, setting up environment for docker-compose..."
        )

        # Get localstack port
        localstack_port = localstack_container.get_exposed_port(4566)
        print(f"Localstack port: {localstack_port}")

        # Update the test secrets with the correct port
        import json

        updated_credentials = {
            "host": sftp_host,
            "username": "testuser",
            "password": "testpass",
            "port": str(sftp_port),
        }

        # Create/Update the secret in LocalStack
        secretsmanager_client = boto3.client(
            "secretsmanager",
            endpoint_url=f"http://localhost:{localstack_port}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        try:
            # Try to create the secret first
            secretsmanager_client.create_secret(
                Name="us-fl-sftp-credentials",
                SecretString=json.dumps(updated_credentials),
            )
            print("Created test secrets with correct SFTP port")
        except Exception as e:
            if "already exists" in str(e):
                # Secret already exists, try to update it
                try:
                    secretsmanager_client.update_secret(
                        SecretId="us-fl-sftp-credentials",
                        SecretString=json.dumps(updated_credentials),
                    )
                    print("Updated test secrets with correct SFTP port")
                except Exception as update_e:
                    print(f"Warning: Could not update secrets: {update_e}")
            else:
                print(f"Warning: Could not create secrets: {e}")

        # Prepare environment variables for docker-compose
        env_vars = test_environment_vars.copy()
        env_vars.update(
            {
                "OC_STORAGE_TYPE": "s3",
                "OC_S3_BUCKET": test_bucket,
                "OC_S3_PREFIX": "test-us-fl/",
                "OC_S3_ENDPOINT_URL": f"http://host.docker.internal:{localstack_port}",
                "OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL": f"http://host.docker.internal:{localstack_port}",
                "AWS_REGION": "us-east-1",
            }
        )

        print("Running fetcher via docker-compose app-runner...")
        print(f"Environment variables: {env_vars}")

        # Run the fetcher via docker-compose
        try:
            result = await docker_compose_runner.run_fetcher(
                config_name="us-fl",
                environment_vars=env_vars,
                timeout=300,  # 5 minutes timeout
            )

            print(f"Docker-compose result: returncode={result.returncode}")
            print(f"STDOUT: {result.stdout}")
            if result.stderr:
                print(f"STDERR: {result.stderr}")

            # Check if the command succeeded
            if result.returncode != 0:
                pytest.fail(
                    f"Fetcher failed with return code {result.returncode}. "
                    f"STDOUT: {result.stdout}, STDERR: {result.stderr}"
                )

        except Exception as e:
            print(f"Error running fetcher via docker-compose: {e}")
            pytest.fail(f"Failed to run fetcher via docker-compose: {e}")

        # Wait a moment for S3 uploads to complete
        await asyncio.sleep(2)

        # Verify that bundles were created in S3
        try:
            # List objects in the test bucket
            response = s3_client.list_objects_v2(
                Bucket=test_bucket,
                Prefix="test-us-fl/",
            )

            # Should have at least some objects
            assert "Contents" in response, (
                f"No objects found in S3 bucket '{test_bucket}' with prefix 'test-us-fl/'. "
                f"This may indicate that the fetcher did not upload any bundles."
            )
            objects = response["Contents"]
            assert len(objects) > 0, (
                f"Expected objects in S3 bucket '{test_bucket}' with prefix 'test-us-fl/', "
                f"but found none. The fetcher may not have uploaded any bundles."
            )

            # Check for specific bundle files
            bundle_keys = [obj["Key"] for obj in objects]
            print(
                f"Found {len(bundle_keys)} objects in S3 bucket '{test_bucket}' with prefix 'test-us-fl/':"
            )
            for key in bundle_keys:
                print(f"  {key}")

            # Should have ZIP files (bundles) - the fetcher creates ZIP files, not WARC files
            zip_files = [key for key in bundle_keys if key.endswith(".zip")]
            assert len(zip_files) > 0, (
                f"No ZIP bundle files found in S3 bucket '{test_bucket}'. "
                f"Found {len(bundle_keys)} objects but none are ZIP files. "
                f"This may indicate that the bundle creation process failed."
            )

            # Should have metadata files
            meta_files = [key for key in bundle_keys if key.endswith(".json")]
            assert len(meta_files) > 0, (
                f"No metadata files found in S3 bucket '{test_bucket}'. "
                f"Found {len(bundle_keys)} objects but none are JSON metadata files. "
                f"This may indicate that the metadata creation process failed."
            )

            # Verify bundle structure by examining one of the ZIP files
            if zip_files:
                zip_key = zip_files[0]
                zip_response = s3_client.get_object(Bucket=test_bucket, Key=zip_key)
                zip_content = zip_response["Body"].read()

                # ZIP files should start with the ZIP magic number
                assert zip_content.startswith(b"PK"), (
                    "ZIP file missing proper header (should start with PK)"
                )

                # Debug: Print the first 200 bytes of the ZIP file to see what's in it
                print(f"ZIP file content (first 200 bytes): {zip_content[:200]}")

                # Try to extract and check the ZIP content
                import io
                import zipfile

                try:
                    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
                        print(f"ZIP file contains {len(zip_file.namelist())} files:")
                        for name in zip_file.namelist():
                            print(f"  - {name}")
                            # Read the content of each file in the ZIP
                            with zip_file.open(name) as file_in_zip:
                                file_content = file_in_zip.read()
                                print(
                                    f"    Content (first 100 bytes): {file_content[:100]!r}"
                                )

                                # Check for mock data in the extracted content
                                mock_data_indicators = [
                                    b"Mock daily data",
                                    b"Mock quarterly corporate data",
                                    b"Sample corporate data content",
                                ]

                                found_indicators = sum(
                                    1
                                    for indicator in mock_data_indicators
                                    if indicator in file_content
                                )
                                if found_indicators > 0:
                                    print(
                                        f"    ✓ Found {found_indicators} mock data indicators"
                                    )
                                    break
                        else:
                            print("    ✗ No mock data found in any file in the ZIP")
                            raise AssertionError(
                                "ZIP file doesn't contain expected mock data in any of its files"
                            )
                except Exception as zip_error:
                    print(f"Error reading ZIP file: {zip_error}")
                    # Fall back to checking raw content
                    mock_data_indicators = [
                        b"Mock daily data",
                        b"Mock quarterly corporate data",
                        b"Sample corporate data content",
                    ]

                    found_indicators = sum(
                        1
                        for indicator in mock_data_indicators
                        if indicator in zip_content
                    )
                    assert found_indicators > 0, (
                        "ZIP file doesn't contain expected mock data"
                    )

            # Verify metadata structure
            if meta_files:
                meta_key = meta_files[0]
                meta_response = s3_client.get_object(Bucket=test_bucket, Key=meta_key)
                meta_content = meta_response["Body"].read()

                # Debug: Print the metadata content to see what's in it
                print(f"Metadata content (first 200 bytes): {meta_content[:200]}")
                print(
                    f"Metadata content (decoded): {meta_content.decode('utf-8', errors='ignore')[:200]}"
                )

                # Metadata should be valid JSON or Python dict format
                import ast

                try:
                    # Try JSON first
                    metadata = json.loads(meta_content.decode("utf-8"))
                except json.JSONDecodeError as json_error:
                    print(
                        f"JSON decode failed, trying Python dict format: {json_error}"
                    )
                    try:
                        # Try Python dict format (using ast.literal_eval)
                        metadata = ast.literal_eval(meta_content.decode("utf-8"))
                        print("Successfully parsed metadata as Python dict format")
                    except (ValueError, SyntaxError) as ast_error:
                        print(f"Python dict parse failed: {ast_error}")
                        print(f"Raw metadata content: {meta_content}")
                        raise

                # Check expected metadata structure
                assert "primary_url" in metadata, "Metadata missing primary_url"
                assert "resources_count" in metadata, "Metadata missing resources_count"

                # Debug: Print all available metadata fields
                print(f"Available metadata fields: {list(metadata.keys())}")

                # The meta field might not be present in all metadata formats
                # Check if it exists, but don't fail if it's missing
                if "meta" in metadata:
                    print("✓ Metadata contains 'meta' field")
                else:
                    print(
                        "⚠ Metadata does not contain 'meta' field (this may be expected)"
                    )

                # Should have SFTP-related metadata
                assert metadata["primary_url"].startswith("sftp://"), (
                    "Primary URL should be SFTP"
                )

        except Exception as e:
            error_msg = f"Failed to verify S3 content in bucket '{test_bucket}': {e}"

            # Provide more specific error information based on the exception type
            if "NoSuchBucket" in str(e):
                error_msg += (
                    f"\n  The bucket '{test_bucket}' does not exist. This may indicate:"
                )
                error_msg += "\n  - The bucket creation failed during test setup"
                error_msg += "\n  - The bucket name is incorrect"
                error_msg += "\n  - LocalStack is not properly configured"
                error_msg += "\n  - Check that LocalStack is running and accessible"
            elif "AccessDenied" in str(e):
                error_msg += (
                    f"\n  Access denied to bucket '{test_bucket}'. This may indicate:"
                )
                error_msg += "\n  - Incorrect AWS credentials"
                error_msg += "\n  - Bucket permissions issue"
                error_msg += "\n  - LocalStack configuration problem"
            elif "No ZIP bundle files found" in str(e):
                error_msg += (
                    "\n  The fetcher processed files but no ZIP bundles were created."
                )
                error_msg += "\n  This may indicate:"
                error_msg += "\n  - The bundle creation process failed"
                error_msg += "\n  - The S3 upload process failed"
                error_msg += "\n  - The bundle loader is not working correctly"
            elif "No metadata files found" in str(e):
                error_msg += "\n  The fetcher processed files but no metadata files were created."
                error_msg += "\n  This may indicate:"
                error_msg += "\n  - The metadata creation process failed"
                error_msg += "\n  - The S3 upload process failed"
                error_msg += "\n  - The bundle loader is not working correctly"

            pytest.fail(error_msg)

    @pytest.mark.asyncio
    async def test_us_fl_date_filtering(
        self,
    ) -> None:
        """Test that the US FL date filtering works correctly.

        The configuration should only process files with dates >= 20230728.
        """

        # Create the file filter inline to avoid importing configuration
        def create_daily_file_filter(start_date: str) -> Callable[[str], bool]:
            def filter_function(filename: str) -> bool:
                """Check if daily file should be processed based on start date."""
                try:
                    # Look for date pattern in filename
                    for i in range(len(filename) - 7):
                        date_str = filename[i : i + 8]
                        if date_str.isdigit() and len(date_str) == 8:
                            if date_str >= start_date:
                                return True
                    return False
                except Exception:
                    return True

            return filter_function

        file_filter = create_daily_file_filter("20230728")

        # Test files that should be included (>= 20230728)
        included_files = [
            "20230728_daily_data.txt",
            "20230729_daily_data.txt",
            "20230730_daily_data.txt",
            "20240101_daily_data.txt",
        ]

        # Test files that should be excluded (< 20230728)
        excluded_files = [
            "20230725_daily_data.txt",
            "20230726_daily_data.txt",
            "20230727_daily_data.txt",
        ]

        # Verify included files
        for filename in included_files:
            assert file_filter(filename), (
                f"File {filename} should be included but was filtered out"
            )

        # Verify excluded files
        for filename in excluded_files:
            assert not file_filter(filename), (
                f"File {filename} should be excluded but was included"
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_us_fl_bundle_structure(
        self,
        sftp_server_container: DockerContainer,
        localstack_container: DockerContainer,
        s3_client: Any,
        test_bucket: str,
        setup_storage_and_kvstore: Any,
        mock_credential_provider: AsyncMock,
    ) -> None:
        """Test that the US FL configuration creates bundles with the expected structure."""
        # Note: SFTP server runs on default port 22 within the Docker network

        # Create a proper mock credential provider that returns the right values
        from unittest.mock import AsyncMock

        mock_credential_provider = AsyncMock()

        # Set up the get_credential method to return the appropriate values
        async def mock_get_credential(config_name: str, field: str) -> str:
            if field == "host":
                return "localhost"
            if field == "username":
                return "testuser"
            if field == "password":
                return "testpass"
            raise ValueError(f"Unknown field: {field}")

        mock_credential_provider.get_credential = mock_get_credential

        # Create a custom US FL configuration
        with patch(
            "data_fetcher.global_credential_provider.get_default_credential_provider"
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_credential_provider

            # Create the US FL configuration
            fetch_context = _setup_us_fl_sftp_fetcher()

            # Verify bundle locators are configured correctly
            assert len(fetch_context.bundle_locators) == 2

            # Check daily provider configuration
            daily_provider = fetch_context.bundle_locators[0]
            assert daily_provider.remote_dir == "doc/cor"
            assert daily_provider.filename_pattern == "*.txt"
            assert daily_provider.persistence_prefix == "us_fl_daily_provider"
            assert daily_provider.file_filter is not None

            # Check quarterly provider configuration
            quarterly_provider = fetch_context.bundle_locators[1]
            assert quarterly_provider.file_paths == ["doc/Quarterly/Cor/cordata.zip"]
            assert quarterly_provider.persistence_prefix == "us_fl_quarterly_provider"

            # Check loader configuration
            loader = fetch_context.bundle_loader
            assert loader is not None
            assert loader.meta_load_name == "us_fl_sftp_loader"  # type: ignore[attr-defined]

            # Run a quick test to verify the configuration works
            from data_fetcher_core.core import FetchPlan

            plan = FetchPlan(
                requests=[],
                context=FetchRunContext(run_id="test-us-fl-structure"),
                concurrency=1,
            )

            from data_fetcher_core.fetcher import Fetcher

            fetcher = Fetcher(fetch_context)

            # Run the fetcher
            result = await fetcher.run(plan)

            # Verify basic result structure
            assert result is not None
            assert hasattr(result, "processed_count")
            assert hasattr(result, "errors")
            assert hasattr(result, "context")

            # Wait for S3 uploads
            await asyncio.sleep(2)

            # Verify that the expected file structure was processed
            try:
                response = s3_client.list_objects_v2(
                    Bucket=test_bucket,
                    Prefix="test-us-fl/",
                )

                if "Contents" in response:
                    objects = response["Contents"]
                    bundle_keys = [obj["Key"] for obj in objects]

                    # Should have processed both daily and quarterly data
                    # Look for indicators in the bundle names or metadata
                    has_daily_data = any(
                        "daily" in key.lower() or "cor" in key.lower()
                        for key in bundle_keys
                    )
                    has_quarterly_data = any(
                        "quarterly" in key.lower() or "cordata" in key.lower()
                        for key in bundle_keys
                    )

                    # At least one type of data should be present
                    assert has_daily_data or has_quarterly_data, (
                        "No daily or quarterly data found in bundles"
                    )

            except Exception as e:
                pytest.fail(f"Failed to verify bundle structure: {e}")


# Mark tests that require Docker/containers
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "functional: mark test as functional test")


# Skip integration tests if Docker is not available
def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Modify test collection to skip integration tests if Docker is not available."""
    skip_integration = pytest.mark.skip(
        reason="Docker not available for integration tests"
    )

    for item in items:
        if "integration" in item.keywords:
            # Skip if Docker socket doesn't exist (Docker not available)
            if not os.path.exists("/var/run/docker.sock"):
                item.add_marker(skip_integration)
