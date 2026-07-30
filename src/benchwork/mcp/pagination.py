"""Opaque, deterministic cursor pagination."""

from __future__ import annotations

import base64
import json
from typing import Any, Iterable

from ..athanor import AthanorError

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _decode(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        offset = payload["offset"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise AthanorError("invalid pagination cursor") from error
    if not isinstance(offset, int) or offset < 0:
        raise AthanorError("invalid pagination cursor")
    return offset


def _encode(offset: int) -> str:
    blob = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(blob).decode().rstrip("=")


def page(
    values: Iterable[Any],
    *,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    if not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
        raise AthanorError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    items = list(values)
    offset = _decode(cursor)
    if offset > len(items):
        raise AthanorError("pagination cursor is past the end of the collection")
    selected = items[offset : offset + limit]
    following = offset + len(selected)
    return {
        "items": selected,
        "next_cursor": _encode(following) if following < len(items) else None,
        "total": len(items),
    }
