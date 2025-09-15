"""HTTP protocol configuration class.

This module contains the HTTP-specific `HttpProtocolConfig` used by HTTP loaders
and managers to configure connection behavior.
"""

from dataclasses import dataclass

from data_fetcher_core.core import ProtocolConfig
from data_fetcher_sftp.authentication import AuthenticationMechanism


@dataclass
class HttpProtocolConfig(ProtocolConfig):
    """HTTP protocol configuration.

    Contains all the settings needed to configure HTTP connections,
    including timeouts, rate limiting, authentication, and headers.
    """

    timeout: float = 30.0
    default_headers: dict[str, str] | None = None
    rate_limit_requests_per_second: float = 10.0
    max_retries: int = 3
    authentication_mechanism: AuthenticationMechanism | None = None

    def __post_init__(self) -> None:
        """Initialize default values if not provided."""
        if self.default_headers is None:
            self.default_headers = {"User-Agent": "OCFetcher/1.0"}

    def get_connection_key(self) -> str:
        """Get a unique key for this HTTP configuration.

        The key is based on the configuration parameters that affect
        connection behavior, excluding runtime-specific values.
        """
        # Create a hashable representation of the configuration
        auth_key = ""
        if self.authentication_mechanism:
            auth_key = f"auth_{id(self.authentication_mechanism)}"

        headers_key = ""
        if self.default_headers:
            # Sort headers for consistent key generation
            sorted_headers = sorted(self.default_headers.items())
            headers_key = f"headers_{hash(tuple(sorted_headers))}"

        return f"http_{self.timeout}_{self.rate_limit_requests_per_second}_{self.max_retries}_{auth_key}_{headers_key}"

    def get_protocol_type(self) -> str:
        """Get the HTTP protocol type identifier."""
        return "http"
