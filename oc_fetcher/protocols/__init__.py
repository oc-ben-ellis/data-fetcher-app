"""Protocol-specific managers and implementations.

This module provides protocol managers for different communication protocols,
including HTTP, SFTP, and authentication handling.
"""

from .authentication import (
    AuthenticationMechanism,
    BasicAuthenticationMechanism,
    BearerTokenAuthenticationMechanism,
    NoAuthenticationMechanism,
    OAuthAuthenticationMechanism,
)
from .http_manager import HttpManager
from .sftp_manager import OncePerIntervalGate, ScheduledDailyGate, SftpManager

__all__ = [
    "AuthenticationMechanism",
    "BasicAuthenticationMechanism",
    "BearerTokenAuthenticationMechanism",
    "NoAuthenticationMechanism",
    "OAuthAuthenticationMechanism",
    "HttpManager",
    "SftpManager",
    "ScheduledDailyGate",
    "OncePerIntervalGate",
]
