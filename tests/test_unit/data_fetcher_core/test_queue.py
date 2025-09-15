"""Tests for persistent queue implementation.

This module contains unit tests for the persistent queue system,
including KVStoreQueue, serializers, and queue operations.
"""

import asyncio
from typing import Any

import pytest
from yarl import URL

# RequestMeta is dict-like in current implementation; use dicts in tests
from data_fetcher_core.exceptions import ConfigurationError
from data_fetcher_core.kv_store import KeyValueStore, create_kv_store
from data_fetcher_core.queue import (
    JSONSerializer,
    KVStoreQueue,
    RequestMetaSerializer,
)


class TestJSONSerializer:
    """Test JSONSerializer class."""

    def test_basic_serialization(self) -> None:
        """Test basic JSON serialization and deserialization."""
        serializer = JSONSerializer()

        # Test simple object
        obj = {"key": "value", "number": 42}
        serialized = serializer.dumps(obj)
        deserialized = serializer.loads(serialized)

        assert deserialized == obj

    def test_complex_serialization(self) -> None:
        """Test serialization of complex objects."""
        serializer = JSONSerializer()

        # Test object with various types
        obj = {
            "string": "test",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        }
        serialized = serializer.dumps(obj)
        deserialized = serializer.loads(serialized)

        assert deserialized == obj

    def test_non_json_serializable(self) -> None:
        """Test serialization of non-JSON serializable objects."""
        serializer = JSONSerializer()

        # Test with a set (not JSON serializable)
        obj = {"set": {1, 2, 3}}
        serializer.dumps(obj)
        # Should not raise an exception due to default=str


class TestRequestMetaSerializer:
    """Test RequestMetaSerializer class."""

    def test_request_meta_serialization(self) -> None:
        """Test RequestMeta serialization and deserialization."""
        serializer = RequestMetaSerializer()

        # Create a RequestMeta object
        request = {
            "url": str(URL("https://example.com")),
            "depth": 1,
            "referer": str(URL("https://referer.com")),
            "headers": {"User-Agent": "test"},
            "flags": {"test_flag": True},
        }

        # Serialize
        serialized = serializer.dumps(request)
        assert isinstance(serialized, str)

        # Deserialize
        deserialized = serializer.loads(serialized)
        assert isinstance(deserialized, dict)
        assert str(deserialized["url"]) == "https://example.com"
        assert deserialized["depth"] == 1
        assert str(deserialized["referer"]) == "https://referer.com"
        assert deserialized["headers"] == {"User-Agent": "test"}
        assert deserialized["flags"] == {"test_flag": True}

    def test_request_meta_with_minimal_fields(self) -> None:
        """Test RequestMeta serialization with minimal fields."""
        serializer = RequestMetaSerializer()

        # Create a minimal RequestMeta object
        request = {"url": str(URL("https://example.com"))}

        # Serialize and deserialize
        serialized = serializer.dumps(request)
        deserialized = serializer.loads(serialized)

        assert str(deserialized["url"]) == "https://example.com"
        assert deserialized["depth"] == 0  # default value
        assert deserialized["referer"] is None
        assert deserialized["headers"] == {}
        assert deserialized["flags"] == {}


class TestKVStoreQueue:
    """Test KVStoreQueue class."""

    @pytest.fixture
    def kv_store(self) -> Any:
        """Create a memory kv store for testing."""
        return create_kv_store(store_type="memory")

    @pytest.fixture
    def queue(self, kv_store: Any) -> KVStoreQueue:
        """Create a KVStoreQueue for testing."""
        return KVStoreQueue(
            kv_store=kv_store,
            namespace="test_queue",
            serializer=RequestMetaSerializer(),
        )

    @pytest.mark.asyncio
    async def test_basic_operations(self, queue: KVStoreQueue) -> None:
        """Test basic queue operations."""
        # Test empty queue
        assert await queue.size() == 0

        # Create test request
        request = {"url": str(URL("https://example.com"))}

        # Test enqueue
        enqueued = await queue.enqueue([request])
        assert enqueued == 1
        assert await queue.size() == 1

        # Test peek
        peeked = await queue.peek()
        assert len(peeked) == 1
        assert str(peeked[0]["url"]) == "https://example.com"
        assert await queue.size() == 1  # Size should not change

        # Test dequeue
        dequeued = await queue.dequeue()
        assert len(dequeued) == 1
        assert str(dequeued[0]["url"]) == "https://example.com"
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_multiple_items(self, queue: KVStoreQueue) -> None:
        """Test queue operations with multiple items."""
        # Create multiple requests
        requests = [{"url": str(URL(f"https://example.com/{i}"))} for i in range(5)]

        # Test enqueue multiple items
        enqueued = await queue.enqueue(requests)
        assert enqueued == 5
        assert await queue.size() == 5

        # Test dequeue multiple items
        dequeued = await queue.dequeue(max_items=3)
        assert len(dequeued) == 3
        assert await queue.size() == 2

        # Test dequeue remaining items
        dequeued = await queue.dequeue(max_items=10)  # More than available
        assert len(dequeued) == 2
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_empty_operations(self, queue: KVStoreQueue) -> None:
        """Test operations on empty queue."""
        # Test dequeue from empty queue
        dequeued = await queue.dequeue()
        assert len(dequeued) == 0

        # Test peek on empty queue
        peeked = await queue.peek()
        assert len(peeked) == 0

        # Test enqueue empty list
        enqueued = await queue.enqueue([])
        assert enqueued == 0

    @pytest.mark.asyncio
    async def test_clear_operation(self, queue: KVStoreQueue) -> None:
        """Test queue clear operation."""
        # Add some items
        requests = [
            {"url": str(URL(f"https://example.com/{i}"))} for i in range(3)
        ]
        await queue.enqueue(requests)
        assert await queue.size() == 3

        # Clear queue
        cleared = await queue.clear()
        assert cleared == 3
        assert await queue.size() == 0

        # Test clear on empty queue
        cleared = await queue.clear()
        assert cleared == 0

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, kv_store: KeyValueStore) -> None:
        """Test that different namespaces don't interfere."""
        queue1 = KVStoreQueue(
            kv_store=kv_store,
            namespace="namespace1",
            serializer=RequestMetaSerializer(),
        )
        queue2 = KVStoreQueue(
            kv_store=kv_store,
            namespace="namespace2",
            serializer=RequestMetaSerializer(),
        )

        # Add items to queue1
        request1 = {"url": str(URL("https://queue1.com"))}
        await queue1.enqueue([request1])
        assert await queue1.size() == 1
        assert await queue2.size() == 0

        # Add items to queue2
        request2 = {"url": str(URL("https://queue2.com"))}
        await queue2.enqueue([request2])
        assert await queue1.size() == 1
        assert await queue2.size() == 1

        # Dequeue from queue1
        dequeued1 = await queue1.dequeue()
        assert len(dequeued1) == 1
        assert str(dequeued1[0]["url"]) == "https://queue1.com"
        assert await queue1.size() == 0
        assert await queue2.size() == 1  # queue2 should be unaffected

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, queue: KVStoreQueue) -> None:
        """Test concurrent queue operations."""
        # Create multiple requests
        requests = [{"url": str(URL(f"https://example.com/{i}"))} for i in range(10)]

        # Enqueue all items concurrently
        await queue.enqueue(requests)
        assert await queue.size() == 10

        # Dequeue items concurrently
        async def dequeue_worker() -> int:
            dequeued = await queue.dequeue(max_items=2)
            return len(dequeued)

        # Run multiple dequeue operations concurrently
        results = await asyncio.gather(*[dequeue_worker() for _ in range(5)])

        # Should have dequeued all items
        total_dequeued = sum(results)
        assert total_dequeued == 10
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_invalid_inputs(self, queue: KVStoreQueue) -> None:
        """Test queue behavior with invalid inputs."""
        # Test dequeue with invalid max_items
        dequeued = await queue.dequeue(max_items=0)
        assert len(dequeued) == 0

        dequeued = await queue.dequeue(max_items=-1)
        assert len(dequeued) == 0

        # Test peek with invalid max_items
        peeked = await queue.peek(max_items=0)
        assert len(peeked) == 0

        peeked = await queue.peek(max_items=-1)
        assert len(peeked) == 0

    @pytest.mark.asyncio
    async def test_close_operation(self, queue: KVStoreQueue) -> None:
        """Test queue close operation."""
        # Close should not raise an exception
        await queue.close()

        # Operations should still work after close (kv_store handles its own cleanup)
        request = {"url": str(URL("https://example.com"))}
        await queue.enqueue([request])
        assert await queue.size() == 1

    def test_invalid_namespace(self, kv_store: Any) -> None:
        """Test queue creation with invalid namespace."""
        with pytest.raises(
            ConfigurationError, match="namespace must be a non-empty string"
        ):
            KVStoreQueue(
                kv_store=kv_store,
                namespace="",  # Empty namespace
                serializer=RequestMetaSerializer(),
            )


class TestRequestQueueProtocol:
    """Test that KVStoreQueue implements RequestQueue protocol correctly."""

    def test_protocol_compliance(self) -> None:
        """Test that KVStoreQueue implements RequestQueue protocol."""
        kv_store = create_kv_store(store_type="memory")
        queue = KVStoreQueue(
            kv_store=kv_store,
            namespace="test",
            serializer=RequestMetaSerializer(),
        )

        # Check that all required methods exist
        assert hasattr(queue, "enqueue")
        assert hasattr(queue, "dequeue")
        assert hasattr(queue, "size")
        assert hasattr(queue, "peek")
        assert hasattr(queue, "clear")
        assert hasattr(queue, "close")

        # Check that methods are callable
        assert callable(queue.enqueue)
        assert callable(queue.dequeue)
        assert callable(queue.size)
        assert callable(queue.peek)
        assert callable(queue.clear)
        assert callable(queue.close)
