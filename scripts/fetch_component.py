#!/usr/bin/env python3
"""Download a Home Assistant custom component from a GitHub release into custom_components/.

Usage
-----
    # Download the latest release of any component:
    python scripts/fetch_component.py owner/repo

    # Download a specific version:
    python scripts/fetch_component.py owner/repo 5.3.1

    # List available releases:
    python scripts/fetch_component.py owner/repo --list

    # Write to a custom destination instead of ./custom_components/:
    python scripts/fetch_component.py owner/repo --target-dir /path/to/custom_components

Examples
--------
    python scripts/fetch_component.py Lint-Free-Technology/uix
    python scripts/fetch_component.py Lint-Free-Technology/uix 5.3.1
    python scripts/fetch_component.py custom-cards/button-card --list

How it works
------------
The script downloads the GitHub release zip archive for the requested tag,
scans it for ``custom_components/<name>/`` sub-trees, and extracts each
discovered component into ``<target-dir>/<name>/``.  This works for any
repository that ships one or more custom components inside a top-level
``custom_components/`` directory, which is the standard Home Assistant
custom-component layout.

Why a script instead of a submodule or package dependency?
  Custom components typically ship their Python source and compiled JS
  (and other build artefacts) together in a GitHub release.  A script gives
  explicit version control without duplicating the built artefact in this
  repository.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

API_BASE = "https://api.github.com"
DEFAULT_TARGET_DIR = Path(__file__).parent.parent / "custom_components"

# Matches "owner/repo" where both parts are valid GitHub name segments.
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _validate_repo(repo: str) -> None:
    """Raise SystemExit if *repo* does not look like a valid ``owner/repo`` slug."""
    if not _REPO_RE.match(repo):
        sys.exit(
            f"Invalid repository format: {repo!r}. "
            "Expected 'owner/repo', e.g. 'Lint-Free-Technology/uix'."
        )


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------


def _github_get(path: str) -> dict | list:
    url = f"{API_BASE}{path}"
    req = Request(url, headers={"Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=30) as resp:  # noqa: S310 - known-safe URL
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def list_releases(repo: str) -> None:
    """Print the available releases for *repo* (``owner/repo`` format)."""
    _validate_repo(repo)
    releases = _github_get(f"/repos/{repo}/releases")
    if not releases:
        print(f"No releases found for {repo}.")
        return
    print(f"{'Tag':<20} {'Name'}")
    print("-" * 60)
    for r in releases:
        print(f"{r['tag_name']:<20} {r['name']}")


def resolve_version(repo: str, version: str | None) -> str:
    """Return the tag string (e.g. ``'v5.3.1'``) for the requested version.

    When *version* is ``None`` the latest release tag is returned.
    """
    _validate_repo(repo)
    if version is None:
        try:
            data = _github_get(f"/repos/{repo}/releases/latest")
        except HTTPError as exc:
            sys.exit(f"Could not fetch latest release for {repo}: {exc}")
        return data["tag_name"]

    tag = version if version.startswith("v") else f"v{version}"
    try:
        _github_get(f"/repos/{repo}/releases/tags/{tag}")
    except HTTPError as exc:
        sys.exit(f"Release {tag} not found for {repo}: {exc}")
    return tag


def fetch(
    repo: str,
    version: str | None = None,
    target_dir: Path | None = None,
) -> None:
    """Download and extract the ``custom_components/`` tree from a GitHub release.

    Parameters
    ----------
    repo:
        GitHub repository in ``owner/repo`` format, e.g. ``Lint-Free-Technology/uix``.
    version:
        Release version string without a ``v`` prefix, e.g. ``'5.3.1'``.
        Defaults to the latest published release.
    target_dir:
        Host directory to extract into.  Each discovered component is placed
        at ``<target_dir>/<component_name>/``.
        Defaults to ``./custom_components/`` relative to this repository root.
    """
    if target_dir is None:
        target_dir = DEFAULT_TARGET_DIR
    target_dir = Path(target_dir)

    tag = resolve_version(repo, version)
    print(f"Fetching {repo}@{tag} …")

    zip_url = f"https://github.com/{repo}/archive/refs/tags/{tag}.zip"
    req = Request(zip_url)
    with urlopen(req, timeout=60) as resp:  # noqa: S310 - known-safe URL
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Discover all custom_components/<name>/ entries in the archive.
        component_names: set[str] = set()
        for name in zf.namelist():
            parts = name.split("/")
            # Archive entries look like: "<repo>-<tag>/custom_components/<component>/..."
            if "custom_components" in parts:
                cc_idx = parts.index("custom_components")
                if cc_idx + 1 < len(parts) and parts[cc_idx + 1]:
                    component_names.add(parts[cc_idx + 1])

        if not component_names:
            sys.exit(
                f"No custom_components/ directory found in the {tag} release of {repo}.\n"
                "Ensure the repository uses the standard HA custom-component layout."
            )

        for component in sorted(component_names):
            dest = target_dir / component
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True)

            # Extract files belonging to this component.
            prefix = None
            for name in zf.namelist():
                if f"custom_components/{component}/" not in name:
                    continue
                if prefix is None:
                    prefix = name.split("custom_components/")[0]
                rel = name[len(prefix) + len(f"custom_components/{component}/"):]
                if not rel:
                    continue
                target = dest / rel
                if name.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))

            print(f"  ✓ {component} → {dest}")

    print(f"Done. {len(component_names)} component(s) installed from {repo}@{tag}.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "repo",
        help="GitHub repository in owner/repo format, e.g. Lint-Free-Technology/uix",
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Version tag to download, e.g. '5.3.1' (without 'v' prefix). "
             "Defaults to the latest release.",
    )
    parser.add_argument(
        "--target-dir",
        metavar="DIR",
        default=None,
        help=f"Directory to extract components into (default: {DEFAULT_TARGET_DIR})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available releases for the given repository and exit.",
    )
    args = parser.parse_args()

    target = Path(args.target_dir) if args.target_dir else None

    if args.list:
        list_releases(args.repo)
    else:
        fetch(args.repo, args.version, target)


if __name__ == "__main__":
    main()
