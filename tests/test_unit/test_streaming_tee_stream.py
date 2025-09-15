"""Tests for TeeStream utility."""

import asyncio
from collections.abc import AsyncGenerator

from data_fetcher_core.storage.streaming.tee_stream import TeeStream


async def simple_stream() -> AsyncGenerator[bytes]:
    """Simple test stream that yields some data."""
    for i in range(5):
        yield f"chunk_{i}".encode()


async def test_tee_stream_basic():
    """Test basic TeeStream functionality."""
    source_stream = simple_stream()
    tee_stream = TeeStream(source_stream)

    # Get two streams from the tee
    stream_a = tee_stream.get_stream(0)
    stream_b = tee_stream.get_stream(1)

    # Collect data from both streams
    data_a = []
    data_b = []

    async def consume(stream, out):
        async for chunk in stream:
            out.append(chunk)

    await asyncio.gather(consume(stream_a, data_a), consume(stream_b, data_b))

    # Both streams should have the same data
    assert data_a == data_b
    assert len(data_a) == 5
    assert data_a[0] == b"chunk_0"
    assert data_a[4] == b"chunk_4"

    await tee_stream.close()


async def test_tee_stream_multiple_consumers():
    """Test TeeStream with multiple consumers."""
    source_stream = simple_stream()
    tee_stream = TeeStream(source_stream)

    # Get three streams from the tee
    streams = [tee_stream.get_stream(i) for i in range(3)]

    # Collect data from all streams
    all_data = []

    async def consume(stream):
        buf = []
        async for chunk in stream:
            buf.append(chunk)
        return buf

    all_data = await asyncio.gather(*[consume(s) for s in streams])

    # All streams should have the same data
    for data in all_data:
        assert data == all_data[0]
        assert len(data) == 5

    await tee_stream.close()


async def test_tee_stream_empty():
    """Test TeeStream with empty source stream."""

    async def empty_stream() -> AsyncGenerator[bytes]:
        return
        yield  # This line will never be reached

    source_stream = empty_stream()
    tee_stream = TeeStream(source_stream)

    stream = tee_stream.get_stream(0)
    data = []
    async for chunk in stream:
        data.append(chunk)

    assert data == []
    await tee_stream.close()


async def test_tee_stream_large_data():
    """Test TeeStream with larger data chunks."""

    async def large_stream() -> AsyncGenerator[bytes]:
        for _i in range(10):
            yield b"x" * 1024  # 1KB chunks

    source_stream = large_stream()
    tee_stream = TeeStream(source_stream)

    stream_a = tee_stream.get_stream(0)
    stream_b = tee_stream.get_stream(1)

    data_a = []
    data_b = []

    async def consume(stream, out):
        async for chunk in stream:
            out.append(chunk)

    await asyncio.gather(consume(stream_a, data_a), consume(stream_b, data_b))

    assert data_a == data_b
    assert len(data_a) == 10
    assert all(len(chunk) == 1024 for chunk in data_a)

    await tee_stream.close()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_tee_stream_basic())
    asyncio.run(test_tee_stream_multiple_consumers())
    asyncio.run(test_tee_stream_empty())
    asyncio.run(test_tee_stream_large_data())
    print("All tests passed!")
