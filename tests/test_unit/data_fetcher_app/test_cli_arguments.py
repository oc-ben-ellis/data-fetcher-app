"""Unit tests for CLI arguments and AWS profile propagation.

This module validates that:
- CLI flags are parsed into `RunConfig` as expected
- `run_command` wires parsed flags into `main_async`
- `main_async` forwards factory kwargs to `create_fetcher_config`
- AWS profile flags/env are respected by credentials and storage components
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from data_fetcher_app.cli_config import create_run_config
from data_fetcher_app.main import main_async, run_command
from data_fetcher_core.credentials.aws import AWSSecretsCredentialProvider
from data_fetcher_core.notifications.sqs_publisher import SqsPublisher
from data_fetcher_core.storage.pipeline_storage import PipelineStorage


class TestCliParsing:
    """Validate CLI parsing into RunConfig fields."""

    def test_run_config_parses_all_new_flags(self) -> None:
        args = [
            "--aws-profile",
            "global-prof",
            "--credentials-aws-profile",
            "cred-prof",
            "--credentials-aws-region",
            "eu-west-1",
            "--credentials-aws-endpoint-url",
            "http://localhost:4566",
            "--credentials-env-prefix",
            "MY_CRED_",
            "--storage-pipeline-aws-profile",
            "stor-prof",
            "--storage-s3-bucket",
            "my-bkt",
            "--storage-s3-prefix",
            "pre/",
            "--storage-s3-region",
            "us-east-1",
            "--storage-s3-endpoint-url",
            "http://s3.local",
            "--storage-file-path",
            "./data",
            "--storage-use-unzip",
            "--kvstore-serializer",
            "pickle",
            "--kvstore-default-ttl",
            "1234",
            "--kvstore-redis-host",
            "rhost",
            "--kvstore-redis-port",
            "6380",
            "--kvstore-redis-db",
            "2",
            "--kvstore-redis-password",
            "secret",
            "--kvstore-redis-key-prefix",
            "kp_",
        ]

        # recipe id is positional in run_command, but for create_run_config we pass only flags
        config = create_run_config(args)

        assert config.aws_profile == "global-prof"
        assert config.credentials_aws_profile == "cred-prof"
        assert config.credentials_aws_region == "eu-west-1"
        assert config.credentials_aws_endpoint_url == "http://localhost:4566"
        assert config.credentials_env_prefix == "MY_CRED_"

        assert config.storage_pipeline_aws_profile == "stor-prof"
        assert config.storage_s3_bucket == "my-bkt"
        assert config.storage_s3_prefix == "pre/"
        assert config.storage_s3_region == "us-east-1"
        assert config.storage_s3_endpoint_url == "http://s3.local"
        assert config.storage_file_path == "./data"
        assert config.storage_use_unzip is True

        assert config.kvstore_serializer == "pickle"
        assert config.kvstore_default_ttl == 1234
        assert config.kvstore_redis_host == "rhost"
        assert config.kvstore_redis_port == 6380
        assert config.kvstore_redis_db == 2
        assert config.kvstore_redis_password == "secret"
        assert config.kvstore_redis_key_prefix == "kp_"


class TestRunCommandWiring:
    """Validate that run_command passes parsed args to main_async via asyncio.run."""

    @patch("data_fetcher_app.main.asyncio.run")
    def test_run_command_builds_args_and_invokes_main_async(self, run_mock: MagicMock) -> None:
        # Provide minimal args: recipe id then flags
        args = [
            "us-fl",
            "--aws-profile",
            "corp",
            "--storage-s3-bucket",
            "b",
        ]

        run_command(args)

        assert run_mock.call_count == 1
        called = run_mock.call_args[0][0]
        # Ensure it is a coroutine function call to main_async with expected dict
        # We can't easily introspect coroutine args here; instead, check that environment was set
        assert os.environ.get("AWS_PROFILE") == "corp"


class TestMainAsyncFactoryForwarding:
    """Validate that main_async forwards factory kwargs to create_fetcher_config."""

    @pytest.mark.asyncio
    async def test_main_async_passes_factory_kwargs(self) -> None:
        args: dict[str, Any] = {
            "config_name": "us-fl",
            "credentials_provider": "aws",
            "storage": "s3",
            "kvstore": "redis",
            "run_id": "rid",
            "factory_kwargs": {
                "s3_bucket": "buck",
                "s3_prefix": "pre/",
                "redis_host": "rh",
            },
        }

        with patch("data_fetcher_app.main.create_fetcher_config", autospec=True) as cfc:
            # Set a minimal return to allow code to proceed until fetcher init, which we will fail fast after
            cfc.return_value = MagicMock()

            with patch("data_fetcher_app.main.get_fetcher", side_effect=KeyError()):
                with pytest.raises(KeyError):
                    await main_async(args)

            # Verify forwarding of kwargs
            kwargs = cfc.call_args.kwargs
            assert kwargs["s3_bucket"] == "buck"
            assert kwargs["s3_prefix"] == "pre/"
            assert kwargs["redis_host"] == "rh"


class TestAwsProfilePropagation:
    """Validate that AWS profile envs are honored by components."""

    @patch("boto3.session.Session", autospec=True)
    def test_credentials_uses_component_profile_first(self, sess_mock: MagicMock) -> None:
        with patch.dict(os.environ, {
            "OC_CREDENTIAL_PROVIDER_AWS_PROFILE": "cred-prof",
            "AWS_PROFILE": "global-prof",
        }, clear=True):
            provider = AWSSecretsCredentialProvider(region="eu-west-2")

            # Arrange fake client and response to avoid AWS calls
            fake_client = MagicMock()
            fake_client.get_secret_value.return_value = {"SecretString": '{"username":"u"}'}
            instance = MagicMock()
            instance.client.return_value = fake_client
            sess_mock.return_value = instance

            # Trigger call path that constructs session
            # We expect a ValueError for missing key; that's okay, we just want session creation
            with pytest.raises(ValueError):
                # secret will not contain requested key and raise
                provider.get_credential.__wrapped__(provider, "us-fl", "password")  # type: ignore[attr-defined]

            # Verify profile preference
            assert sess_mock.call_args.kwargs.get("profile_name") == "cred-prof"

    @patch("boto3.session.Session", autospec=True)
    def test_credentials_falls_back_to_global_profile(self, sess_mock: MagicMock) -> None:
        with patch.dict(os.environ, {"AWS_PROFILE": "global-prof"}, clear=True):
            provider = AWSSecretsCredentialProvider(region="eu-west-2")
            fake_client = MagicMock()
            fake_client.get_secret_value.return_value = {"SecretString": '{"username":"u"}'}
            instance = MagicMock()
            instance.client.return_value = fake_client
            sess_mock.return_value = instance

            with pytest.raises(ValueError):
                provider.get_credential.__wrapped__(provider, "us-fl", "password")  # type: ignore[attr-defined]

            assert sess_mock.call_args.kwargs.get("profile_name") == "global-prof"

    @patch("boto3.session.Session", autospec=True)
    def test_pipeline_storage_uses_profile(self, sess_mock: MagicMock) -> None:
        with patch.dict(os.environ, {
            "OC_STORAGE_PIPELINE_AWS_PROFILE": "stor-prof",
            # No endpoint URL so we avoid LocalStack credentials path
        }, clear=True):
            # Construct with minimal args to avoid network
            storage = PipelineStorage(
                bucket_name="b",
                prefix="",
                region="eu-west-2",
                endpoint_url=None,
                sqs_publisher=MagicMock(),
            )

            # The session is created twice in PipelineStorage (__post_init__ and write path), at least assert first
            assert sess_mock.call_args.kwargs.get("profile_name") == "stor-prof"
            assert hasattr(storage, "s3_client")

    @patch("boto3.session.Session", autospec=True)
    def test_sqs_publisher_uses_profile(self, sess_mock: MagicMock) -> None:
        with patch.dict(os.environ, {
            "OC_STORAGE_PIPELINE_AWS_PROFILE": "stor-prof",
        }, clear=True):
            publisher = SqsPublisher(queue_url="http://example.com/queue", region="eu-west-2", endpoint_url=None)
            assert sess_mock.call_args.kwargs.get("profile_name") == "stor-prof"
            assert hasattr(publisher, "sqs_client")
