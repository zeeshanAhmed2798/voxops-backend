"""Shared cursor-pagination response models and opaque cursor helpers."""

import base64
import json
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


ItemT = TypeVar("ItemT")


class CursorPage(BaseModel, Generic[ItemT]):
    """A stable page that can be continued with ``next_cursor``."""

    items: list[ItemT]
    next_cursor: str | None = None
    has_more: bool
    limit: int = Field(ge=1, le=100)


def encode_cursor(values: dict[str, str]) -> str:
    """Encode non-sensitive keyset values into an opaque URL-safe cursor."""
    raw = json.dumps(values, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> dict[str, str]:
    """Decode a cursor, raising ValueError for malformed input."""
    try:
        padding = "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(cursor + padding).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid cursor.") from exc
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise ValueError("Invalid cursor.")
    return value
