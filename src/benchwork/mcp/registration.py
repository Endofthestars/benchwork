"""MCP registration helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any

from .runtime import BenchworkTools


def register_tools(
    server: Any,
    tools: BenchworkTools,
    names: Iterable[str],
) -> None:
    """Register async façades while preserving each typed method signature."""
    for name in names:
        method = getattr(tools, name)

        @wraps(method)  # type: ignore[arg-type]
        async def invoke(
            *args: Any,
            __method: Callable[..., dict[str, Any]] = method,
            **kwargs: Any,
        ) -> dict[str, Any]:
            return __method(*args, **kwargs)

        server.add_tool(
            invoke,
            name=name,
            structured_output=True,
        )
