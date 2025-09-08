"""Protocol configuration classes for different communication protocols.

This module provides base protocol configuration classes and specific implementations
for HTTP and SFTP protocols. These configurations are used to manage connection pools
and protocol-specific settings.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from data_fetcher_sftp.authentication import AuthenticationMechanism


@dataclass
class ProtocolConfig(ABC):
    """Base class for protocol-specific configurations.

    This abstract base class defines the interface that all protocol configurations
    must implement. Each protocol configuration contains the settings needed to
    establish and manage connections for that specific protocol.
    """

    @abstractmethod
    def get_connection_key(self) -> str:
        """Get a unique key for this configuration.

        This key is used to identify and reuse connection pools that match
        this configuration. Configurations with the same key will share
        the same connection pool.

        Returns:
            A unique string identifier for this configuration.
        """

    @abstractmethod
    def get_protocol_type(self) -> str:
        """Get the protocol type identifier.

        Returns:
            A string identifying the protocol type (e.g., 'http', 'sftp').
        """


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


@dataclass
class SftpProtocolConfig(ProtocolConfig):
    """SFTP protocol configuration.

    Contains all the settings needed to configure SFTP connections,
    including timeouts, rate limiting, and connection parameters.
    """

    config_name: str
    connect_timeout: float = 20.0
    rate_limit_requests_per_second: float = 5.0
    max_retries: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    retry_exponential_base: float = 2.0

    def get_connection_key(self) -> str:
        """Get a unique key for this SFTP configuration.

        The key is based on the configuration name and connection parameters
        that affect connection behavior.
        """
        return f"sftp_{self.config_name}_{self.connect_timeout}_{self.rate_limit_requests_per_second}_{self.max_retries}"

    def get_protocol_type(self) -> str:
        """Get the SFTP protocol type identifier."""
        return "sftp"
