"""Tests for key-value store implementations.

This module contains unit tests for key-value store functionality,
including in-memory storage, Redis integration, and base interfaces.
"""

import asyncio
from typing import Any

import pytest

from data_fetcher_core.kv_store import (
    InMemoryKeyValueStore,
)


class TestInMemoryKeyValueStore:
    """Test the in-memory key-value store implementation."""

    @pytest.fixture
    def store(self) -> InMemoryKeyValueStore:
        """Create a fresh in-memory store for each test."""
        return InMemoryKeyValueStore(serializer="json", default_ttl=3600)

    @pytest.mark.asyncio
    async def test_basic_operations(self, store: InMemoryKeyValueStore) -> None:
        """Test basic PUT, GET, DELETE operations."""
        try:
            # Test PUT and GET
            await store.put("test_key", {"value": "test_data"})
            result = await store.get("test_key")
            assert result == {"value": "test_data"}

            # Test GET with default
            result = await store.get("nonexistent_key", default="default_value")
            assert result == "default_value"

            # Test EXISTS
            assert await store.exists("test_key") is True
            assert await store.exists("nonexistent_key") is False

            # Test DELETE
            assert await store.delete("test_key") is True
            assert await store.delete("nonexistent_key") is False
            assert await store.exists("test_key") is False
        finally:
            await store.close()

    @pytest.mark.asyncio
    async def test_ttl_functionality(self, store: InMemoryKeyValueStore) -> None:
        """Test TTL (time-to-live) functionality."""
        try:
            # Store with very short TTL for faster testing
            await store.put("ttl_key", "ttl_value", ttl=1)  # 1 second TTL

            # Should exist immediately
            assert await store.exists("ttl_key") is True
            assert await store.get("ttl_key") == "ttl_value"

            # Wait for expiration
            await asyncio.sleep(1.1)  # Wait slightly longer than TTL

            # Should not exist after TTL
            assert await store.exists("ttl_key") is False
            assert await store.get("ttl_key") is None
        finally:
            await store.close()

    @pytest.mark.asyncio
    async def test_range_operations(self, store: InMemoryKeyValueStore) -> None:
        """Test range GET operations."""
        try:
            # Store multiple keys
            await store.put("a_key", "a_value")
            await store.put("b_key", "b_value")
            await store.put("c_key", "c_value")
            await store.put("d_key", "d_value")

            # Test range get with start key
            result = await store.range_get("b_key")
            assert len(result) == 3
            assert result[0][0] == "b_key"
            assert result[0][1] == "b_value"

            # Test range get with start and end key
            result = await store.range_get("b_key", "d_key")
            assert len(result) == 2
            assert result[0][0] == "b_key"
            assert result[1][0] == "c_key"

            # Test range get with limit
            result = await store.range_get("a_key", limit=2)
            assert len(result) == 2
            assert result[0][0] == "a_key"
            assert result[1][0] == "b_key"
        finally:
            await store.close()

    @pytest.mark.asyncio
    async def test_serialization(self, store: InMemoryKeyValueStore) -> None:
        """Test serialization of different data types."""
        try:
            # Test complex data structures
            complex_data = {
                "string": "value",
                "number": 42,
                "list": [1, 2, 3],
                "dict": {"nested": "data"},
                "boolean": True,
                "null": None,
            }

            await store.put("complex_key", complex_data)
            result = await store.get("complex_key")

            assert result == complex_data
            assert isinstance(result["number"], int)  # type: ignore[index]
            assert isinstance(result["list"], list)  # type: ignore[index]
            assert isinstance(result["dict"], dict)  # type: ignore[index]
        finally:
            await store.close()

    @pytest.mark.asyncio
    async def test_concurrent_access(self, store: InMemoryKeyValueStore) -> None:
        """Test concurrent access to the store."""
        try:
            # Create multiple concurrent tasks
            async def write_task(key: str, value: Any) -> None:
                await store.put(key, value)

            async def read_task(key: str) -> Any:
                return await store.get(key)

            # Start concurrent operations
            tasks = [write_task(f"key_{i}", f"value_{i}") for i in range(10)] + [
                read_task(f"key_{i}") for i in range(10)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check that all operations completed
            assert len(results) == 20

            # Verify some values were written and can be read
            for i in range(10):
                value = await store.get(f"key_{i}")
                assert value == f"value_{i}"
        finally:
            await store.close()


# Redis integration tests moved to tests/test_integration/test_redis.py


# TODO: Global store functionality is not implemented yet
# These tests are commented out until global store functionality is implemented


if __name__ == "__main__":
    # Run a simple demonstration
    async def demo() -> None:
        """Run a demonstration of the key-value store."""
        print("=== Key-Value Store Demonstration ===")

        # Create a store instance
        store = InMemoryKeyValueStore(serializer="json", default_ttl=3600)

        try:
            # Basic operations
            print("\n1. Basic Operations:")
            await store.put("demo_key", {"message": "Hello, World!", "number": 42})
            result = await store.get("demo_key")
            print(f"   Stored and retrieved: {result}")

            # TTL demonstration
            print("\n2. TTL Demonstration:")
            await store.put("ttl_demo", "This will expire in 2 seconds", ttl=2)
            print(f"   Key exists: {await store.exists('ttl_demo')}")
            await asyncio.sleep(2.1)
            print(f"   Key exists after TTL: {await store.exists('ttl_demo')}")

            # Range operations
            print("\n3. Range Operations:")
            for i in range(5):
                await store.put(f"range_key_{i}", f"value_{i}")

            results = await store.range_get("range_key_1", "range_key_4")
            print(f"   Range results: {results}")

        finally:
            await store.close()
            print("\n=== Demonstration Complete ===")

    # Run the demonstration
    asyncio.run(demo())
