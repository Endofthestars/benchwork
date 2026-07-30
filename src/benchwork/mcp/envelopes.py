"""Stable, bounded MCP response envelopes."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ..errors import classify_error
from ..schema_validation import validate_instance

SCHEMA_VERSION = "mcp-tool-result/1.0"
MAX_RESULT_BYTES = 512 * 1024


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("MCP results cannot contain non-finite numbers")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _project_relative(value: Any, project_root: Path | None) -> Any:
    if project_root is None:
        return value
    root = str(project_root.resolve())
    if isinstance(value, str):
        return value.replace(root, ".")
    if isinstance(value, dict):
        return {
            str(key): _project_relative(item, project_root)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_project_relative(item, project_root) for item in value]
    return value


def success(
    tool: str,
    data: Any,
    *,
    receipt: Any = None,
    warnings: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> dict[str, Any]:
    rendered_receipt = receipt.as_dict() if hasattr(receipt, "as_dict") else receipt
    result: dict[str, Any] = {
        "ok": True,
        "tool": tool,
        "schema_version": SCHEMA_VERSION,
        "data": _json_safe(data),
        "receipt": _json_safe(rendered_receipt),
        "warnings": warnings or [],
        "next_actions": next_actions or [],
    }
    validate_instance("mcp-tool-result-1.0.json", result)
    if len(json.dumps(result, separators=(",", ":")).encode("utf-8")) > MAX_RESULT_BYTES:
        raise ValueError("MCP result exceeds the bounded output limit; use pagination")
    return result


def failure(
    tool: str,
    error: ValueError,
    *,
    code: str | None = None,
    project_root: Path | None = None,
    next_actions: list[str] | None = None,
) -> dict[str, Any]:
    classified = classify_error(error)
    error_code = code or classified.code
    if "STALE_PREVIEW" in str(error):
        error_code = "STALE_PREVIEW"
    elif "INVALID_CONFIRMATION" in str(error):
        error_code = "INVALID_CONFIRMATION"
    result: dict[str, Any] = {
        "ok": False,
        "tool": tool,
        "schema_version": SCHEMA_VERSION,
        "error": {
            "code": error_code,
            "message": _project_relative(
                str(error).split(": ", 1)[-1],
                project_root,
            ),
            "details": _json_safe(
                _project_relative(classified.details, project_root)
            ),
        },
        "warnings": [],
        "next_actions": next_actions or [],
    }
    validate_instance("mcp-tool-result-1.0.json", result)
    if len(json.dumps(result, separators=(",", ":")).encode("utf-8")) > MAX_RESULT_BYTES:
        result["error"]["details"] = {}
        result["error"]["message"] = "Benchwork tool failure; details exceeded the output limit"
        validate_instance("mcp-tool-result-1.0.json", result)
    return result
