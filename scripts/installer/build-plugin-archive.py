#!/usr/bin/env python3
"""Build a deterministic, versioned local-marketplace plugin archive."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def files_to_archive() -> list[tuple[Path, Path]]:
    sources = (
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / "plugins" / "benchwork",
    )
    result: list[tuple[Path, Path]] = []
    for source in sources:
        if source.is_file():
            result.append((source, source.relative_to(ROOT)))
            continue
        for path in sorted(source.rglob("*")):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
            ):
                result.append((path, path.relative_to(ROOT)))
    return result


def build(output: Path, epoch: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                directories: set[Path] = set()
                entries = files_to_archive()
                for _, relative in entries:
                    directories.update(relative.parents)
                for directory in sorted(
                    (path for path in directories if path != Path(".")),
                    key=lambda path: (len(path.parts), path.as_posix()),
                ):
                    info = tarfile.TarInfo(directory.as_posix())
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = epoch
                    archive.addfile(info)
                for source, relative in entries:
                    blob = source.read_bytes()
                    info = tarfile.TarInfo(relative.as_posix())
                    info.size = len(blob)
                    info.mode = 0o755 if os.access(source, os.X_OK) else 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = epoch
                    archive.addfile(info, io.BytesIO(blob))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--epoch",
        type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")),
    )
    args = parser.parse_args()
    build(args.output, args.epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
