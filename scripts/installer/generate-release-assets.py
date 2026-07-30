#!/usr/bin/env python3
"""Generate checksums, release manifest, channel descriptor, and provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from tomllib import loads


ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(path: Path, url: str) -> dict[str, object]:
    return {
        "url": f"{url.rstrip('/')}/{path.name}",
        "sha256": digest(path),
        "size": path.stat().st_size,
    }


def plugin_version(version: str) -> str:
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(a|b|rc)(\d+)", version)
    if match is None:
        return version
    labels = {"a": "alpha", "b": "beta", "rc": "rc"}
    return f"{match.group(1)}-{labels[match.group(2)]}.{match.group(3)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--asset-base-url", required=True)
    parser.add_argument("--manifest-url", required=True)
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "unknown"))
    parser.add_argument("--uv-version", default="0.12.0")
    args = parser.parse_args()

    project = loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    directory = args.directory
    wheel = next(directory.glob(f"benchwork_arcana-{version}-*.whl"))
    sdist = directory / f"benchwork_arcana-{version}.tar.gz"
    plugin = directory / f"benchwork-codex-plugin-{version}.tar.gz"
    installer = directory / "install.sh"
    uv_installer = directory / "uv-install.sh"
    sbom = directory / "benchwork-sbom.cdx.json"
    provenance = directory / "benchwork-provenance.intoto.json"

    provenance.write_text(
        json.dumps(
            {
                "_type": "https://in-toto.io/Statement/v1",
                "subject": [
                    {"name": path.name, "digest": {"sha256": digest(path)}}
                    for path in (wheel, sdist, plugin, installer)
                ],
                "predicateType": "https://slsa.dev/provenance/v1",
                "predicate": {
                    "buildDefinition": {
                        "buildType": "https://benchwork.dev/build/release-assets/v1",
                        "externalParameters": {"version": version},
                        "resolvedDependencies": [
                            {"uri": f"git+https://github.com/Endofthestars/benchwork@{args.commit}"}
                        ],
                    },
                    "runDetails": {
                        "builder": {"id": "https://github.com/Endofthestars/benchwork/actions"},
                        "metadata": {
                            "invocationId": os.environ.get("GITHUB_RUN_ID", "local"),
                            "startedOn": datetime.now(UTC).isoformat(),
                        },
                    },
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    checksum_inputs = (wheel, sdist, plugin, installer, uv_installer, sbom, provenance)
    sums = directory / "SHA256SUMS"
    sums.write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in checksum_inputs),
        encoding="utf-8",
    )

    channel = "rc" if "rc" in version else "nightly" if "dev" in version else "stable"
    manifest = {
        "schema_version": "benchwork-release-manifest/1.0",
        "version": version,
        "tag": f"v{version}",
        "channel": channel,
        "python_requirement": ">=3.11",
        "package": {
            "name": "benchwork-arcana",
            "requirement": f"benchwork-arcana=={version}",
            "wheel": artifact(wheel, args.asset_base_url),
            "sdist": artifact(sdist, args.asset_base_url),
        },
        "plugin": {
            "name": "benchwork",
            "version": plugin_version(version),
            "runtime_requirement": f"benchwork-arcana=={version}",
            "archive": artifact(plugin, args.asset_base_url),
        },
        "installer": artifact(installer, args.asset_base_url),
        "bootstrap": {
            "uv": {
                "version": args.uv_version,
                "installer": artifact(uv_installer, args.asset_base_url),
            }
        },
        "assets": {
            "sha256sums": artifact(sums, args.asset_base_url),
            "sbom": artifact(sbom, args.asset_base_url),
            "provenance": artifact(provenance, args.asset_base_url),
        },
    }
    manifest_path = directory / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    channel_descriptor = {
        "schema_version": "benchwork-release-channel/1.0",
        "channel": channel,
        "version": version,
        "manifest_url": args.manifest_url,
        "manifest_sha256": digest(manifest_path),
        "manifest_size": manifest_path.stat().st_size,
    }
    (directory / f"{channel}.json").write_text(
        json.dumps(channel_descriptor, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
