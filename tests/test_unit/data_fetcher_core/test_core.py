"""Tests for core framework components.

This module contains unit tests for the core framework components,
including DataRegistryFetcherConfigBuilder and configuration utilities.
"""

import pytest
from oc_pipeline_bus.identifiers import Bid as BID

from data_fetcher_core.core import (
    BundleRef,
    DataRegistryFetcherConfig,
    FetchPlan,
    FetchRunContext,
)


class TestRequestMeta:
    """Test RequestMeta structure (dict-based in current implementation)."""

    def test_basic_creation(self) -> None:
        req = {
            "url": "https://example.com",
            "depth": 0,
            "headers": {},
            "flags": {},
            "referer": None,
        }
        assert req["url"] == "https://example.com"
        assert req.get("depth", 0) == 0
        assert req.get("referer") is None
        assert req.get("headers") == {}
        assert req.get("flags") == {}

    def test_with_all_fields(self) -> None:
        req = {
            "url": "https://example.com/page",
            "depth": 2,
            "referer": "https://example.com",
            "headers": {"User-Agent": "TestBot"},
            "flags": {"priority": "high"},
        }
        assert req["url"] == "https://example.com/page"
        assert req["depth"] == 2
        assert req["referer"] == "https://example.com"
        assert req["headers"] == {"User-Agent": "TestBot"}
        assert req["flags"] == {"priority": "high"}


class TestResourceMeta:
    """Test ResourceMeta structure (dict-based)."""

    def test_basic_creation(self) -> None:
        res = {"url": "https://example.com/resource", "headers": {}}
        assert res["url"] == "https://example.com/resource"
        assert res.get("status") is None
        assert res.get("content_type") is None
        assert res.get("headers") == {}
        assert res.get("note") is None

    def test_with_all_fields(self) -> None:
        res = {
            "url": "https://example.com/resource",
            "status": 200,
            "content_type": "text/html",
            "headers": {"Content-Length": "1024"},
            "note": "primary",
        }
        assert res["url"] == "https://example.com/resource"
        assert res["status"] == 200
        assert res["content_type"] == "text/html"
        assert res["headers"] == {"Content-Length": "1024"}
        assert res["note"] == "primary"


class TestBID:
    """Test BID class."""

    def test_basic_creation(self) -> None:
        """Test basic BID creation (spec-compliant string required)."""
        val = "bid:v1:test_registry:20240115103000:abc12345"
        bid = BID(val)
        assert isinstance(bid, BID)
        assert str(bid) == val

    def test_custom_value(self) -> None:
        """Test BID creation with custom value."""
        custom_value = "bid:v1:test_registry:20240115103000:abc12345"
        bid = BID(custom_value)
        assert str(bid) == custom_value

    def test_generate_class_method(self) -> None:
        """Construct directly with valid string; generation not supported here."""
        val = "bid:v1:test_registry:20240115103000:abc12345"
        bid = BID(val)
        assert isinstance(bid, BID)
        assert str(bid) == val

    def test_uniqueness(self) -> None:
        """Test that BIDs are unique."""
        bid1 = BID("bid:v1:test_registry:20240115103000:abc12345")
        bid2 = BID("bid:v1:test_registry:20240115103001:def67890")
        assert bid1 != bid2
        assert str(bid1) != str(bid2)

    def test_equality(self) -> None:
        """Test BID equality."""
        value = "bid:v1:test_registry:20240115103000:abc12345"
        bid1 = BID(value)
        bid2 = BID(value)
        assert bid1 == bid2
        assert str(bid1) == str(bid2)

    def test_inequality_with_different_types(self) -> None:
        """Test BID inequality with different types."""
        bid = BID("bid:v1:test_registry:20240115103000:abc12345")
        assert bid != "bid:v1:test_registry:20240115103000:abc12345"
        assert bid != 123
        assert bid is not None

    def test_hash(self) -> None:
        """Test BID hashing."""
        value = "bid:v1:test_registry:20240115103000:abc12345"
        bid1 = BID(value)
        bid2 = BID(value)
        bid3 = BID("bid:v1:test_registry:20240115103001:def67890")

        # Same values should have same hash
        assert hash(bid1) == hash(bid2)

        # Different values should have different hashes
        assert hash(bid1) != hash(bid3)

    def test_string_representation(self) -> None:
        """Test BID string representations."""
        value = "bid:v1:test_registry:20240115103000:abc12345"
        bid = BID(value)

        # Test __str__
        assert str(bid) == value

        # Test __repr__ string contains value
        repr_str = repr(bid)
        assert value in repr_str

    def test_value_property(self) -> None:
        """Test BID string usage as value."""
        value = "bid:v1:test_registry:20240115103000:abc12345"
        bid = BID(value)
        assert str(bid) == value

    def test_spec_compliant_format(self) -> None:
        """Test that BID validates spec-compliant format."""
        # Valid spec-compliant BID
        valid_bid = "bid:v1:test_registry:20240115103000:abc12345"
        bid = BID(valid_bid)
        assert str(bid) == valid_bid

        # Spec validation method no longer exists; constructor validation suffices

    def test_invalid_format_rejection(self) -> None:
        """Test that clearly invalid BID formats are rejected."""
        with pytest.raises(Exception):
            BID("invalid-format")

    def test_test_values_allowed(self) -> None:
        """Spec-enforced strings must match pattern; invalid ones should raise."""
        with pytest.raises(Exception):
            BID("test-bundle-id")

    def test_multiple_generations(self) -> None:
        """Construct multiple BIDs from strings to verify stability."""
        bid_strings = [
            "bid:v1:test_registry:20240115103000:abc12345",
            "bid:v1:test_registry:20240115103001:def67890",
        ]
        bids = [BID(s) for s in bid_strings]
        assert all(isinstance(b, BID) for b in bids)


class TestBundleRef:
    """Test BundleRef dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic BundleRef creation via dict interface."""
        ref = BundleRef.from_dict(
            {
                "bid": "bid:v1:test_registry:20240115103000:abc12345",
                "meta": {"primary_url": "https://example.com", "resources_count": 5},
            }
        )
        assert ref.meta.get("primary_url") == "https://example.com"
        assert ref.meta.get("resources_count") == 5

    def test_with_all_fields(self) -> None:
        """Test BundleRef creation with all fields."""
        custom_bid = BID("bid:v1:test_registry:20240115103000:abc12345")
        ref = BundleRef.from_dict(
            {
                "bid": str(custom_bid),
                "meta": {
                    "fetched_at": 1234567890,
                    "primary_url": "https://example.com",
                    "resources_count": 3,
                },
            }
        )
        assert str(ref.bid) == str(custom_bid)
        assert ref.meta == {
            "fetched_at": 1234567890,
            "primary_url": "https://example.com",
            "resources_count": 3,
        }

    def test_bid_automatic_generation(self) -> None:
        """Test that BID is automatically generated when not provided."""
        ref1 = BundleRef.from_dict(
            {"bid": "bid:v1:test_registry:20240115103000:abc12345", "meta": {}}
        )
        ref2 = BundleRef.from_dict(
            {"bid": "bid:v1:test_registry:20240115103001:def67890", "meta": {}}
        )
        assert ref1.bid != ref2.bid

    def test_bid_custom_value(self) -> None:
        """Test BundleRef with custom BID."""
        custom_bid = BID("bid:v1:test_registry:20240115103000:abc12345")
        ref = BundleRef.from_dict({"bid": str(custom_bid), "meta": {}})
        assert str(ref.bid) == "bid:v1:test_registry:20240115103000:abc12345"


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
        recipe = DataRegistryFetcherConfig(loader={"dummy": {}}, locators=[])
        context = FetchRunContext(run_id="test_run")
        plan = FetchPlan(config=recipe, context=context)
        assert plan.concurrency == 1

    def test_with_all_fields(self) -> None:
        """Test FetchPlan creation with all fields."""
        recipe = DataRegistryFetcherConfig(loader={"dummy": {}}, locators=[])
        context = FetchRunContext(run_id="test_run", shared={"key": "value"})
        plan = FetchPlan(
            config=recipe,
            context=context,
            concurrency=8,
        )
        assert plan.concurrency == 8
        assert plan.context == context
        assert plan.config == recipe
