"""Factory functions for creating HTTP components.

This module provides factory functions to create and configure HTTP
components including protocol configurations and managers.
"""

from data_fetcher_core.protocol_config import HttpProtocolConfig
from data_fetcher_http.http_manager import HttpManager
from data_fetcher_sftp.authentication import AuthenticationMechanism


def create_http_protocol_config(
    timeout: float = 30.0,
    rate_limit_requests_per_second: float = 10.0,
    max_retries: int = 3,
    default_headers: dict[str, str] | None = None,
    authentication_mechanism: AuthenticationMechanism | None = None,
) -> HttpProtocolConfig:
    """Create an HTTP protocol configuration with the given settings.

    Args:
        timeout: Request timeout in seconds. Defaults to 30.0.
        rate_limit_requests_per_second: Rate limit for requests per second. Defaults to 10.0.
        max_retries: Maximum number of retries. Defaults to 3.
        default_headers: Default HTTP headers. Defaults to None.
        authentication_mechanism: Authentication mechanism. Defaults to None.

    Returns:
        Configured HttpProtocolConfig instance.
    """
    return HttpProtocolConfig(
        timeout=timeout,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        max_retries=max_retries,
        default_headers=default_headers,
        authentication_mechanism=authentication_mechanism,
    )


def create_http_manager() -> HttpManager:
    """Create an HTTP manager instance.

    Returns:
        New HttpManager instance.
    """
    return HttpManager()
