"""Strategy factories for SFTP components.

This module provides strategy factories that can be registered with the
StrategyFactoryRegistry to enable YAML-based configuration loading.
"""

from dataclasses import asdict, dataclass, is_dataclass
from typing import Annotated, Any

from oc_pipeline_bus.strategy_registry import (
    InvalidArgumentStrategyException,
    StrategyFactory,
)

from data_fetcher_core.strategy_types import (
    FilterStrategyBase,
    FileSortStrategyBase,
    LoaderStrategy,
    LocatorStrategy,
)
from data_fetcher_sftp.sftp_bundle_locators import (
    DirectorySftpBundleLocator,
    FileSftpBundleLocator,
)
from data_fetcher_sftp.sftp_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_loader import SftpBundleLoader
from data_fetcher_sftp.sftp_manager import SftpManager


@dataclass
class SftpLoaderConfig:
    """Configuration for SFTP bundle loader."""

    meta_load_name: str
    # value is an alias like "us_fl" → resolve to filename via protocols.sftp.{value} → load into SftpProtocolConfig
    sftp_config: Annotated[
        SftpProtocolConfig, "path:protocols.sftp.{value}", "relative_config"
    ]


@dataclass
class SftpDirectoryLocatorConfig:
    """Configuration for SFTP directory bundle locator."""

    # Non-defaults first
    sftp_config: Annotated[
        SftpProtocolConfig, "path:protocols.sftp.{value}", "relative_config"
    ]
    remote_dir: str
    filename_pattern: str = "*"
    max_files: int | None = None
    file_filter: Annotated[FilterStrategyBase, "strategy"] = None
    file_sort: Annotated[FileSortStrategyBase, "strategy"] = None
    state_management_prefix: str = "sftp_directory_provider"


@dataclass
class SftpFileLocatorConfig:
    """Configuration for SFTP file bundle locator."""

    # Non-defaults first
    sftp_config: Annotated[
        SftpProtocolConfig, "path:protocols.sftp.{value}", "relative_config"
    ]
    file_paths: list[str]
    state_management_prefix: str = "sftp_file_provider"


class SftpBundleLoaderFactory(StrategyFactory):
    """Factory for creating SftpBundleLoader instances."""

    sftp_manager: SftpManager

    def __init__(self, sftp_manager: SftpManager) -> None:
        self.sftp_manager = sftp_manager

    def validate(self, params: Any) -> None:
        """Validate parameters for SftpBundleLoader creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        params_dict = asdict(params) if is_dataclass(params) else params

        required_fields = ["meta_load_name", "sftp_config"]

        for field in required_fields:
            if field not in params_dict:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    SftpBundleLoader,
                    "sftp_loader",
                    params,
                )

        if "sftp_config" not in params_dict:
            raise InvalidArgumentStrategyException(
                "sftp_config is required",
                SftpBundleLoader,
                "sftp_loader",
                params,
            )

    def create(self, params: Any) -> SftpBundleLoader:
        """Create an SftpBundleLoader instance.

        Args:
            params: Dictionary of parameters for loader creation (may be processed config object)

        Returns:
            Created SftpBundleLoader instance
        """
        # The sftp_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual SftpProtocolConfig object
        if is_dataclass(params):
            sftp_config = params.sftp_config
            meta_load_name = params.meta_load_name
        else:
            sftp_config = params["sftp_config"]
            meta_load_name = params["meta_load_name"]

        return SftpBundleLoader(
            sftp_manager=self.sftp_manager,
            sftp_config=sftp_config,
            meta_load_name=meta_load_name,
        )

    def get_config_type(self, params: dict[str, Any]) -> type | None:
        """Get the configuration type for further processing.

        Args:
            params: Dictionary of parameters that may contain nested configurations

        Returns:
            SftpLoaderConfig - for processing sftp_config relative config
        """
        return SftpLoaderConfig


class DirectorySftpBundleLocatorFactory(StrategyFactory):
    """Factory for creating DirectorySftpBundleLocator instances."""

    sftp_manager: SftpManager = None

    def __init__(self, sftp_manager: SftpManager) -> None:
        self.sftp_manager = sftp_manager

    def validate(self, params: Any) -> None:
        """Validate parameters for DirectorySftpBundleLocator creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        params_dict = asdict(params) if is_dataclass(params) else params

        required_fields = ["sftp_config", "remote_dir"]

        for field in required_fields:
            if field not in params_dict:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    DirectorySftpBundleLocator,
                    "directory_locator",
                    params,
                )

        if "sftp_config" not in params_dict:
            raise InvalidArgumentStrategyException(
                "sftp_config is required",
                DirectorySftpBundleLocator,
                "directory_locator",
                params,
            )

        if not isinstance(params_dict["remote_dir"], str):
            raise InvalidArgumentStrategyException(
                "remote_dir must be a string",
                DirectorySftpBundleLocator,
                "directory_locator",
                params,
            )

    def create(self, params: Any) -> DirectorySftpBundleLocator:
        """Create a DirectorySftpBundleLocator instance.

        Args:
            params: Dictionary of parameters for locator creation (may be processed config object)

        Returns:
            Created DirectorySftpBundleLocator instance
        """
        # The sftp_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual SftpProtocolConfig object
        if is_dataclass(params):
            sftp_config = params.sftp_config
            remote_dir = params.remote_dir
            filename_pattern = getattr(params, "filename_pattern", "*")
            max_files = getattr(params, "max_files", None)
            file_filter = getattr(params, "file_filter", None)
            file_sort = getattr(params, "file_sort", None)
            state_management_prefix = getattr(
                params, "state_management_prefix", "sftp_directory_provider"
            )
        else:
            sftp_config = params["sftp_config"]
            remote_dir = params["remote_dir"]
            filename_pattern = params.get("filename_pattern", "*")
            max_files = params.get("max_files")
            file_filter = params.get("file_filter")
            file_sort = params.get("file_sort")
            state_management_prefix = params.get(
                "state_management_prefix", "sftp_directory_provider"
            )

        return DirectorySftpBundleLocator(
            sftp_manager=self.sftp_manager,
            sftp_config=sftp_config,
            remote_dir=remote_dir,
            filename_pattern=filename_pattern,
            max_files=max_files,
            file_filter=file_filter,
            file_sort=file_sort,
            state_management_prefix=state_management_prefix,
        )

    def get_config_type(self, params: dict[str, Any]) -> type | None:
        """Get the configuration type for further processing.

        Args:
            params: Dictionary of parameters that may contain nested configurations

        Returns:
            SftpDirectoryLocatorConfig - for processing sftp_config relative config
        """
        return SftpDirectoryLocatorConfig


class FileSftpBundleLocatorFactory(StrategyFactory):
    """Factory for creating FileSftpBundleLocator instances."""

    sftp_manager: SftpManager = None

    def __init__(self, sftp_manager: SftpManager) -> None:
        self.sftp_manager = sftp_manager

    def validate(self, params: Any) -> None:
        """Validate parameters for FileSftpBundleLocator creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        params_dict = asdict(params) if is_dataclass(params) else params

        required_fields = ["sftp_config", "file_paths"]

        for field in required_fields:
            if field not in params_dict:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    FileSftpBundleLocator,
                    "file_locator",
                    params,
                )

        if "sftp_config" not in params_dict:
            raise InvalidArgumentStrategyException(
                "sftp_config is required",
                FileSftpBundleLocator,
                "file_locator",
                params,
            )

        if not isinstance(params_dict["file_paths"], list):
            raise InvalidArgumentStrategyException(
                "file_paths must be a list of strings",
                FileSftpBundleLocator,
                "file_locator",
                params,
            )

        for i, path in enumerate(params_dict["file_paths"]):
            if not isinstance(path, str):
                raise InvalidArgumentStrategyException(
                    f"file_paths[{i}] must be a string",
                    FileSftpBundleLocator,
                    "file_locator",
                    params,
                )

    def create(self, params: Any) -> FileSftpBundleLocator:
        """Create a FileSftpBundleLocator instance.

        Args:
            params: Dictionary of parameters for locator creation (may be processed config object)

        Returns:
            Created FileSftpBundleLocator instance
        """
        # The sftp_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual SftpProtocolConfig object
        if is_dataclass(params):
            sftp_config = params.sftp_config
            file_paths = params.file_paths
            state_management_prefix = getattr(
                params, "state_management_prefix", "sftp_file_provider"
            )
        else:
            sftp_config = params["sftp_config"]
            file_paths = params["file_paths"]
            state_management_prefix = params.get(
                "state_management_prefix", "sftp_file_provider"
            )

        return FileSftpBundleLocator(
            sftp_manager=self.sftp_manager,
            sftp_config=sftp_config,
            file_paths=file_paths,
            state_management_prefix=state_management_prefix,
        )

    def get_config_type(self, params: dict[str, Any]) -> type | None:
        """Get the configuration type for further processing.

        Args:
            params: Dictionary of parameters that may contain nested configurations

        Returns:
            SftpFileLocatorConfig - for processing sftp_config relative config
        """
        return SftpFileLocatorConfig


def register_sftp_strategies(registry, sftp_manager: SftpManager) -> None:
    """Register all SFTP strategy factories with the registry.

    Args:
        registry: StrategyFactoryRegistry instance to register with
    """
    # Register loader factory against base interface
    registry.register(
        LoaderStrategy, "sftp_loader", SftpBundleLoaderFactory(sftp_manager)
    )

    # Register locator factories
    registry.register(
        LocatorStrategy,
        "sftp_directory",
        DirectorySftpBundleLocatorFactory(sftp_manager),
    )

    registry.register(
        LocatorStrategy, "sftp_file", FileSftpBundleLocatorFactory(sftp_manager)
    )

    # Register file sort strategies
    registry.register(FileSortStrategyBase, "mtime", ModifiedTimeFileSortStrategyFactory())
    registry.register(FileSortStrategyBase, "lex", LexicographicalFileSortStrategyFactory())
    # Register file filter strategies
    registry.register(FilterStrategyBase, "date_filter", DateFilterStrategyFactory())


# ----------------------
# File Sort Strategies
# ----------------------


class ModifiedTimeFileSortStrategy(FileSortStrategyBase):
    """Sort files by modification time.

    Ascending (oldest first) by default. Set `reverse: true` to get descending (newest first).
    """

    def __init__(self, reverse: bool = False) -> None:
        self._reverse = reverse

    def sort(self, items: list[tuple[str, float | int | None]]) -> list[tuple[str, float | int | None]]:
        # None mtimes go last in ascending, last in descending as well for stability
        def key_fn(item: tuple[str, float | int | None]) -> tuple[int, float]:
            path, mtime = item
            is_none = 1 if mtime is None else 0
            mt = float(mtime or 0.0)
            return (is_none, mt)

        return sorted(items, key=key_fn, reverse=self._reverse)


class ModifiedTimeFileSortStrategyFactory(StrategyFactory):
    """Factory for ModifiedTimeFileSortStrategy.

    Accepts optional parameter `descending` in params for completeness, but the
    registry registration typically fixes this via constructor wiring.
    """

    def __init__(self) -> None:
        ...

    def validate(self, params: Any) -> None:  # noqa: D401
        # No required parameters
        return

    def create(self, params: Any) -> ModifiedTimeFileSortStrategy:
        # Accept optional reverse flag, defaults to ascending (False)
        if is_dataclass(params):
            reverse = bool(getattr(params, "reverse", False))
        elif isinstance(params, dict):
            reverse = bool(params.get("reverse", False))
        else:
            reverse = False
        return ModifiedTimeFileSortStrategy(reverse=reverse)

    def get_config_type(self, params: Any) -> type | None:  # noqa: D401
        # Return dataclass type for nested processing
        return MtimeSortConfig


class LexicographicalFileSortStrategy(FileSortStrategyBase):
    """Sort files lexicographically by their path.

    Ascending by default. Set `reverse: true` to get descending order.
    """

    def __init__(self, reverse: bool = False) -> None:
        self._reverse = reverse

    def sort(self, items: list[tuple[str, float | int | None]]) -> list[tuple[str, float | int | None]]:
        return sorted(items, key=lambda x: (x[0] is None, x[0]), reverse=self._reverse)


class LexicographicalFileSortStrategyFactory(StrategyFactory):
    """Factory for LexicographicalFileSortStrategy."""

    def validate(self, params: Any) -> None:  # noqa: D401
        # No required params
        return

    def create(self, params: Any) -> LexicographicalFileSortStrategy:
        if is_dataclass(params):
            reverse = bool(getattr(params, "reverse", False))
        elif isinstance(params, dict):
            reverse = bool(params.get("reverse", False))
        else:
            reverse = False
        return LexicographicalFileSortStrategy(reverse=reverse)

    def get_config_type(self, params: Any) -> type | None:  # noqa: D401
        # Return dataclass type for nested processing
        return LexSortConfig


# ----------------------
# File Filter Strategies
# ----------------------


class DateFilterStrategy(FilterStrategyBase):
    """Filter files based on a minimum date embedded in the filename.

    Supports simple patterns like 'YYYYMMDD'. The strategy compares the
    extracted date string lexicographically to `start_date`.
    """

    def __init__(self, start_date: str, date_pattern: str = "YYYYMMDD") -> None:
        self._start_date = start_date
        self._pattern = date_pattern.upper()

    def filter(self, data: Any) -> bool:
        # Expect data to be a filename
        name = str(data)
        if self._pattern == "YYYYMMDD":
            # Find first 8-digit sequence and compare
            digits = []
            for ch in name:
                if ch.isdigit():
                    digits.append(ch)
                    if len(digits) == 8:
                        break
                else:
                    # reset if we break a contiguous block
                    if digits:
                        digits = []
            if len(digits) != 8:
                return False
            date_str = "".join(digits)
            return date_str >= self._start_date
        # Unknown pattern: be conservative
        return False


class DateFilterStrategyFactory(StrategyFactory):
    """Factory for DateFilterStrategy."""

    def validate(self, params: Any) -> None:  # noqa: D401
        # Require start_date; date_pattern optional
        if is_dataclass(params):
            if not getattr(params, "start_date", None):
                raise InvalidArgumentStrategyException(
                    "Missing required parameter: start_date",
                    DateFilterStrategy,
                    "date_filter",
                    params,
                )
        elif isinstance(params, dict):
            if "start_date" not in params:
                raise InvalidArgumentStrategyException(
                    "Missing required parameter: start_date",
                    DateFilterStrategy,
                    "date_filter",
                    params,
                )
        return

    def create(self, params: Any) -> DateFilterStrategy:
        if is_dataclass(params):
            start_date = str(getattr(params, "start_date"))
            date_pattern = str(getattr(params, "date_pattern", "YYYYMMDD"))
        elif isinstance(params, dict):
            start_date = str(params.get("start_date"))
            date_pattern = str(params.get("date_pattern", "YYYYMMDD"))
        else:
            # Fallback defaults
            start_date = "00000000"
            date_pattern = "YYYYMMDD"
        return DateFilterStrategy(start_date=start_date, date_pattern=date_pattern)

    def get_config_type(self, params: Any) -> type | None:  # noqa: D401
        # Return dataclass type for nested processing
        return DateFilterConfig


# ----------------------
# Dataclass configs for strategy processing
# ----------------------


@dataclass
class MtimeSortConfig:
    reverse: bool = False


@dataclass
class LexSortConfig:
    reverse: bool = False


@dataclass
class DateFilterConfig:
    start_date: str
    date_pattern: str = "YYYYMMDD"
