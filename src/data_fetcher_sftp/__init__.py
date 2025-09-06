"""Data Fetcher SFTP Package.

This package contains SFTP-specific classes and modules.
"""

from .sftp_credentials import SftpCredentials, SftpCredentialsWrapper

__all__ = [
    "SftpCredentials",
    "SftpCredentialsWrapper",
]
