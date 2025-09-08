"""Environment variable credential provider.

This module provides the EnvironmentCredentialProvider class for retrieving
credentials from environment variables, useful for development and testing.
"""

import os


class EnvironmentCredentialProvider:
    """Credential provider that fetches credentials from environment variables."""

    def __init__(self, prefix: str = "") -> None:
        """Initialize the environment credential provider.

        Args:
            prefix: Optional prefix to add to environment variable names.
        """
        self.prefix = prefix
        self._requested_vars: list[str] = []

    async def get_credential(self, config_name: str, config_key: str) -> str:
        """Get credential from environment variable.

        The environment variable name is expected to be in the format:
        {prefix}{config_name.upper()}_{config_key.upper()}

        Args:
            config_name: Configuration name (e.g., 'us-fl', 'fr').
            config_key: Credential key (e.g., 'username', 'password', 'host').

        Returns:
            The credential value from the environment variable.

        Raises:
            ValueError: When the required environment variable is not set.
                The error message includes the exact variable name and all
                previously requested variables for debugging.
        """
        env_var_name = (
            f"{self.prefix}{config_name.upper().replace('-', '_')}_{config_key.upper()}"
        )

        # Track requested variables for better error reporting
        if env_var_name not in self._requested_vars:
            self._requested_vars.append(env_var_name)

        value = os.getenv(env_var_name)
        if value is None:
            # Provide detailed error message with all requested variables
            missing_vars = [
                var for var in self._requested_vars if os.getenv(var) is None
            ]
            error_msg = (
                f"Environment variable '{env_var_name}' not found. "
                f"Please set the following environment variables:\n"
                f"  {env_var_name}\n"
            )

            if len(missing_vars) > 1:
                error_msg += "\nOther missing environment variables:\n"
                for var in missing_vars:
                    if var != env_var_name:
                        error_msg += f"  {var}\n"

            error_msg += (
                f"\nEnvironment variable format: {self.prefix}{config_name.upper()}_{config_key.upper()}\n"
                f"Example: For config 'us-fl' and key 'username', set: {self.prefix}US_FL_USERNAME"
            )

            raise ValueError(error_msg)

        return value

    def clear(self) -> None:
        """Clear any cached credentials and requested variables tracking."""
        self._requested_vars.clear()

    def get_missing_variables(self) -> list[str]:
        """Get list of environment variables that were requested but not found.

        Returns:
            List of environment variable names that are missing.
        """
        return [var for var in self._requested_vars if os.getenv(var) is None]

    def get_requested_variables(self) -> list[str]:
        """Get list of all environment variables that were requested.

        Returns:
            List of all environment variable names that were requested.
        """
        return self._requested_vars.copy()
