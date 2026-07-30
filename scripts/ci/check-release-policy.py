#!/usr/bin/env python3
"""Prevent a stable release while public naming surfaces are provisional."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRERELEASE = re.compile(r"(?:a|b|rc|dev)\d*$")


def main() -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    if PRERELEASE.search(version):
        print(f"Development release {version} is permitted.")
        return 0

    compatibility = (ROOT / "docs" / "en" / "COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )
    if "Current provisional value" in compatibility or "not frozen" in compatibility:
        print(
            "Stable release blocked: distribution, CLI, import, and schema "
            "domain names are not frozen."
        )
        return 1
    print(f"Stable release policy satisfied for {version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
