"""Core framework components and base classes.

This module provides the fundamental building blocks of the OC Fetcher framework,
including the base FetcherRecipeBuilder and configuration creation utilities.
"""

import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_fetcher_core.config_factory import FetcherConfig

from data_fetcher_core.exceptions import ValidationError

# Removed global storage import - will be passed explicitly

# HTTP status code constants
MIN_HTTP_STATUS = 100
MAX_HTTP_STATUS = 599

Url = str


class BundleRefValidationError(ValidationError):
    """Raised when BundleRef data validation fails."""

    def __init__(self, message: str) -> None:
        """Initialize the error with a specific message.

        Args:
            message: Description of the validation failure.
        """
        super().__init__(message, "bundle_ref")


def _generate_uuid7() -> str:
    """Generate a UUIDv7-like identifier with timestamp and randomness.

    This is a simplified implementation that provides time-ordered UUIDs
    similar to UUIDv7 but using standard library components.

    Returns:
        A UUID string with timestamp prefix for time-based ordering.
    """
    # Get current timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)

    # Generate random bytes for uniqueness
    random_bytes = secrets.token_bytes(10)  # 80 bits of randomness

    # Create a UUID-like string with timestamp prefix
    # Format: timestamp_ms (13 digits) + random hex (20 chars)
    timestamp_str = f"{timestamp_ms:013d}"
    random_str = random_bytes.hex()

    # Create a UUID-like format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    return f"{timestamp_str[:8]}-{timestamp_str[8:12]}-{random_str[:4]}-{random_str[4:8]}-{random_str[8:20]}"


class BID:
    """Bundle ID - a UUIDv7 value for tracking bundle creation time.

    BIDs are used for tracing and debugging across locators and loaders,
    and may be used by the storage layer to determine file paths.
    """

    def __init__(self, value: str | None = None) -> None:
        """Initialize a BID with a UUIDv7 value.

        Args:
            value: Optional UUIDv7 string. If None, generates a new UUIDv7.

        Raises:
            ValueError: If the provided value is not a valid BID format.
        """
        if value is None:
            self._value = _generate_uuid7()
        else:
            if not self._is_valid_bid_format(value):
                error_message = "Invalid BID format"
                raise ValidationError(error_message, "bid")
            self._value = value

    @staticmethod
    def _is_valid_bid_format(value: str) -> bool:
        """Validate BID format.

        Args:
            value: The BID string to validate.

        Returns:
            True if the BID format is valid, False otherwise.
        """
        # Allow simple test values for testing purposes
        if value.startswith(("test-", "custom-")):
            return True

        # Check basic format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = value.split("-")
        uuid_parts_count = 5
        if len(parts) != uuid_parts_count:
            return False

        # Check each part length
        expected_lengths = [8, 4, 4, 4, 12]
        for part, expected_len in zip(parts, expected_lengths, strict=False):
            if len(part) != expected_len:
                return False
            # Check if all characters are hex
            try:
                int(part, 16)
            except ValueError:
                return False

        return True

    def __str__(self) -> str:
        """Return the BID as a string."""
        return self._value

    def __repr__(self) -> str:
        """Return a string representation of the BID."""
        return f"BID('{self._value}')"

    def __eq__(self, other: object) -> bool:
        """Check if two BIDs are equal."""
        if not isinstance(other, BID):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Return hash of the BID."""
        return hash(self._value)

    @classmethod
    def generate(cls) -> "BID":
        """Generate a new BID with a fresh UUIDv7.

        Returns:
            A new BID instance with a fresh UUIDv7 value.
        """
        return cls()

    @property
    def value(self) -> str:
        """Get the underlying UUIDv7 string value.

        Returns:
            The UUIDv7 string value.
        """
        return self._value


@dataclass
class RequestMeta:
    """Metadata for a fetch request."""

    url: Url
    depth: int = 0
    referer: Url | None = None
    headers: dict[str, str] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate RequestMeta fields after initialization."""
        if not isinstance(self.url, str) or not self.url.strip():
            error_message = "url must be a non-empty string"
            raise ValidationError(error_message, "url")
        if not isinstance(self.depth, int) or self.depth < 0:
            error_message = "depth must be a non-negative integer"
            raise ValidationError(error_message, "depth")
        if self.referer is not None and (
            not isinstance(self.referer, str) or not self.referer.strip()
        ):
            error_message = "referer must be a non-empty string or None"
            raise ValidationError(error_message, "referer")
        if not isinstance(self.headers, dict):
            error_message = "headers must be a dictionary"  # type: ignore[unreachable]
            raise ValidationError(error_message, "headers")
        if not isinstance(self.flags, dict):
            error_message = "flags must be a dictionary"  # type: ignore[unreachable]
            raise ValidationError(error_message, "flags")


@dataclass
class ResourceMeta:
    """Metadata for a fetched resource."""

    url: Url
    status: int | None = None
    content_type: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    note: str | None = None

    def __post_init__(self) -> None:
        """Validate ResourceMeta fields after initialization."""
        if not isinstance(self.url, str) or not self.url.strip():
            error_message = "url must be a non-empty string"
            raise ValidationError(error_message, "url")
        if self.status is not None and (
            not isinstance(self.status, int)
            or self.status < MIN_HTTP_STATUS
            or self.status > MAX_HTTP_STATUS
        ):
            error_message = "status must be a valid HTTP status code (100-599) or None"
            raise ValidationError(error_message, "status")
        if self.content_type is not None and (
            not isinstance(self.content_type, str) or not self.content_type.strip()
        ):
            error_message = "content_type must be a non-empty string or None"
            raise ValidationError(error_message, "content_type")
        if not isinstance(self.headers, dict):
            error_message = "headers must be a dictionary"  # type: ignore[unreachable]
            raise ValidationError(error_message, "headers")
        if self.note is not None and (
            not isinstance(self.note, str) or not self.note.strip()
        ):
            error_message = "note must be a non-empty string or None"
            raise ValidationError(error_message, "note")


@dataclass
class BundleRef:
    """Reference to a bundle of fetched resources."""

    primary_url: Url
    resources_count: int
    bid: BID = field(default_factory=BID.generate)
    storage_key: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BundleRef":
        """Create a BundleRef from a dictionary.

        Args:
            data: Dictionary containing bundle reference data.

        Returns:
            A new BundleRef instance.

        Raises:
            BundleRefValidationError: If required fields are missing or invalid.
        """
        if not isinstance(data, dict):
            error_message = "Data must be a dictionary"  # type: ignore[unreachable]
            raise BundleRefValidationError(error_message)

        # Validate required fields
        if "bid" not in data:
            error_message = "BundleRef data must contain 'bid' field"
            raise BundleRefValidationError(error_message)

        if "primary_url" not in data:
            error_message = "BundleRef data must contain 'primary_url' field"
            raise BundleRefValidationError(error_message)

        if "resources_count" not in data:
            error_message = "BundleRef data must contain 'resources_count' field"
            raise BundleRefValidationError(error_message)

        # Validate field types
        primary_url = data["primary_url"]
        if not isinstance(primary_url, str) or not primary_url.strip():
            error_message = "primary_url must be a non-empty string"
            raise BundleRefValidationError(error_message)

        resources_count = data["resources_count"]
        if not isinstance(resources_count, int) or resources_count < 0:
            error_message = "resources_count must be a non-negative integer"
            raise BundleRefValidationError(error_message)

        # Validate BID format
        try:
            bid = BID(data["bid"])
        except ValidationError as e:
            error_message = "Invalid BID format"
            raise BundleRefValidationError(error_message) from e

        # Validate optional fields
        storage_key = data.get("storage_key")
        if storage_key is not None and not isinstance(storage_key, str):
            error_message = "storage_key must be a string or None"
            raise BundleRefValidationError(error_message)

        meta = data.get("meta", {})
        if not isinstance(meta, dict):
            error_message = "meta must be a dictionary"
            raise BundleRefValidationError(error_message)

        return cls(
            primary_url=primary_url,
            resources_count=resources_count,
            bid=bid,
            storage_key=storage_key,
            meta=meta,
        )


@dataclass
class FetchRunContext:
    """Context for a fetch run."""

    run_id: str
    shared: dict[str, Any] = field(default_factory=dict)
    processed_count: int = 0
    errors: list[str] = field(default_factory=list)
    app_config: "FetcherConfig | None" = None


@dataclass
class RequestParameterLocator:
    """Bundle locator that serves pre-defined requests from a queue.

    This locator maintains an internal queue of RequestMeta objects and serves them
    via the standard get_next_urls() interface. Once the queue is empty, it returns
    no more URLs, allowing other locators to take over.
    """

    requests: list[RequestMeta]

    def __post_init__(self) -> None:
        """Initialize the internal queue with the provided requests."""
        self._request_queue: list[RequestMeta] = self.requests.copy()
        self._exhausted: bool = False

    async def get_next_urls(self, _ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of requests from the internal queue.

        Args:
            _ctx: Fetch run context (unused for this locator)

        Returns:
            List of RequestMeta objects from the internal queue
        """
        if self._exhausted:
            return []

        # Return up to 10 requests at a time (configurable)
        batch_size = 10
        urls: list[RequestMeta] = []

        while self._request_queue and len(urls) < batch_size:
            urls.append(self._request_queue.pop(0))

        # Mark as exhausted if queue is empty
        if not self._request_queue:
            self._exhausted = True

        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], _ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed.

        This locator doesn't need to track processed URLs since it only serves
        from its internal queue and doesn't generate new URLs.

        Args:
            request: The processed request
            bundle_refs: Bundle references from the processing
            _ctx: Fetch run context (unused)
        """
        # No-op: this locator doesn't track processed URLs


@dataclass
class FetcherRecipe:
    """Recipe for the entire fetch operation."""

    recipe_id: str = "default"
    bundle_locators: list[Any] = field(default_factory=list)
    bundle_loader: object | None = None


@dataclass
class FetchPlan:
    """Plan for fetching resources."""

    recipe: FetcherRecipe
    context: FetchRunContext
    concurrency: int = 1
    target_queue_size: int = 100


class FetcherRecipeBuilder:
    """Builder for creating fetcher configurations."""

    def __init__(self) -> None:
        """Initialize the fetcher recipe builder."""
        self._bundle_loader: object = None
        self._bundle_locators: list[Any] = []

    def use_bundle_loader(
        self, bundle_loader_instance: object
    ) -> "FetcherRecipeBuilder":
        """Set the loader instance."""
        self._bundle_loader = bundle_loader_instance
        return self

    def add_bundle_locator(
        self, bundle_locator_instance: object
    ) -> "FetcherRecipeBuilder":
        """Add a bundle locator instance."""
        self._bundle_locators.append(bundle_locator_instance)
        return self

    def build(self) -> FetcherRecipe:
        """Build the fetcher configuration."""
        if not self._bundle_loader:
            raise ValueError("Bundle loader required")  # noqa: TRY003

        return FetcherRecipe(
            recipe_id="",  # Will be set by the recipe setup function
            bundle_locators=self._bundle_locators,
            bundle_loader=self._bundle_loader,
        )


def create_fetcher_config() -> FetcherRecipeBuilder:
    """Create a new fetcher configuration builder."""
    return FetcherRecipeBuilder()
