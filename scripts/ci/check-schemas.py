#!/usr/bin/env python3
"""Validate published Schema structure and identifier uniqueness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    identifiers: dict[str, Path] = {}
    failures: list[str] = []
    for path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            failures.append(f"{path.name}: {error}")
            continue
        identifier = schema.get("$id")
        if not isinstance(identifier, str):
            failures.append(f"{path.name}: missing string $id")
        elif identifier in identifiers:
            failures.append(
                f"{path.name}: duplicate $id also used by {identifiers[identifier].name}"
            )
        else:
            identifiers[identifier] = path
        version = path.stem.rsplit("-", 1)[-1]
        if not isinstance(identifier, str) or not identifier.endswith(f"/{version}"):
            failures.append(f"{path.name}: $id does not end in /{version}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Validated {len(identifiers)} published schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
