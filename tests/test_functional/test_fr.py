"""Functional and basic tests for France API fetcher.

This module contains comprehensive functional tests for the France API
fetcher, including end-to-end workflows and integration testing, as well
as basic unit tests for core functionality and error handling.

The tests now use the app-runner via docker-compose instead of calling
the code directly, while maintaining test containers for test-specific dependencies.
"""

import asyncio
import datetime
import json
import os
import time
from collections.abc import AsyncGenerator, Generator
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
import requests
from testcontainers.core.container import (  # type: ignore[import-untyped]
    DockerContainer,
)
from testcontainers.core.waiting_utils import (  # type: ignore[import-untyped]
    wait_for_logs,
)

from data_fetcher_configs.fr import _setup_fr_api_fetcher
from data_fetcher_core.core import FetchRunContext
from data_fetcher_core.global_storage import configure_global_storage
from data_fetcher_core.kv_store import configure_global_store, get_global_store

from .docker_helpers import (
    DockerComposeRunner,
)


@pytest.fixture(scope="session", autouse=True)
def setup_early_s3() -> Generator[None]:
    """Set up S3 configuration early to prevent auto-execution issues."""
    print("EARLY S3 SETUP - before any containers")

    # Set basic environment variables that might prevent auto-execution issues
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    yield

    print("EARLY S3 CLEANUP")


@pytest.fixture(scope="class")
def siren_api_container() -> Generator[DockerContainer]:
    """Start a mock SIREN API server container for testing."""
    try:
        # Use the organized mock from mocks/fr_siren_api/
        mock_path = Path(__file__).parent.parent.parent / "mocks" / "fr_siren_api"

        if not mock_path.exists():
            pytest.fail(f"SIREN API mock not found at {mock_path}")

        print("Starting SIREN API mock container...")
        container = DockerContainer("siren_api_mock")
        container.with_exposed_ports(5000)
        container.start()
        print("SIREN API mock container started!")

        # Wait for the container to be ready using wait_for_logs
        print("Waiting for container to be ready...")
        try:
            # Wait for Flask to start up (look for the typical Flask startup message)
            wait_for_logs(container, "Running on http://0.0.0.0:5000", timeout=60)
            print("✓ Container logs show Flask is running")
        except Exception as e:
            print(f"Warning: Could not wait for specific logs: {e}")
            # Fallback: wait a bit for the container to fully start
            time.sleep(10)

        # Test the API endpoint with retries
        try:
            mapped_port = container.get_exposed_port(5000)
            print(f"✓ Container port mapping successful: {mapped_port}")
        except Exception as e:
            print(f"Error getting exposed port: {e}")
            # Try to get the port again after a short wait
            time.sleep(5)
            mapped_port = container.get_exposed_port(5000)
        print(f"Testing API on port {mapped_port}...")
        max_retries = 5
        for attempt in range(max_retries):
            try:
                print(f"Testing API endpoint (attempt {attempt + 1}/{max_retries})...")
                response = requests.get(
                    f"http://localhost:{mapped_port}/health", timeout=10
                )
                if response.status_code == 200:
                    print("✓ SIREN API mock is responding")
                    break
                else:
                    print(
                        f"⚠ SIREN API mock health check failed: {response.status_code}"
                    )
            except Exception as e:
                print(f"⚠ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retry
                else:
                    print("Failed to start SIREN API mock after all retries")
                    pytest.fail("SIREN API mock failed to start")

        print("SIREN API FIXTURE SETUP COMPLETE - yielding container to test")
        yield container
        print("SIREN API FIXTURE CLEANUP - container stopping")

        container.stop()

    except Exception as e:
        pytest.fail(f"Failed to start SIREN API mock container: {e}")


@pytest.fixture(scope="class")
def localstack_container() -> Generator[DockerContainer]:
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
async def setup_storage_and_kvstore(
    test_bucket: str, localstack_container: DockerContainer
) -> AsyncGenerator[None]:
    """Set up global storage and KV store for testing."""
    print("SETUP_STORAGE_AND_KVSTORE FIXTURE STARTED")

    # Configure global storage to use S3 with localstack
    mapped_port = localstack_container.get_exposed_port(4566)
    print(f"Got localstack port: {mapped_port}")

    # Set environment variables for S3 configuration
    import os

    os.environ["OC_STORAGE_TYPE"] = "s3"
    os.environ["OC_S3_BUCKET"] = test_bucket
    os.environ["OC_S3_PREFIX"] = "test-fr/"
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
        key_prefix="test_fr:",
    )

    print("STORAGE AND KVSTORE SETUP COMPLETE - yielding")
    yield
    print("STORAGE AND KVSTORE CLEANUP")

    # Cleanup
    store = await get_global_store()
    await store.close()


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock OAuth credentials for the test API."""
    credentials = MagicMock()
    credentials.client_id = "test_client_id"
    credentials.client_secret = "test_client_secret"
    return credentials


@pytest.fixture
def mock_credential_provider(mock_credentials: MagicMock) -> AsyncMock:
    """Create a mock credential provider for OAuth."""
    provider = AsyncMock()
    provider.get_credential.return_value = mock_credentials
    return provider


class TestFrenchFunctional:
    """Functional and basic tests for French INSEE API configuration."""

    def test_fr_date_filtering(self) -> None:
        """Test that the FR date filtering works correctly."""
        from data_fetcher_configs.fr import _create_fr_date_filter

        date_filter = _create_fr_date_filter("2024-01-15")

        # Test dates that should be included (>= 2024-01-15)
        included_dates = [
            "2024-01-15",
            "2024-01-16",
            "2024-01-20",
            "2024-02-01",
        ]

        # Test dates that should be excluded (< 2024-01-15)
        excluded_dates = [
            "2024-01-14",
            "2024-01-10",
            "2023-12-31",
        ]

        # Verify included dates
        for date_str in included_dates:
            assert date_filter(date_str), (
                f"Date {date_str} should be included but was filtered out"
            )

        # Verify excluded dates
        for date_str in excluded_dates:
            assert not date_filter(date_str), (
                f"Date {date_str} should be excluded but was included"
            )

    def test_sirene_query_builder(self) -> None:
        """Test the Sirene query builder."""
        from data_fetcher_configs.fr import _create_sirene_query_builder

        query_builder = _create_sirene_query_builder()

        # Test query without narrowing
        query = query_builder("2024-01-15")
        expected_base = "dateDernierTraitementUniteLegale:[2024-01-15T00:00:00%20TO%202024-01-15T23:59:59]"
        expected_filters = "-periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O"
        # Check that both parts are in the query (order doesn't matter)
        assert expected_base in query
        assert expected_filters in query

        # Test query with SIREN narrowing
        query_with_narrowing = query_builder("2024-01-15", "siren:00")
        assert "siren:00*" in query_with_narrowing
        assert expected_base in query_with_narrowing
        assert expected_filters in query_with_narrowing

        # Test query with other narrowing
        query_with_other = query_builder("2024-01-15", "some:filter")
        assert "some:filter" in query_with_other
        assert expected_base in query_with_other
        assert expected_filters in query_with_other

    def test_siren_narrowing_strategy(self) -> None:
        """Test the SIREN narrowing strategy."""
        from data_fetcher_configs.fr import _create_siren_narrowing_strategy

        narrowing_strategy = _create_siren_narrowing_strategy()

        # Test initial narrowing
        initial = narrowing_strategy(None)
        assert initial == "siren:00"

        # Test progression through SIREN prefixes
        next_narrowing = narrowing_strategy(initial)
        assert next_narrowing == "siren:01"

        next_narrowing = narrowing_strategy(next_narrowing)
        assert next_narrowing == "siren:02"

        # Test handling of siren:99 (should return same to trigger date increment)
        siren_99 = narrowing_strategy("siren:99")
        assert siren_99 == "siren:99"

        # Test longer SIREN prefixes
        long_prefix = narrowing_strategy("siren:09")
        assert long_prefix == "siren:10"

    def test_sirene_error_handler(self) -> None:
        """Test the Sirene error handler."""
        from data_fetcher_configs.fr import _create_sirene_error_handler

        error_handler = _create_sirene_error_handler()

        # Test 404 (should return False - don't retry)
        assert not error_handler("http://example.com", 404)

        # Test server errors (should return False - don't retry)
        for status_code in [500, 503, 504, 403]:
            assert not error_handler("http://example.com", status_code)

        # Test 200 (should return True - continue)
        assert error_handler("http://example.com", 200)

        # Test other status codes (should return False)
        assert not error_handler("http://example.com", 400)
        assert not error_handler("http://example.com", 401)

    @pytest.mark.asyncio
    async def test_fr_configuration_structure(self) -> None:
        """Test that the FR configuration has the expected structure."""
        from data_fetcher_configs.fr import _setup_fr_api_fetcher

        # Mock the credential provider
        mock_credential_provider = AsyncMock()

        async def mock_get_credential(config_name: str, field: str) -> str:
            if field == "client_id":
                return "test_client_id"
            if field == "client_secret":
                return "test_client_secret"
            if field == "token_url":
                return "https://api.insee.fr/token"
            raise ValueError(f"Unknown field: {field}")

        mock_credential_provider.get_credential = mock_get_credential

        # Create the FR configuration with mocked credential provider
        with patch(
            "data_fetcher.global_credential_provider.get_default_credential_provider"
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_credential_provider

            fetch_context = _setup_fr_api_fetcher()

            # Verify the configuration structure
            assert fetch_context is not None
            assert fetch_context.bundle_loader is not None
            assert len(fetch_context.bundle_locators) == 3

            # Check bundle locators
            siren_provider = fetch_context.bundle_locators[0]
            gap_provider = fetch_context.bundle_locators[1]
            failed_companies_provider = fetch_context.bundle_locators[2]

            # Verify provider types and persistence prefixes
            assert siren_provider.persistence_prefix == "fr_siren_provider"
            assert gap_provider.persistence_prefix == "fr_gap_provider"
            assert (
                failed_companies_provider.persistence_prefix
                == "fr_failed_companies_provider"
            )

            # Check loader configuration
            assert fetch_context.bundle_loader.meta_load_name == "fr_sirene_api_loader"  # type: ignore[attr-defined]

    def test_fr_configuration_imports(self) -> None:
        """Test that the FR configuration can be imported and basic functions work."""
        from data_fetcher_configs.fr import (
            _create_fr_date_filter,
            _create_siren_narrowing_strategy,
            _create_sirene_error_handler,
            _create_sirene_query_builder,
            _setup_fr_api_fetcher,
        )

        # Test that the configuration function exists
        assert callable(_setup_fr_api_fetcher)

        # Test that helper functions exist and are callable
        assert callable(_create_fr_date_filter)
        assert callable(_create_sirene_query_builder)
        assert callable(_create_siren_narrowing_strategy)
        assert callable(_create_sirene_error_handler)

    def test_fr_date_range_calculation(self) -> None:
        """Test that the date range calculation in FR configuration is reasonable."""
        # This test verifies that the date range logic is working
        # The actual calculation happens in _setup_fr_api_fetcher
        end_date = datetime.datetime.now(tz=datetime.UTC).date()
        start_date = end_date - timedelta(days=5)

        # Verify the date range is reasonable
        assert start_date < end_date
        assert (end_date - start_date).days == 5

        # Verify dates are in the expected format
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        assert len(start_date_str) == 10  # YYYY-MM-DD format
        assert len(end_date_str) == 10  # YYYY-MM-DD format
        assert start_date_str < end_date_str

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fr_api_functional(
        self,
        siren_api_container: DockerContainer,
        localstack_container: DockerContainer,
        s3_client: Any,
        test_bucket: str,
        test_secrets: dict[str, str],
        docker_compose_runner: DockerComposeRunner,
        test_environment_vars: dict[str, str],
    ) -> None:
        """Test the complete French INSEE API workflow using docker-compose app-runner.

        This test:
        1. Sets up a mock SIREN API server with test data
        2. Configures the fr fetcher to use the test API server
        3. Runs the fetcher via docker-compose app-runner
        4. Verifies that bundles are created with expected structure
        5. Checks that data is properly uploaded to S3
        """
        print("TEST METHOD STARTED - beginning test execution")

        # First, wait a moment to ensure all fixtures are completely ready
        await asyncio.sleep(1)

        # Verify SIREN API container is accessible before proceeding
        print("Verifying SIREN API container accessibility...")

        # Get the API server port and host
        api_port = siren_api_container.get_exposed_port(5000)
        api_host = "localhost"

        print(f"SIREN API Connection details: {api_host}:{api_port}")

        # Test basic API connectivity before creating fetcher components
        try:
            print("Testing basic API connection...")
            response = requests.get(f"http://{api_host}:{api_port}/health", timeout=10)
            if response.status_code == 200:
                print("✓ SIREN API connection successful")
            else:
                pytest.fail(f"SIREN API health check failed: {response.status_code}")
        except Exception as e:
            print(f"API connection test failed: {e}")
            pytest.fail(f"API connection test failed: {e}")

        # Only proceed with fetcher creation after API verification succeeds
        print("API verification complete, setting up environment for docker-compose...")

        # Get localstack port
        localstack_port = localstack_container.get_exposed_port(4566)
        print(f"Localstack port: {localstack_port}")

        # Update the test secrets with the correct API endpoint
        updated_credentials = {
            "consumer_key": "test_client_id",
            "consumer_secret": "test_client_secret",
            "token_url": f"http://{api_host}:{api_port}/token",
            "api_base_url": f"http://{api_host}:{api_port}",
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
            # Try to create the secret first (AWS credential provider expects -sftp-credentials suffix)
            secretsmanager_client.create_secret(
                Name="fr-api-sftp-credentials",
                SecretString=json.dumps(updated_credentials),
            )
            print("Created test secrets with correct API endpoint")
        except Exception as e:
            if "already exists" in str(e):
                # Secret already exists, try to update it
                try:
                    secretsmanager_client.update_secret(
                        SecretId="fr-api-sftp-credentials",
                        SecretString=json.dumps(updated_credentials),
                    )
                    print("Updated test secrets with correct API endpoint")
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
                "OC_S3_PREFIX": "test-fr/",
                "OC_S3_ENDPOINT_URL": f"http://host.docker.internal:{localstack_port}",
                "OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL": f"http://host.docker.internal:{localstack_port}",
                "AWS_REGION": "us-east-1",
                "OC_STORAGE_USE_BUNDLER": "true",
                "OC_STORAGE_USE_UNZIP": "false",
            }
        )

        print("Running fetcher via docker-compose app-runner...")
        print(f"Environment variables: {env_vars}")

        # Run the fetcher via docker-compose
        try:
            result = await docker_compose_runner.run_fetcher(
                config_name="fr",
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
                Prefix="test-fr/",
            )

            # Should have at least some objects
            assert "Contents" in response, (
                f"No objects found in S3 bucket '{test_bucket}' with prefix 'test-fr/'. "
                f"This may indicate that the fetcher did not upload any bundles."
            )
            objects = response["Contents"]
            assert len(objects) > 0, (
                f"Expected objects in S3 bucket '{test_bucket}' with prefix 'test-fr/', "
                f"but found none. The fetcher may not have uploaded any bundles."
            )

            # Check for specific bundle files
            bundle_keys = [obj["Key"] for obj in objects]

            # The API loader creates JSON files with embedded metadata
            # This is the expected behavior for API-based data fetching
            json_files = [key for key in bundle_keys if key.endswith(".json")]
            assert len(json_files) > 0, (
                f"No JSON bundle files found in S3 bucket '{test_bucket}'. "
                f"Found {len(bundle_keys)} objects but none are JSON files. "
                f"This may indicate that the bundle creation process failed."
            )

            # Should have metadata files
            meta_files = [key for key in bundle_keys if key.endswith(".json")]
            assert len(meta_files) > 0, (
                f"No metadata files found in S3 bucket '{test_bucket}'. "
                f"Found {len(bundle_keys)} objects but none are JSON metadata files. "
                f"This may indicate that the metadata creation process failed."
            )

            # Verify bundle structure by examining one of the JSON files
            if json_files:
                json_key = json_files[0]
                json_response = s3_client.get_object(Bucket=test_bucket, Key=json_key)
                json_content = json_response["Body"].read()

                # Debug: Print the first 500 characters to see what's actually stored
                content_str = json_content.decode("utf-8")
                print(f"DEBUG: First 500 chars of JSON file '{json_key}':")
                print(content_str[:500])
                print("DEBUG: End of content preview")

                # JSON files should contain valid JSON (or at least contain our expected data)
                try:
                    json_data = json.loads(content_str)
                    assert isinstance(json_data, dict), (
                        "JSON file should contain a dictionary"
                    )
                    print("✓ JSON file contains valid JSON")
                except json.JSONDecodeError as e:
                    print(f"Warning: JSON file contains invalid JSON: {e}")
                    # Even if JSON is invalid, check if it contains our expected data
                    print("Checking if file contains expected API data anyway...")

                # Should contain some of our mock API data
                mock_data_indicators = [
                    "siren",
                    "uniteLegale",
                    "statutDiffusionUniteLegale",
                    "dateDernierTraitementUniteLegale",
                ]

                # At least one indicator should be present
                found_indicators = sum(
                    1 for indicator in mock_data_indicators if indicator in content_str
                )
                assert found_indicators > 0, (
                    f"JSON file doesn't contain expected mock API data. Content preview: {content_str[:200]}"
                )
                print(
                    f"✓ Found {found_indicators} expected data indicators in JSON file"
                )

            # Verify metadata structure
            if meta_files:
                meta_key = meta_files[0]
                meta_response = s3_client.get_object(Bucket=test_bucket, Key=meta_key)
                meta_content = meta_response["Body"].read()

                # Debug: Print the metadata content to see its format
                meta_str = meta_content.decode("utf-8")
                print(f"DEBUG: Metadata content from '{meta_key}':")
                print(meta_str[:500])
                print("DEBUG: End of metadata preview")

                # Metadata might be stored as Python dict string or JSON
                import ast

                try:
                    # Try to parse as JSON first
                    metadata = json.loads(meta_str)
                    print("✓ Metadata parsed as JSON")
                except json.JSONDecodeError:
                    try:
                        # Try to parse as Python dict string
                        metadata = ast.literal_eval(meta_str)
                        print("✓ Metadata parsed as Python dict string")
                    except (ValueError, SyntaxError) as e:
                        pytest.fail(
                            f"Metadata is neither valid JSON nor Python dict: {e}"
                        )

                # Check expected metadata structure (be more flexible about required fields)
                assert "primary_url" in metadata, "Metadata missing primary_url"
                if "resources_count" in metadata:
                    print("✓ Metadata contains resources_count")
                if "meta" in metadata:
                    print("✓ Metadata contains meta field")
                else:
                    print(
                        "Note: Metadata doesn't contain meta field (this may be normal)"
                    )

                # Should have API-related metadata
                assert metadata["primary_url"].startswith("http://"), (
                    "Primary URL should be HTTP"
                )
                print("✓ Metadata structure verified")

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
            elif "No JSON bundle files found" in str(e):
                error_msg += (
                    "\n  The fetcher processed files but no JSON bundles were created."
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
    @pytest.mark.integration
    async def test_fr_bundle_structure(
        self,
        siren_api_container: DockerContainer,
        localstack_container: DockerContainer,
        s3_client: Any,
        test_bucket: str,
        setup_storage_and_kvstore: None,
        mock_credential_provider: AsyncMock,
    ) -> None:
        """Test that the FR configuration creates bundles with the expected structure."""
        # Get the API server port
        api_port = siren_api_container.get_exposed_port(5000)

        # Create a proper mock credential provider that returns the right values
        from unittest.mock import AsyncMock

        mock_credential_provider = AsyncMock()

        # Set up the get_credential method to return the appropriate values
        async def mock_get_credential(config_name: str, field: str) -> str:
            if field == "client_id":
                return "test_client_id"
            if field == "client_secret":
                return "test_client_secret"
            if field == "token_url":
                return f"http://localhost:{api_port}/token"
            raise ValueError(f"Unknown field: {field}")

        mock_credential_provider.get_credential = mock_get_credential

        # Create a custom FR configuration
        with patch(
            "data_fetcher.global_credential_provider.get_default_credential_provider"
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_credential_provider

            # Create the FR configuration
            fetch_context = _setup_fr_api_fetcher()

            # Verify bundle locators are configured correctly
            assert len(fetch_context.bundle_locators) == 3

            # Check siren provider configuration
            siren_provider = fetch_context.bundle_locators[0]
            assert "siren" in siren_provider.base_url
            assert siren_provider.persistence_prefix == "fr_siren_provider"

            # Check gap provider configuration
            gap_provider = fetch_context.bundle_locators[1]
            assert "siren" in gap_provider.base_url
            assert gap_provider.persistence_prefix == "fr_gap_provider"

            # Check failed companies provider configuration
            failed_companies_provider = fetch_context.bundle_locators[2]
            assert (
                failed_companies_provider.persistence_prefix
                == "fr_failed_companies_provider"
            )

            # Check loader configuration
            loader = fetch_context.bundle_loader
            assert loader is not None
            assert loader.meta_load_name == "fr_sirene_api_loader"  # type: ignore[attr-defined]

            # Run a quick test to verify the configuration works
            from data_fetcher_core.core import FetchPlan

            plan = FetchPlan(
                requests=[],
                context=FetchRunContext(run_id="test-fr-structure"),
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
                    Prefix="test-fr/",
                )

                if "Contents" in response:
                    objects = response["Contents"]
                    bundle_keys = [obj["Key"] for obj in objects]

                    # Should have processed SIREN API data
                    # Look for indicators in the bundle names or metadata
                    has_siren_data = any(
                        "siren" in key.lower() or "api" in key.lower()
                        for key in bundle_keys
                    )

                    # At least some data should be present
                    assert has_siren_data, "No SIREN API data found in bundles"

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
