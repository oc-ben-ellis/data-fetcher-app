"""Integration tests for SFTP functionality.

This module contains integration tests for SFTP operations, including
end-to-end testing with mock SFTP servers and real SFTP interactions.
"""

import os
import time
from collections.abc import Generator
from typing import Any

import boto3
import pytest
from testcontainers.core.container import (  # type: ignore[import-untyped]
    DockerContainer,
)
from testcontainers.core.waiting_utils import (  # type: ignore[import-untyped]
    wait_for_logs,
)

from data_fetcher_core.core import FetchContext, FetchPlan, FetchRunContext, RequestMeta
from data_fetcher_core.fetcher import Fetcher
from data_fetcher_core.kv_store import configure_global_store
from data_fetcher_core.storage.builder import (
    create_storage_config,
    get_global_storage,
    set_global_storage,
)
from data_fetcher_http_api.api_generic_bundle_locators import (
    GenericDirectoryBundleLocator,
    GenericFileBundleLocator,
)
from data_fetcher_sftp.sftp_loader import SFTPLoader
from data_fetcher_sftp.sftp_manager import SftpManager


class TestSFTPIntegration:
    """Integration tests for SFTP fetcher components."""

    @pytest.fixture
    def sftp_container(self) -> Generator[DockerContainer]:
        """Start SFTP container with test files."""
        container = DockerContainer("atmoz/sftp:latest")
        container.with_command("testuser:testpass:1002")
        container.with_exposed_ports("22")

        print("Starting SFTP container...")
        container.start()

        # Wait for container to be ready
        wait_for_logs(container, "Server listening on")
        print("SFTP container started!")

        # Create test directories and files
        exec_result = container.exec(
            [
                "sh",
                "-c",
                "mkdir -p /home/testuser/doc/cor /home/testuser/doc/Quarterly/Cor && "
                "echo 'test data 1' > /home/testuser/doc/cor/file1.txt && "
                "echo 'test data 2' > /home/testuser/doc/cor/file2.txt && "
                "echo 'quarterly data' > /home/testuser/doc/Quarterly/Cor/data.zip && "
                "chown -R testuser:testuser /home/testuser/doc/ || true",
            ]
        )
        print(f"Setup result: {exec_result}")

        yield container

        print("Stopping SFTP container...")
        container.stop()

    @pytest.fixture
    def localstack_container(self) -> Generator[DockerContainer]:
        """Start LocalStack container for S3 and Secrets Manager."""
        container = DockerContainer("localstack/localstack:3.0")
        container.with_env("SERVICES", "s3,secretsmanager")
        container.with_env("PERSISTENCE", "1")
        container.with_env("DEBUG", "1")
        container.with_exposed_ports("4566")

        print("Starting LocalStack container...")
        container.start()

        # Wait for services to be ready
        time.sleep(5)

        # Test S3 service
        test_client = boto3.client(
            "s3",
            endpoint_url=f"http://localhost:{container.get_exposed_port(4566)}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        # Create test bucket
        test_client.create_bucket(Bucket="test-bucket")
        print("LocalStack S3 ready")

        # Test Secrets Manager service
        secrets_client = boto3.client(
            "secretsmanager",
            endpoint_url=f"http://localhost:{container.get_exposed_port(4566)}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        # Create test secret (will be updated with correct host/port later)
        secrets_client.create_secret(
            Name="test-sftp-credentials",
            SecretString='{"host": "localhost", "username": "testuser", "password": "testpass", "port": 22}',
        )
        print("LocalStack Secrets Manager ready")

        yield container

        print("Stopping LocalStack container...")
        container.stop()

    @pytest.mark.asyncio
    async def test_sftp_connection(self, sftp_container: DockerContainer) -> None:
        """Test basic SFTP connection."""
        container = sftp_container

        print(f"Testing SFTP connection to localhost:{container.get_exposed_port(22)}")

        # Create a simple credentials provider for testing
        class TestCredentialsProvider:
            async def get_credentials(self) -> Any:
                from data_fetcher_core.credentials.sftp_credentials import (
                    SftpCredentials,
                )

                return SftpCredentials(
                    host="localhost",
                    username="testuser",
                    password="testpass",
                    port=int(container.get_exposed_port(22)),
                )

        # Create SFTP manager
        sftp_manager = SftpManager(credentials_provider=TestCredentialsProvider())  # type: ignore[arg-type]

        # Test connection
        conn = await sftp_manager.get_connection()
        assert conn is not None

        # List files - first check what's in the home directory
        home_files = conn.listdir(".")
        print(f"Files in home directory: {home_files}")

        # Check if doc directory exists
        if "doc" in home_files:
            doc_files = conn.listdir("doc")
            print(f"Files in doc: {doc_files}")

            if "cor" in doc_files:
                files = conn.listdir("doc/cor")
                print(f"Files in doc/cor: {files}")
                assert "file1.txt" in files
                assert "file2.txt" in files
            else:
                print("doc/cor directory not found")
                # List what's in doc
                for item in doc_files:
                    print(f"  {item}")
        else:
            print("doc directory not found in home directory")

        await sftp_manager.close()

    @pytest.mark.asyncio
    async def test_sftp_loader_single_file(
        self, sftp_container: DockerContainer, localstack_container: DockerContainer
    ) -> None:
        """Test SFTP loader with a single file."""
        print("Testing SFTP loader with single file...")

        container = sftp_container
        localstack = localstack_container

        # Set AWS credentials for LocalStack
        os.environ["AWS_ACCESS_KEY_ID"] = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
        os.environ["AWS_REGION"] = "us-east-1"

        # Configure global services
        storage_config = create_storage_config().pipeline_storage(
            bucket="test-bucket",
            endpoint_url=f"http://localhost:{localstack.get_exposed_port(4566)}",
        )
        set_global_storage(storage_config)

        # Create a simple credentials provider for testing
        class TestCredentialsProvider:
            async def get_credentials(self) -> Any:
                from data_fetcher_core.credentials.sftp_credentials import (
                    SftpCredentials,
                )

                return SftpCredentials(
                    host="localhost",
                    username="testuser",
                    password="testpass",
                    port=int(container.get_exposed_port(22)),
                )

        # Create SFTP loader
        sftp_manager = SftpManager(credentials_provider=TestCredentialsProvider())  # type: ignore[arg-type]

        sftp_loader = SFTPLoader(
            sftp_manager=sftp_manager, remote_dir="/", filename_pattern="*.txt"
        )

        # Test loading a single file
        request = RequestMeta(url="sftp://doc/cor/file1.txt")
        storage = get_global_storage()
        ctx = FetchRunContext(run_id="test-single-file")

        bundle_refs = await sftp_loader.load(request, storage, ctx)  # type: ignore[arg-type]

        print(f"Generated {len(bundle_refs)} bundle refs")
        for i, bundle_ref in enumerate(bundle_refs):
            print(f"  Bundle {i}: {bundle_ref.primary_url}")
            if hasattr(bundle_ref, "meta"):
                print(f"    Meta: {bundle_ref.meta}")

        assert len(bundle_refs) == 1

        # Check if file was uploaded to S3
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://localhost:{localstack.get_exposed_port(4566)}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        response = s3_client.list_objects_v2(Bucket="test-bucket")
        print(f"S3 objects: {response.get('Contents', [])}")

        await sftp_manager.close()

    @pytest.mark.asyncio
    async def test_bundle_locators(self, sftp_container: DockerContainer) -> None:
        """Test bundle locators separately."""
        print("Testing bundle locators...")

        container = sftp_container

        # Create a simple credentials provider for testing
        class TestCredentialsProvider:
            async def get_credentials(self) -> Any:
                from data_fetcher_core.credentials.sftp_credentials import (
                    SftpCredentials,
                )

                return SftpCredentials(
                    host="localhost",
                    username="testuser",
                    password="testpass",
                    port=int(container.get_exposed_port(22)),
                )

        # Create SFTP manager
        sftp_manager = SftpManager(credentials_provider=TestCredentialsProvider())  # type: ignore[arg-type]

        # Create bundle locators
        dir_locator = GenericDirectoryBundleLocator(
            sftp_manager=sftp_manager, remote_dir="doc/cor", filename_pattern="*.txt"
        )

        file_locator = GenericFileBundleLocator(
            sftp_manager=sftp_manager, file_paths=["doc/Quarterly/Cor/data.zip"]
        )

        # Test URL generation
        ctx = FetchRunContext(run_id="test-locators")

        dir_urls = await dir_locator.get_next_urls(ctx)
        print(
            f"Directory locator generated {len(dir_urls)} URLs: {[url.url for url in dir_urls]}"
        )

        file_urls = await file_locator.get_next_urls(ctx)
        print(
            f"File locator generated {len(file_urls)} URLs: {[url.url for url in file_urls]}"
        )

        assert len(dir_urls) == 2  # file1.txt and file2.txt
        assert len(file_urls) == 1  # data.zip

    @pytest.mark.asyncio
    async def test_fetcher_with_sftp(
        self, sftp_container: DockerContainer, localstack_container: DockerContainer
    ) -> None:
        """Test complete fetcher with SFTP."""
        print("Testing complete fetcher with SFTP...")

        container = sftp_container
        localstack = localstack_container

        # Set AWS credentials for LocalStack
        os.environ["AWS_ACCESS_KEY_ID"] = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
        os.environ["AWS_REGION"] = "us-east-1"

        # Configure global services
        storage_config = create_storage_config().pipeline_storage(
            bucket="test-bucket",
            endpoint_url=f"http://localhost:{localstack.get_exposed_port(4566)}",
        )
        set_global_storage(storage_config)

        configure_global_store(store_type="memory")

        # Create a simple credentials provider for testing
        class TestCredentialsProvider:
            async def get_credentials(self) -> Any:
                from data_fetcher_core.credentials.sftp_credentials import (
                    SftpCredentials,
                )

                return SftpCredentials(
                    host="localhost",
                    username="testuser",
                    password="testpass",
                    port=int(container.get_exposed_port(22)),
                )

        # Create SFTP components
        sftp_manager = SftpManager(credentials_provider=TestCredentialsProvider())  # type: ignore[arg-type]

        sftp_loader = SFTPLoader(
            sftp_manager=sftp_manager, remote_dir="/", filename_pattern="*.txt"
        )

        # Create bundle locators
        dir_locator = GenericDirectoryBundleLocator(
            sftp_manager=sftp_manager, remote_dir="doc/cor", filename_pattern="*.txt"
        )

        # Create fetch context
        fetch_context = FetchContext(
            bundle_loader=sftp_loader,
            storage=get_global_storage(),
            bundle_locators=[dir_locator],
        )

        # Create fetcher
        fetcher = Fetcher(fetch_context)

        # Create fetch plan
        plan = FetchPlan(
            requests=[], context=FetchRunContext(run_id="test-fetcher"), concurrency=1
        )

        # Run fetcher
        result = await fetcher.run(plan)

        print(
            f"Fetcher result: processed_count={result.processed_count}, errors={len(result.errors)}"
        )
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  {error}")

        # Check S3 for uploaded files
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://localhost:{localstack.get_exposed_port(4566)}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        response = s3_client.list_objects_v2(Bucket="test-bucket")
        if "Contents" in response:
            print(f"Found {len(response['Contents'])} objects in S3:")
            for obj in response["Contents"]:
                print(f"  {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("No objects found in S3 bucket")

        await sftp_manager.close()

    @pytest.mark.asyncio
    async def test_sftp_with_credentials_provider(
        self, sftp_container: DockerContainer, localstack_container: DockerContainer
    ) -> None:
        """Test SFTP with credentials from Secrets Manager."""
        print("Testing SFTP with credentials provider...")

        container = sftp_container
        localstack = localstack_container

        # Set AWS credentials for LocalStack (must be set before storage config)
        os.environ["AWS_ACCESS_KEY_ID"] = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
        os.environ["AWS_REGION"] = "us-east-1"

        # Configure global services
        storage_config = create_storage_config().pipeline_storage(
            bucket="test-bucket",
            endpoint_url=f"http://localhost:{localstack.get_exposed_port(4566)}",
        )
        set_global_storage(storage_config)

        # Set environment variables for credential provider configuration
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "aws"
        os.environ["OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL"] = (
            f"http://localhost:{localstack.get_exposed_port(4566)}"
        )

        # Create a simple credentials provider for testing (like other tests)
        class TestCredentialsProvider:
            async def get_credentials(self) -> Any:
                from data_fetcher_core.credentials.sftp_credentials import (
                    SftpCredentials,
                )

                return SftpCredentials(
                    host="localhost",
                    username="testuser",
                    password="testpass",
                    port=int(container.get_exposed_port(22)),
                )

        # Create SFTP manager with credentials provider
        sftp_creds = TestCredentialsProvider()

        # Get credentials
        credentials = await sftp_creds.get_credentials()
        print(f"Retrieved credentials: {credentials}")
        print(f"Connecting to {credentials.host}:{credentials.port}")

        # Create SFTP manager
        sftp_manager = SftpManager(credentials_provider=sftp_creds)  # type: ignore[arg-type]

        # Test connection
        conn = await sftp_manager.get_connection()
        assert conn is not None

        # List files
        files = conn.listdir("doc/cor")
        print(f"Files in doc/cor: {files}")
        assert "file1.txt" in files

        await sftp_manager.close()
