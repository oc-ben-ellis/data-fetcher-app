"""Tests for core framework components.

This module contains unit tests for the core framework components,
including FetcherContextBuilder and configuration utilities.
"""

from oc_fetcher.core import (
    BundleRef,
    FetchPlan,
    FetchRunContext,
    RequestMeta,
    ResourceMeta,
)


class TestRequestMeta:
    """Test RequestMeta dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic RequestMeta creation."""
        req = RequestMeta(url="https://example.com")
        assert req.url == "https://example.com"
        assert req.depth == 0
        assert req.referer is None
        assert req.headers == {}
        assert req.flags == {}

    def test_with_all_fields(self) -> None:
        """Test RequestMeta creation with all fields."""
        req = RequestMeta(
            url="https://example.com/page",
            depth=2,
            referer="https://example.com",
            headers={"User-Agent": "TestBot"},
            flags={"priority": "high"},
        )
        assert req.url == "https://example.com/page"
        assert req.depth == 2
        assert req.referer == "https://example.com"
        assert req.headers == {"User-Agent": "TestBot"}
        assert req.flags == {"priority": "high"}


class TestResourceMeta:
    """Test ResourceMeta dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic ResourceMeta creation."""
        res = ResourceMeta(url="https://example.com/resource")
        assert res.url == "https://example.com/resource"
        assert res.status is None
        assert res.content_type is None
        assert res.headers == {}
        assert res.note is None

    def test_with_all_fields(self) -> None:
        """Test ResourceMeta creation with all fields."""
        res = ResourceMeta(
            url="https://example.com/resource",
            status=200,
            content_type="text/html",
            headers={"Content-Length": "1024"},
            note="primary",
        )
        assert res.url == "https://example.com/resource"
        assert res.status == 200
        assert res.content_type == "text/html"
        assert res.headers == {"Content-Length": "1024"}
        assert res.note == "primary"


class TestBundleRef:
    """Test BundleRef dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic BundleRef creation."""
        ref = BundleRef(primary_url="https://example.com", resources_count=5)
        assert ref.primary_url == "https://example.com"
        assert ref.resources_count == 5
        assert ref.storage_key is None
        assert ref.meta == {}

    def test_with_all_fields(self) -> None:
        """Test BundleRef creation with all fields."""
        ref = BundleRef(
            primary_url="https://example.com",
            resources_count=3,
            storage_key="warc_file_123",
            meta={"fetched_at": 1234567890},
        )
        assert ref.primary_url == "https://example.com"
        assert ref.resources_count == 3
        assert ref.storage_key == "warc_file_123"
        assert ref.meta == {"fetched_at": 1234567890}


class TestFetchRunContext:
    """Test FetchRunContext dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic FetchRunContext creation."""
        ctx = FetchRunContext()
        assert ctx.shared == {}

    def test_with_shared_data(self) -> None:
        """Test FetchRunContext with shared data."""
        ctx = FetchRunContext(shared={"key": "value", "count": 42})
        assert ctx.shared == {"key": "value", "count": 42}


class TestFetchPlan:
    """Test FetchPlan dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic FetchPlan creation."""
        context = FetchRunContext()
        plan = FetchPlan(requests=[], context=context)
        assert plan.concurrency == 1

    def test_with_all_fields(self) -> None:
        """Test FetchPlan creation with all fields."""
        context = FetchRunContext(shared={"key": "value"})
        requests = [RequestMeta(url="https://example.com")]
        plan = FetchPlan(
            requests=requests,
            context=context,
            concurrency=8,
        )
        assert plan.concurrency == 8
        assert plan.requests == requests
        assert plan.context == context
