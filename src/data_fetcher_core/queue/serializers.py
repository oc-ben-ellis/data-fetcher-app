"""Serializers for queue items.

This module provides serialization implementations for queue items,
with specialized support for RequestMeta objects.
"""

import json

from yarl import URL

from data_fetcher_core.core import BundleRef, RequestMeta

from .base import Serializer


class JSONSerializer(Serializer):
    """JSON-based serializer for queue items.

    Provides JSON serialization/deserialization for general objects.
    Uses default=str to handle non-JSON-serializable types.
    """

    def dumps(self, obj: object) -> str:
        """Serialize object to JSON string.

        Args:
            obj: The object to serialize.

        Returns:
            JSON string representation of the object.
        """
        return json.dumps(obj, default=str)

    def loads(self, data: str) -> object:
        """Deserialize JSON string to object.

        Args:
            data: The JSON string to deserialize.

        Returns:
            The deserialized object.
        """
        return json.loads(data)


class RequestMetaSerializer(JSONSerializer):
    """Specialized serializer for RequestMeta objects.

    Handles serialization of RequestMeta objects by converting them
    to dictionaries before JSON serialization.
    """

    def dumps(self, obj: object) -> str:
        """Serialize RequestMeta to JSON.

        Args:
            obj: The RequestMeta object to serialize.

        Returns:
            JSON string representation of the RequestMeta.
        """
        if isinstance(obj, dict):
            return json.dumps(obj, default=str)
        return super().dumps(obj)

    def loads(self, data: str) -> RequestMeta:
        """Deserialize JSON to RequestMeta object.

        Args:
            data: The JSON string to deserialize.

        Returns:
            RequestMeta object reconstructed from the serialized data.
        """
        data_dict = json.loads(data)

        # Reconstruct RequestMeta dict
        return {
            "url": str(URL(data_dict["url"])),
            "depth": data_dict.get("depth", 0),
            "referer": str(URL(data_dict["referer"]))
            if data_dict.get("referer")
            else None,
            "headers": data_dict.get("headers", {}),
            "flags": data_dict.get("flags", {}),
        }


class BundleRefSerializer(JSONSerializer):
    """Serializer for `BundleRef` objects using simple dict representation."""

    def dumps(self, obj: object) -> str:
        if isinstance(obj, BundleRef):
            # Ensure request_meta is serialized as a plain dict
            data = {
                "bid": str(obj.bid),
                "request_meta": dict(obj.request_meta),
            }
            return json.dumps(data, default=str)
        return super().dumps(obj)

    def loads(self, data: str) -> BundleRef:
        data_dict = json.loads(data)
        request_meta = data_dict.get("request_meta", {})
        # Coerce non-dict mappings/strings defensively into a dict
        if not isinstance(request_meta, dict):
            try:
                request_meta = dict(request_meta)  # type: ignore[arg-type]
            except (TypeError, ValueError, AttributeError) as e:
                raise ValueError(f"Failed to convert request_meta to dict: {e}") from e
        return BundleRef.from_dict(
            {
                "bid": data_dict.get("bid"),
                "request_meta": request_meta,
            }
        )
