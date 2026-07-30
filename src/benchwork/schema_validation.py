"""Runtime validation against Benchwork's published JSON Schemas."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from .athanor import AthanorError


RFC3339_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time")
def _is_rfc3339_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not RFC3339_DATE_TIME.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _schema_directory() -> Path:
    module = Path(__file__).resolve()
    candidates = (
        module.parents[2] / "schemas",
        module.parents[1] / "share" / "benchwork" / "schemas",
        Path(sys.prefix) / "share" / "benchwork" / "schemas",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise AthanorError("installed Benchwork schemas are missing")


@lru_cache(maxsize=1)
def _schemas() -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    registry = Registry()
    for path in _schema_directory().glob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def validate_instance(schema_name: str, instance: dict[str, Any]) -> None:
    schemas, registry = _schemas()
    try:
        Draft202012Validator(
            schemas[schema_name],
            registry=registry,
            format_checker=FORMAT_CHECKER,
        ).validate(instance)
    except ValidationError as error:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise AthanorError(f"{schema_name} validation failed at {location}: {error.message}") from error
