#!/usr/bin/env python3
"""Validate published Schema structure and identifier uniqueness."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urldefrag

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]


def _resolve_pointer(document: object, fragment: str) -> object:
    if not fragment:
        return document
    if not fragment.startswith("/"):
        raise ValueError(f"unsupported non-pointer fragment #{fragment}")
    current = document
    for token in fragment[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise ValueError(f"unresolvable fragment #{fragment}")
    return current


def _check_references(value: object, document_id: str, by_id: dict[str, object]) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            base, fragment = urldefrag(reference)
            target_id = base or document_id
            if target_id not in by_id:
                raise ValueError(f"unavailable Schema {target_id}")
            _resolve_pointer(by_id[target_id], fragment)
        for member in value.values():
            _check_references(member, document_id, by_id)
    elif isinstance(value, list):
        for member in value:
            _check_references(member, document_id, by_id)


def main() -> int:
    identifiers: dict[str, Path] = {}
    documents: dict[str, object] = {}
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
            documents[identifier] = schema
        version = path.stem.rsplit("-", 1)[-1]
        if not isinstance(identifier, str) or not identifier.endswith(f"/{version}"):
            failures.append(f"{path.name}: $id does not end in /{version}")
    for identifier, path in identifiers.items():
        try:
            _check_references(documents[identifier], identifier, documents)
        except (KeyError, IndexError, ValueError) as error:
            failures.append(f"{path.name}: {error}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Validated {len(identifiers)} published schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
