#!/usr/bin/env python3
"""Fail when a repository-local Markdown link points to a missing path."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
IGNORED_PREFIXES = ("http://", "https://", "mailto:", "#")


def local_target(document: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>")
    if not target or target.startswith(IGNORED_PREFIXES):
        return None
    path_text = unquote(target.split("#", 1)[0])
    if not path_text:
        return None
    return (document.parent / path_text).resolve()


def main() -> int:
    failures: list[str] = []
    for document in sorted(ROOT.rglob("*.md")):
        if any(part.startswith(".") and part not in {".github"} for part in document.parts):
            continue
        text = document.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK.finditer(line):
                target = local_target(document, match.group(1))
                if target is not None and not target.exists():
                    failures.append(
                        f"{document.relative_to(ROOT)}:{line_number}: "
                        f"missing {match.group(1)}"
                    )
    if failures:
        print("\n".join(failures))
        return 1
    print("Documentation links verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
