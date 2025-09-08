"""Tests for core framework components.

This module contains unit tests for the core framework components,
including FetcherRecipeBuilder and configuration utilities.
"""

from data_fetcher_core.core import (
    BID,
    BundleRef,
    FetcherRecipe,
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


class TestBID:
    """Test BID class."""

    def test_basic_creation(self) -> None:
        """Test basic BID creation."""
        bid = BID()
        assert isinstance(bid, BID)
        assert isinstance(str(bid), str)
        assert len(str(bid)) > 0

    def test_custom_value(self) -> None:
        """Test BID creation with custom value."""
        custom_value = "custom-bid-value"
        bid = BID(custom_value)
        assert str(bid) == custom_value
        assert bid.value == custom_value

    def test_generate_class_method(self) -> None:
        """Test BID.generate() class method."""
        bid = BID.generate()
        assert isinstance(bid, BID)
        assert isinstance(str(bid), str)

    def test_uniqueness(self) -> None:
        """Test that BIDs are unique."""
        bid1 = BID()
        bid2 = BID()
        assert bid1 != bid2
        assert str(bid1) != str(bid2)

    def test_equality(self) -> None:
        """Test BID equality."""
        value = "test-bid-value"
        bid1 = BID(value)
        bid2 = BID(value)
        assert bid1 == bid2
        assert str(bid1) == str(bid2)

    def test_inequality_with_different_types(self) -> None:
        """Test BID inequality with different types."""
        bid = BID("test-value")
        assert bid != "test-value"
        assert bid != 123
        assert bid is not None

    def test_hash(self) -> None:
        """Test BID hashing."""
        value = "test-bid-value"
        bid1 = BID(value)
        bid2 = BID(value)
        bid3 = BID("test-different-value")

        # Same values should have same hash
        assert hash(bid1) == hash(bid2)

        # Different values should have different hashes
        assert hash(bid1) != hash(bid3)

    def test_string_representation(self) -> None:
        """Test BID string representations."""
        value = "test-bid-value"
        bid = BID(value)

        # Test __str__
        assert str(bid) == value

        # Test __repr__
        repr_str = repr(bid)
        assert "BID(" in repr_str
        assert value in repr_str

    def test_value_property(self) -> None:
        """Test BID value property."""
        value = "test-bid-value"
        bid = BID(value)
        assert bid.value == value

    def test_time_based_format(self) -> None:
        """Test that BID has time-based format."""
        bid = BID()
        bid_str = str(bid)

        # Should be in UUID-like format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = bid_str.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8  # timestamp part
        assert len(parts[1]) == 4  # timestamp part
        assert len(parts[2]) == 4  # random part
        assert len(parts[3]) == 4  # random part
        assert len(parts[4]) == 12  # random part

    def test_multiple_generations(self) -> None:
        """Test multiple BID generations."""
        bids = [BID() for _ in range(10)]
        bid_strings = [str(bid) for bid in bids]

        # All should be unique
        assert len(set(bid_strings)) == 10

        # All should be valid BID instances
        for bid in bids:
            assert isinstance(bid, BID)


class TestBundleRef:
    """Test BundleRef dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic BundleRef creation."""
        ref = BundleRef(primary_url="https://example.com", resources_count=5)
        assert ref.primary_url == "https://example.com"
        assert ref.resources_count == 5
        assert ref.storage_key is None
        assert ref.meta == {}
        # BID should be automatically generated
        assert isinstance(ref.bid, BID)
        assert str(ref.bid) is not None

    def test_with_all_fields(self) -> None:
        """Test BundleRef creation with all fields."""
        custom_bid = BID("custom-bundle-id")
        ref = BundleRef(
            primary_url="https://example.com",
            resources_count=3,
            bid=custom_bid,
            storage_key="warc_file_123",
            meta={"fetched_at": 1234567890},
        )
        assert ref.primary_url == "https://example.com"
        assert ref.resources_count == 3
        assert ref.bid == custom_bid
        assert ref.storage_key == "warc_file_123"
        assert ref.meta == {"fetched_at": 1234567890}

    def test_bid_automatic_generation(self) -> None:
        """Test that BID is automatically generated when not provided."""
        ref1 = BundleRef(primary_url="https://example.com", resources_count=1)
        ref2 = BundleRef(primary_url="https://example.com", resources_count=1)

        # Both should have BIDs
        assert isinstance(ref1.bid, BID)
        assert isinstance(ref2.bid, BID)

        # BIDs should be different
        assert ref1.bid != ref2.bid

    def test_bid_custom_value(self) -> None:
        """Test BundleRef with custom BID."""
        custom_bid = BID("test-bundle-id")
        ref = BundleRef(
            primary_url="https://example.com", resources_count=1, bid=custom_bid
        )
        assert ref.bid == custom_bid
        assert str(ref.bid) == "test-bundle-id"


class TestFetchRunContext:
    """Test FetchRunContext dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic FetchRunContext creation."""
        ctx = FetchRunContext(run_id="test_run")
        assert ctx.shared == {}

    def test_with_shared_data(self) -> None:
        """Test FetchRunContext with shared data."""
        ctx = FetchRunContext(run_id="test_run", shared={"key": "value", "count": 42})
        assert ctx.shared == {"key": "value", "count": 42}

    def test_with_run_id(self) -> None:
        """Test FetchRunContext with run_id."""
        run_id = "fetcher_test_20250127143022"
        ctx = FetchRunContext(run_id=run_id)
        assert ctx.run_id == run_id
        assert ctx.shared == {}

    def test_with_run_id_and_shared_data(self) -> None:
        """Test FetchRunContext with both run_id and shared data."""
        run_id = "fetcher_test_20250127143022"
        shared_data = {"key": "value", "count": 42}
        ctx = FetchRunContext(run_id=run_id, shared=shared_data)
        assert ctx.run_id == run_id
        assert ctx.shared == shared_data


class TestFetchPlan:
    """Test FetchPlan dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic FetchPlan creation."""
        recipe = FetcherRecipe(recipe_id="test_recipe")
        context = FetchRunContext(run_id="test_run")
        plan = FetchPlan(recipe=recipe, context=context)
        assert plan.concurrency == 1

    def test_with_all_fields(self) -> None:
        """Test FetchPlan creation with all fields."""
        recipe = FetcherRecipe(recipe_id="test_recipe")
        context = FetchRunContext(run_id="test_run", shared={"key": "value"})
        plan = FetchPlan(
            recipe=recipe,
            context=context,
            concurrency=8,
        )
        assert plan.concurrency == 8
        assert plan.context == context
        assert plan.recipe == recipe
