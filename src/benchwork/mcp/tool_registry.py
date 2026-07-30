"""Fail-closed loader for the frozen Phase 2 MCP tool inventory."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
from typing import Any


REGISTRY_SCHEMA_VERSION = "mcp-tool-registry/1.0"
REGISTRY_API_VERSION = "0.3"
TOOL_CATEGORIES = ("read", "task", "canonical", "experiment")
TOOL_FIELDS = {
    "name",
    "category",
    "permission",
    "risk",
    "approval",
    "canonical_effect",
}


@lru_cache(maxsize=1)
def _load_tool_registry() -> dict[str, Any]:
    """Load and minimally verify the packaged registry before registration."""
    resource = files(__package__).joinpath("tool_registry.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("MCP tool registry must be an object")
    if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ValueError("unsupported MCP tool registry schema")
    if payload.get("api_version") != REGISTRY_API_VERSION:
        raise ValueError("unsupported MCP tool API version")
    entries = payload.get("tools")
    if not isinstance(entries, list) or not entries:
        raise ValueError("MCP tool registry must contain tools")

    names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != TOOL_FIELDS:
            raise ValueError("invalid MCP tool registry entry")
        name = entry["name"]
        if not isinstance(name, str) or not name.startswith("benchwork_"):
            raise ValueError("invalid MCP tool name")
        if name in names:
            raise ValueError(f"duplicate MCP tool name: {name}")
        if entry["category"] not in TOOL_CATEGORIES:
            raise ValueError(f"invalid MCP tool category: {name}")
        names.add(name)
    return payload


def load_tool_registry() -> dict[str, Any]:
    """Return a detached registry snapshot for inspection and validation."""
    return deepcopy(_load_tool_registry())


def tool_names(category: str | None = None) -> tuple[str, ...]:
    """Return stable registry order, optionally filtered by category."""
    if category is not None and category not in TOOL_CATEGORIES:
        raise ValueError(f"unknown MCP tool category: {category}")
    entries = _load_tool_registry()["tools"]
    return tuple(
        entry["name"]
        for entry in entries
        if category is None or entry["category"] == category
    )


def tool_metadata(name: str) -> dict[str, Any]:
    """Return one immutable-by-convention metadata copy."""
    for entry in _load_tool_registry()["tools"]:
        if entry["name"] == name:
            return dict(entry)
    raise KeyError(name)
