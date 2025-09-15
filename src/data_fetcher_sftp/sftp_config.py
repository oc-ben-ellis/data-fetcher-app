"""SFTP protocol configuration class.

This module contains the SFTP-specific `SftpProtocolConfig` used by SFTP loaders
and managers to configure connection behavior.
"""

from dataclasses import dataclass

from data_fetcher_core.core import ProtocolConfig


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
