#!/usr/bin/env python3
"""Download the UIX custom component from GitHub into custom_components/.

Usage
-----
    python scripts/fetch_uix.py              # latest release
    python scripts/fetch_uix.py 5.3.1       # specific version (without "v" prefix)
    python scripts/fetch_uix.py --list      # list available releases

The script fetches the release zip from GitHub, extracts the
``custom_components/uix/`` subtree, and places it at
``<repo-root>/custom_components/uix/``.

Why a script instead of a submodule or package dependency?
  UIX ships its Python source and compiled JS together in a single GitHub
  release.  A script gives us explicit version control without duplicating
  the built artefact in this repository.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

REPO = "Lint-Free-Technology/uix"
API_BASE = "https://api.github.com"
TARGET_DIR = Path(__file__).parent.parent / "custom_components"


def _github_get(path: str) -> dict | list:
    url = f"{API_BASE}{path}"
    req = Request(url, headers={"Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=30) as resp:  # noqa: S310 - known-safe URL
        return json.loads(resp.read())


def list_releases() -> None:
    releases = _github_get(f"/repos/{REPO}/releases")
    print(f"{'Tag':<15} {'Name'}")
    print("-" * 50)
    for r in releases:
        print(f"{r['tag_name']:<15} {r['name']}")


def resolve_version(version: str | None) -> str:
    """Return the tag string (e.g. 'v5.3.1') for the requested version."""
    if version is None:
        data = _github_get(f"/repos/{REPO}/releases/latest")
        return data["tag_name"]
    tag = version if version.startswith("v") else f"v{version}"
    # Validate the tag exists.
    try:
        _github_get(f"/repos/{REPO}/releases/tags/{tag}")
    except HTTPError as exc:
        sys.exit(f"Release {tag} not found: {exc}")
    return tag


def fetch(version: str | None = None) -> None:
    tag = resolve_version(version)
    print(f"Fetching UIX {tag} …")

    zip_url = f"https://github.com/{REPO}/archive/refs/tags/{tag}.zip"
    req = Request(zip_url)
    with urlopen(req, timeout=60) as resp:  # noqa: S310 - known-safe URL
        data = resp.read()

    dest = TARGET_DIR / "uix"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        prefix = None
        for name in zf.namelist():
            if "custom_components/uix/" in name:
                if prefix is None:
                    # Determine the top-level archive folder, e.g. "uix-5.3.1/"
                    prefix = name.split("custom_components/")[0]
                rel = name[len(prefix) + len("custom_components/uix/"):]
                if not rel:
                    continue
                target = dest / rel
                if name.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))

    print(f"UIX {tag} installed to {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "version",
        nargs="?",
        help="Version to download, e.g. '5.3.1'.  Defaults to the latest release.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available UIX releases and exit.",
    )
    args = parser.parse_args()

    if args.list:
        list_releases()
    else:
        fetch(args.version)


if __name__ == "__main__":
    main()
