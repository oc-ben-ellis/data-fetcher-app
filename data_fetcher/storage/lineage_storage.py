"""OpenLineage integration storage implementation.

This module provides the LineageStorage class for storing data while recording
lineage metadata using the oc_lineage library. It tracks fetch events and
resource streams for data lineage purposes.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from ..core import BundleRef

# Mock oc_lineage library - replace with actual import when available
try:
    from oc_lineage.core.emitter import (  # type: ignore[import-not-found]
        DatasetInfo,
        EventType,
        LineageEmitter,
    )
    from returns.result import Failure  # type: ignore[import-not-found]

    OC_LINEAGE_AVAILABLE = True
except ImportError:
    # Mock classes for development/testing
    OC_LINEAGE_AVAILABLE = False

    class MockLineageEmitter:
        """Mock lineage emitter for development/testing."""

        @staticmethod
        def create(
            transport_type: str,
            job_name: str,
            job_namespace: str,
            run_id: str | None = None,
            transport_config: dict[str, Any] | None = None,
        ) -> "MockEmitter":
            """Mock create method that returns a mock emitter."""
            return MockEmitter()

    class MockEmitter:
        """Mock emitter that logs events instead of sending them."""

        def emit_event(
            self,
            event_type: str,
            inputs: list[Any] | None = None,
            outputs: list[Any] | None = None,
        ) -> None:
            """Mock emit_event that logs the event."""
            print(f"[MOCK] Emitting {event_type} event:")
            if inputs:
                print(f"  Inputs: {inputs}")
            if outputs:
                print(f"  Outputs: {outputs}")

    class MockDatasetInfo:
        """Mock dataset info for development/testing."""

        def __init__(self, namespace: str, name: str) -> None:
            """Initialize the mock dataset info.

            Args:
                namespace: The namespace for the dataset.
                name: The name of the dataset.
            """
            self.namespace = namespace
            self.name = name

        def __repr__(self) -> str:
            """Return string representation of the dataset info.

            Returns:
                String representation in the format 'DatasetInfo(namespace='...', name='...')'.
            """
            return f"DatasetInfo(namespace='{self.namespace}', name='{self.name}')"

    class MockEventType:
        """Mock event types for development/testing."""

        START = "START"
        COMPLETE = "COMPLETE"
        FAIL = "FAIL"

    # Use mock classes
    LineageEmitter = MockLineageEmitter
    DatasetInfo = MockDatasetInfo
    EventType = MockEventType
    Failure = type("MockFailure", (), {"failure": lambda self: "Mock failure"})


@dataclass
class LineageStorage:
    """Lineage-aware storage implementation that records metadata and events."""

    base_storage: Any
    job_name: str = "data-fetcher"
    job_namespace: str = "data.fetcher"
    run_id: str | None = None
    transport_type: str = "console"
    transport_config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize the lineage storage and create lineage emitter."""
        # Generate run_id if not provided
        if self.run_id is None:
            import uuid

            self.run_id = str(uuid.uuid4())

        # Create lineage emitter
        emitter_config: dict[str, Any] = {
            "transport_type": self.transport_type,
            "job_name": self.job_name,
            "job_namespace": self.job_namespace,
            "run_id": self.run_id,
        }

        if self.transport_config:
            emitter_config["transport_config"] = self.transport_config

        res = LineageEmitter.create(**emitter_config)

        if OC_LINEAGE_AVAILABLE and isinstance(res, Failure):
            print(f"Failed to create lineage emitter: {res.failure()}")
            self.emitter = None
        else:
            self.emitter = res.unwrap() if OC_LINEAGE_AVAILABLE else res

    @asynccontextmanager
    async def open_bundle(
        self, bundle_ref: BundleRef
    ) -> AsyncGenerator["LineageBundle", None]:
        """Open a bundle for writing with lineage tracking."""
        bundle = LineageBundle(
            self.base_storage,
            bundle_ref,
            self.emitter,
            self.job_name,
            self.job_namespace,
            self.run_id or "",  # Ensure run_id is not None
        )
        try:
            yield bundle
        finally:
            await bundle.close()


class LineageBundle:
    """Lineage bundle for writing resources with metadata tracking."""

    def __init__(
        self,
        base_storage: Any,
        bundle_ref: BundleRef,
        emitter: Any,
        job_name: str,
        job_namespace: str,
        run_id: str,
    ) -> None:
        """Initialize the lineage bundle.

        Args:
            base_storage: The underlying storage to use.
            bundle_ref: Reference to the bundle being created.
            emitter: Lineage emitter for recording events.
            job_name: Name of the job for lineage tracking.
            job_namespace: Namespace for the job.
            run_id: Unique identifier for this run.
        """
        self.base_storage = base_storage
        self.bundle_ref = bundle_ref
        self.emitter = emitter
        self.job_name = job_name
        self.job_namespace = job_namespace
        self.run_id = run_id
        self.resources_written: list[dict[str, Any]] = []

        # Emit START event
        if self.emitter:
            inputs = [
                DatasetInfo(
                    namespace=self._extract_namespace(bundle_ref.primary_url),
                    name=self._extract_name(bundle_ref.primary_url),
                )
            ]
            self.emitter.emit_event(EventType.START, inputs=inputs)

    def _extract_namespace(self, url: str) -> str:
        """Extract namespace from URL for lineage tracking."""
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return f"{parsed.scheme}://{parsed.netloc}"
        elif parsed.scheme == "sftp":
            return f"sftp://{parsed.netloc}"
        else:
            return f"{parsed.scheme}://{parsed.netloc}"

    def _extract_name(self, url: str) -> str:
        """Extract name from URL for lineage tracking."""
        parsed = urlparse(url)
        path = parsed.path
        if not path or path == "/":
            return "index"

        # Remove leading slash and get filename
        path = path.lstrip("/")
        if "/" in path:
            path = path.split("/")[-1]

        return path or "index"

    async def write_resource(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Write a resource to storage while tracking lineage metadata."""
        # Write to base storage first
        if hasattr(self.base_storage, "open_bundle"):
            # If base_storage is a storage instance, use it directly
            async with self.base_storage.open_bundle(self.bundle_ref) as base_bundle:
                await base_bundle.write_resource(url, content_type, status_code, stream)
        else:
            # If base_storage is a bundle, use it directly
            await self.base_storage.write_resource(
                url, content_type, status_code, stream
            )

        # Track resource metadata for lineage
        resource_info: dict[str, Any] = {
            "url": url,
            "content_type": content_type,
            "status_code": status_code,
            "namespace": self._extract_namespace(url),
            "name": self._extract_name(url),
        }
        self.resources_written.append(resource_info)

    async def close(self) -> None:
        """Close the bundle and emit lineage completion event."""
        # Close base storage if needed
        if hasattr(self.base_storage, "close"):
            await self.base_storage.close()

        # Emit COMPLETE event with outputs
        if self.emitter:
            outputs = []
            for resource in self.resources_written:
                outputs.append(
                    DatasetInfo(namespace=resource["namespace"], name=resource["name"])
                )

            self.emitter.emit_event(EventType.COMPLETE, outputs=outputs)
