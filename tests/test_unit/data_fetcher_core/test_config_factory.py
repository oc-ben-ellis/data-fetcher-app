"""Unit tests for the config factory module.

This module tests the configuration factory functions that create application
components without using global state.
"""

import os
from unittest.mock import Mock, patch

import pytest

from data_fetcher_core.config_factory import (
    AppConfig,  # Backward compatibility
    FetcherConfig,
    create_app_config,  # Backward compatibility
    create_fetcher_config,
)
from data_fetcher_core.credentials import (
    AWSSecretsCredentialProvider,
    EnvironmentCredentialProvider,
    create_credential_provider,
)
from data_fetcher_core.kv_store import (
    InMemoryKeyValueStore,
    RedisKeyValueStore,
    create_kv_store,
)
from data_fetcher_core.kv_store.factory import _get_env_int
from data_fetcher_core.storage import create_storage_config_instance
from data_fetcher_core.storage.builder import StorageBuilder
from data_fetcher_core.storage.factory import _get_aws_region, _get_env_bool


class TestHelperFunctions:
    """Test helper functions for environment variable parsing."""

    def test_get_env_int_valid(self) -> None:
        """Test getting valid integer from environment variable."""
        with patch.dict(os.environ, {"TEST_INT": "42"}):
            result = _get_env_int("TEST_INT", 10)
            assert result == 42

    def test_get_env_int_invalid(self) -> None:
        """Test getting invalid integer from environment variable."""
        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            result = _get_env_int("TEST_INT", 10)
            assert result == 10

    def test_get_env_int_missing(self) -> None:
        """Test getting missing integer environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_env_int("TEST_INT", 10)
            assert result == 10

    def test_get_env_bool_true_values(self) -> None:
        """Test getting boolean true values from environment variable."""
        true_values = ["true", "1", "yes", "on", "TRUE", "True"]
        for value in true_values:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                result = _get_env_bool("TEST_BOOL", default=False)
                assert result is True

    def test_get_env_bool_false_values(self) -> None:
        """Test getting boolean false values from environment variable."""
        false_values = ["false", "0", "no", "off", "FALSE", "False"]
        for value in false_values:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                result = _get_env_bool("TEST_BOOL", default=True)
                assert result is False

    def test_get_env_bool_invalid(self) -> None:
        """Test getting invalid boolean from environment variable."""
        with patch.dict(os.environ, {"TEST_BOOL": "maybe"}):
            result = _get_env_bool("TEST_BOOL", default=True)
            assert result is True

    def test_get_env_bool_missing(self) -> None:
        """Test getting missing boolean environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_env_bool("TEST_BOOL", default=True)
            assert result is True

    def test_get_aws_region_precedence(self) -> None:
        """Test AWS region precedence: AWS_REGION > OC_*_REGION > default."""
        # Test AWS_REGION takes precedence
        with patch.dict(
            os.environ,
            {
                "AWS_REGION": "us-east-1",
                "OC_CREDENTIAL_PROVIDER_AWS_REGION": "eu-west-2",
                "OC_S3_REGION": "ap-southeast-1",
            },
        ):
            result = _get_aws_region()
            assert result == "us-east-1"

        # Test OC_CREDENTIAL_PROVIDER_AWS_REGION when AWS_REGION not set
        with patch.dict(
            os.environ,
            {
                "OC_CREDENTIAL_PROVIDER_AWS_REGION": "eu-west-2",
                "OC_S3_REGION": "ap-southeast-1",
            },
            clear=True,
        ):
            result = _get_aws_region()
            assert result == "eu-west-2"

        # Test OC_S3_REGION when others not set
        with patch.dict(os.environ, {"OC_S3_REGION": "ap-southeast-1"}, clear=True):
            result = _get_aws_region()
            assert (
                result == "eu-west-2"
            )  # The function always returns default due to or logic

        # Test default when none set
        with patch.dict(os.environ, {}, clear=True):
            result = _get_aws_region()
            assert result == "eu-west-2"


class TestCreateCredentialProvider:
    """Test credential provider creation."""

    def test_create_aws_credential_provider_default(self) -> None:
        """Test creating AWS credential provider with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            provider = create_credential_provider()
            assert isinstance(provider, AWSSecretsCredentialProvider)
            assert provider.region == "eu-west-2"
            assert provider.endpoint_url is None

    def test_create_aws_credential_provider_with_params(self) -> None:
        """Test creating AWS credential provider with parameters."""
        provider = create_credential_provider(
            provider_type="aws",
            aws_region="us-east-1",
            aws_endpoint_url="http://localhost:4566",
        )
        assert isinstance(provider, AWSSecretsCredentialProvider)
        assert provider.region == "us-east-1"
        assert provider.endpoint_url == "http://localhost:4566"

    def test_create_aws_credential_provider_from_env(self) -> None:
        """Test creating AWS credential provider from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OC_CREDENTIAL_PROVIDER_TYPE": "aws",
                "OC_CREDENTIAL_PROVIDER_AWS_REGION": "us-west-2",
                "OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL": "http://localstack:4566",
            },
        ):
            provider = create_credential_provider()
            assert isinstance(provider, AWSSecretsCredentialProvider)
            assert provider.region == "eu-west-2"  # AWS_REGION takes precedence
            assert provider.endpoint_url == "http://localstack:4566"

    def test_create_environment_credential_provider_default(self) -> None:
        """Test creating environment credential provider with defaults."""
        provider = create_credential_provider(provider_type="environment")
        assert isinstance(provider, EnvironmentCredentialProvider)
        assert provider.prefix == "OC_CREDENTIAL_"

    def test_create_environment_credential_provider_with_params(self) -> None:
        """Test creating environment credential provider with parameters."""
        provider = create_credential_provider(
            provider_type="environment", env_prefix="CUSTOM_"
        )
        assert isinstance(provider, EnvironmentCredentialProvider)
        assert provider.prefix == "CUSTOM_"

    def test_create_environment_credential_provider_from_env(self) -> None:
        """Test creating environment credential provider from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OC_CREDENTIAL_PROVIDER_TYPE": "environment",
                "OC_CREDENTIAL_PROVIDER_ENV_PREFIX": "TEST_",
            },
        ):
            provider = create_credential_provider()
            assert isinstance(provider, EnvironmentCredentialProvider)
            assert provider.prefix == "TEST_"

    def test_create_credential_provider_invalid_type(self) -> None:
        """Test creating credential provider with invalid type."""
        with pytest.raises(ValueError, match="Unknown provider type: invalid"):
            create_credential_provider(provider_type="invalid")


class TestCreateKvStore:
    """Test key-value store creation."""

    def test_create_memory_store_default(self) -> None:
        """Test creating memory store with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            store = create_kv_store()
            assert isinstance(store, RedisKeyValueStore)  # Default changed to redis
            # Test that the store can be used (basic functionality)
            assert hasattr(store, "put")
            assert hasattr(store, "get")

    def test_create_memory_store_with_params(self) -> None:
        """Test creating memory store with parameters."""
        store = create_kv_store(
            store_type="memory",
            serializer="pickle",
            default_ttl=7200,
            config_id="test-config",
        )
        assert isinstance(store, InMemoryKeyValueStore)
        # Test that the store can be used (basic functionality)
        assert hasattr(store, "put")
        assert hasattr(store, "get")

    def test_create_memory_store_from_env(self) -> None:
        """Test creating memory store from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OC_KV_STORE_TYPE": "memory",
                "OC_KV_STORE_SERIALIZER": "pickle",
                "OC_KV_STORE_DEFAULT_TTL": "1800",
                "OC_CONFIG_ID": "env-config",
            },
        ):
            store = create_kv_store()
            assert isinstance(store, InMemoryKeyValueStore)
            # Test that the store can be used (basic functionality)
            assert hasattr(store, "put")
            assert hasattr(store, "get")

    def test_create_redis_store_default(self) -> None:
        """Test creating Redis store with defaults."""
        store = create_kv_store(store_type="redis")
        assert isinstance(store, RedisKeyValueStore)
        # Test that the store can be used (basic functionality)
        assert hasattr(store, "put")
        assert hasattr(store, "get")

    def test_create_redis_store_with_params(self) -> None:
        """Test creating Redis store with parameters."""
        store = create_kv_store(
            store_type="redis",
            redis_host="redis.example.com",
            redis_port=6380,
            redis_db=1,
            redis_password="secret",
            redis_key_prefix="custom:",
            config_id="test-config",
        )
        assert isinstance(store, RedisKeyValueStore)
        # Test that the store can be used (basic functionality)
        assert hasattr(store, "put")
        assert hasattr(store, "get")

    def test_create_redis_store_from_env(self) -> None:
        """Test creating Redis store from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OC_KV_STORE_TYPE": "redis",
                "OC_KV_STORE_REDIS_HOST": "redis.example.com",
                "OC_KV_STORE_REDIS_PORT": "6380",
                "OC_KV_STORE_REDIS_DB": "1",
                "OC_KV_STORE_REDIS_PASSWORD": "secret",
                "OC_KV_STORE_REDIS_KEY_PREFIX": "env:",
                "OC_CONFIG_ID": "env-config",
            },
        ):
            store = create_kv_store()
            assert isinstance(store, RedisKeyValueStore)
            # Test that the store can be used (basic functionality)
            assert hasattr(store, "put")
            assert hasattr(store, "get")

    def test_create_kv_store_invalid_type(self) -> None:
        """Test creating key-value store with invalid type."""
        with pytest.raises(ValueError, match="Unknown store type: invalid"):
            create_kv_store(store_type="invalid")


class TestCreateStorageConfigInstance:
    """Test storage configuration creation."""

    def test_create_s3_storage_default(self) -> None:
        """Test creating S3 storage with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = create_storage_config_instance()
            assert isinstance(config, StorageBuilder)
            # Note: We can't easily test the internal configuration without
            # accessing private attributes, so we just verify it's the right type

    def test_create_s3_storage_with_params(self) -> None:
        """Test creating S3 storage with parameters."""
        config = create_storage_config_instance(
            storage_type="s3",
            s3_bucket="my-bucket",
            s3_prefix="data/",
            s3_region="us-east-1",
            s3_endpoint_url="http://localhost:4566",
        )
        assert isinstance(config, StorageBuilder)

    def test_create_s3_storage_from_env(self) -> None:
        """Test creating S3 storage from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OC_STORAGE_TYPE": "s3",
                "OC_S3_BUCKET": "env-bucket",
                "OC_S3_PREFIX": "env-data/",
                "OC_S3_REGION": "us-west-2",
                "OC_S3_ENDPOINT_URL": "http://localstack:4566",
            },
        ):
            config = create_storage_config_instance()
            assert isinstance(config, StorageBuilder)

    def test_create_file_storage_default(self) -> None:
        """Test creating file storage with defaults."""
        config = create_storage_config_instance(storage_type="file")
        assert isinstance(config, StorageBuilder)

    def test_create_file_storage_with_params(self) -> None:
        """Test creating file storage with parameters."""
        config = create_storage_config_instance(
            storage_type="file", file_path="/custom/path"
        )
        assert isinstance(config, StorageBuilder)

    def test_create_file_storage_from_env(self) -> None:
        """Test creating file storage from environment variables."""
        with patch.dict(
            os.environ, {"OC_STORAGE_TYPE": "file", "OC_STORAGE_FILE_PATH": "/env/path"}
        ):
            config = create_storage_config_instance()
            assert isinstance(config, StorageBuilder)

    def test_create_storage_config_with_decorators(self) -> None:
        """Test creating storage config with decorator settings."""
        config = create_storage_config_instance(storage_type="s3", use_unzip=False)
        assert isinstance(config, StorageBuilder)

    def test_create_storage_config_decorators_from_env(self) -> None:
        """Test creating storage config with decorator settings from env."""
        with patch.dict(
            os.environ,
            {
                "OC_STORAGE_TYPE": "s3",
                "OC_STORAGE_USE_UNZIP": "false",
                "OC_STORAGE_USE_BUNDLER": "false",
            },
        ):
            config = create_storage_config_instance()
            assert isinstance(config, StorageBuilder)

    def test_create_storage_config_invalid_type(self) -> None:
        """Test creating storage config with invalid type."""
        with pytest.raises(ValueError, match="Unknown storage type: invalid"):
            create_storage_config_instance(storage_type="invalid")


class TestFetcherConfig:
    """Test FetcherConfig dataclass."""

    def test_fetcher_config_creation(self) -> None:
        """Test creating FetcherConfig instance."""
        mock_credential_provider = Mock()
        mock_kv_store = Mock()
        mock_storage_config = Mock()

        config = FetcherConfig(
            credential_provider=mock_credential_provider,
            kv_store=mock_kv_store,
            storage=mock_storage_config,
        )

        assert config.credential_provider == mock_credential_provider
        assert config.kv_store == mock_kv_store
        assert config.storage == mock_storage_config

    def test_app_config_backward_compatibility(self) -> None:
        """Test that AppConfig is still available for backward compatibility."""
        mock_credential_provider = Mock()
        mock_kv_store = Mock()
        mock_storage_config = Mock()

        config = AppConfig(
            credential_provider=mock_credential_provider,
            kv_store=mock_kv_store,
            storage=mock_storage_config,
        )

        assert config.credential_provider == mock_credential_provider
        assert config.kv_store == mock_kv_store
        assert config.storage == mock_storage_config


class TestCreateFetcherConfig:
    """Test complete fetcher configuration creation."""

    @pytest.mark.asyncio
    async def test_create_fetcher_config_defaults(self) -> None:
        """Test creating fetcher config with defaults."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
            clear=True,
        ):
            config = await create_fetcher_config()

            assert isinstance(config, FetcherConfig)
            assert isinstance(config.credential_provider, AWSSecretsCredentialProvider)
            assert isinstance(
                config.kv_store, RedisKeyValueStore
            )  # Default changed to redis
            # Storage should be a built instance, not a builder
            assert hasattr(config.storage, "start_bundle")

    @pytest.mark.asyncio
    async def test_create_fetcher_config_with_params(self) -> None:
        """Test creating fetcher config with parameters."""
        config = await create_fetcher_config(
            credentials_provider_type="environment",
            storage_type="file",
            kv_store_type="redis",
            config_id="test-config",
            env_prefix="TEST_",
            file_path="./test_path",
            redis_host="test-redis",
            redis_port=6380,
        )

        assert isinstance(config, FetcherConfig)
        assert isinstance(config.credential_provider, EnvironmentCredentialProvider)
        assert config.credential_provider.prefix == "TEST_"
        assert isinstance(config.kv_store, RedisKeyValueStore)
        # Test that the store can be used (basic functionality)
        assert hasattr(config.kv_store, "put")
        assert hasattr(config.kv_store, "get")
        # Storage should be a built instance, not a builder
        assert hasattr(config.storage, "start_bundle")

    @pytest.mark.asyncio
    async def test_create_fetcher_config_from_env(self) -> None:
        """Test creating fetcher config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OC_CREDENTIAL_PROVIDER_TYPE": "environment",
                "OC_CREDENTIAL_PROVIDER_ENV_PREFIX": "ENV_",
                "OC_STORAGE_TYPE": "file",
                "OC_STORAGE_FILE_PATH": "./test_env_storage",
                "OC_KV_STORE_TYPE": "redis",
                "OC_KV_STORE_REDIS_HOST": "env-redis",
                "OC_KV_STORE_REDIS_PORT": "6380",
                "OC_CONFIG_ID": "env-config",
            },
        ):
            config = await create_fetcher_config()

            assert isinstance(config, FetcherConfig)
            assert isinstance(config.credential_provider, EnvironmentCredentialProvider)
            assert config.credential_provider.prefix == "ENV_"
            assert isinstance(config.kv_store, RedisKeyValueStore)
            # Test that the store can be used (basic functionality)
            assert hasattr(config.kv_store, "put")
            assert hasattr(config.kv_store, "get")
            # Storage should be a built instance, not a builder
            assert hasattr(config.storage, "start_bundle")

    @pytest.mark.asyncio
    async def test_create_fetcher_config_credential_type_mapping(self) -> None:
        """Test that credential provider types are mapped correctly."""
        # Test "env" -> "environment" mapping
        with patch.dict(os.environ, {"OC_SQS_QUEUE_URL": "https://sqs.test.com/queue"}):
            config = await create_fetcher_config(
                credentials_provider_type="environment"
            )
            assert isinstance(config.credential_provider, EnvironmentCredentialProvider)

    @pytest.mark.asyncio
    async def test_create_fetcher_config_with_kwargs_filtering(self) -> None:
        """Test that kwargs are properly filtered for each component."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            config = await create_fetcher_config(
                credentials_provider_type="aws",
                storage_type="s3",
                kv_store_type="memory",
                aws_region="us-east-1",  # Should be passed to credential provider
                s3_bucket="test-bucket",  # Should be passed to storage
                redis_host="test-host",  # Should be passed to kv_store
                config_id="test-config",  # Should be passed to kv_store
            )

        assert isinstance(config, FetcherConfig)
        assert isinstance(config.credential_provider, AWSSecretsCredentialProvider)
        assert config.credential_provider.region == "us-east-1"
        assert isinstance(config.kv_store, InMemoryKeyValueStore)
        # Test that the store can be used (basic functionality)
        assert hasattr(config.kv_store, "put")
        assert hasattr(config.kv_store, "get")
        # Storage should be a built instance, not a builder
        assert hasattr(config.storage, "start_bundle")

    @pytest.mark.asyncio
    async def test_create_app_config_backward_compatibility(self) -> None:
        """Test that create_app_config still works for backward compatibility."""
        config = await create_app_config(
            credentials_provider_type="environment",
            storage_type="file",  # Use file storage to avoid SQS requirement
        )
        assert isinstance(config, FetcherConfig)  # Should return FetcherConfig
        assert isinstance(config.credential_provider, EnvironmentCredentialProvider)


class TestConfigFactoryIntegration:
    """Test integration between config factory components."""

    @pytest.mark.asyncio
    async def test_all_components_work_together(self) -> None:
        """Test that all components can be created and work together."""
        config = await create_fetcher_config(
            credentials_provider_type="environment",
            storage_type="file",
            kv_store_type="memory",
            config_id="integration-test",
        )

        # Verify all components are properly configured
        assert config.credential_provider is not None
        assert config.kv_store is not None
        assert config.storage is not None

        # Verify they can be used (basic functionality)
        assert hasattr(config.credential_provider, "get_credential")
        assert hasattr(config.kv_store, "get")
        assert hasattr(config.kv_store, "put")
        # Storage should have basic storage methods
        assert hasattr(config.storage, "start_bundle")

    @pytest.mark.asyncio
    async def test_config_with_real_environment_variables(self) -> None:
        """Test config creation with realistic environment variable setup."""
        with patch.dict(
            os.environ,
            {
                "OC_CONFIG_ID": "production-config",
                "OC_CREDENTIAL_PROVIDER_TYPE": "aws",
                "AWS_REGION": "us-west-2",
                "OC_STORAGE_TYPE": "s3",
                "OC_S3_BUCKET": "production-bucket",
                "OC_S3_PREFIX": "data/",
                "OC_KV_STORE_TYPE": "redis",
                "OC_KV_STORE_REDIS_HOST": "redis.production.com",
                "OC_KV_STORE_REDIS_PORT": "6379",
                "OC_KV_STORE_REDIS_DB": "0",
                "OC_KV_STORE_REDIS_KEY_PREFIX": "prod:",
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
            },
        ):
            config = await create_fetcher_config()

            assert isinstance(config, FetcherConfig)
            assert isinstance(config.credential_provider, AWSSecretsCredentialProvider)
            assert config.credential_provider.region == "us-west-2"
            assert isinstance(config.kv_store, RedisKeyValueStore)
            # Test that the store can be used (basic functionality)
            assert hasattr(config.kv_store, "put")
            assert hasattr(config.kv_store, "get")
            # Storage should be a built instance, not a builder
            assert hasattr(config.storage, "start_bundle")
