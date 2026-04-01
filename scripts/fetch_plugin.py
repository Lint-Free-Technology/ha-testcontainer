#!/usr/bin/env python3
"""Download a Home Assistant frontend plugin from a GitHub release and register it as a
Lovelace resource in YAML mode.

Usage
-----
    # Download the latest release of a frontend plugin:
    python scripts/fetch_plugin.py owner/repo

    # Download a specific version:
    python scripts/fetch_plugin.py owner/repo 1.2.3

    # List available releases:
    python scripts/fetch_plugin.py owner/repo --list

    # Custom HA config directory (default: ./ha-config):
    python scripts/fetch_plugin.py owner/repo --config-dir /path/to/config

    # Override the resource URL path segment (default: derived from repo name):
    python scripts/fetch_plugin.py owner/repo --plugin-name my-plugin

    # Override the Lovelace resource type (default: module):
    python scripts/fetch_plugin.py owner/repo --resource-type js

Examples
--------
    python scripts/fetch_plugin.py custom-cards/button-card
    python scripts/fetch_plugin.py thomasloven/lovelace-card-mod
    python scripts/fetch_plugin.py kalkih/mini-graph-card 0.12.1

What a "frontend plugin" is
---------------------------
A Home Assistant frontend plugin is a JavaScript module (a ``.js`` file) that
the HA frontend loads at runtime.  Unlike custom *components* (Python packages
under ``custom_components/``), frontend plugins live in the ``www/`` directory
of the HA config tree and are declared as Lovelace resources.

HA automatically serves every file inside ``/config/www/`` at the URL path
``/local/``.  A file placed at::

    ha-config/www/dashboard/button-card/button-card.js

is therefore reachable from the HA frontend at::

    http://localhost:8123/local/dashboard/button-card/button-card.js

This script downloads the plugin JS and registers it in
``ha-config/lovelace_resources.yaml``, which ``configuration.yaml`` includes
with ``resources: !include lovelace_resources.yaml``.

How JS files are discovered in the release
------------------------------------------
1. Release **assets** (attached files) are checked first.  Any ``.js`` file
   found is downloaded directly.
2. If no ``.js`` asset exists, each ``.zip`` asset is scanned and any ``.js``
   files found inside are extracted.
3. As a final fallback, the GitHub source archive (zip) is downloaded and
   scanned for ``.js`` files in ``dist/``, the archive root, or any sub-tree.

Why not HACS?
  HACS is a full HA integration with its own UI.  This script is a lightweight
  alternative suitable for test environments and CI — zero HA integration
  needed, no UI, no dependencies beyond the Python standard library.
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
REPO_ROOT = Path(__file__).parent.parent

# Default HA config directory (contains configuration.yaml, www/, etc.)
DEFAULT_CONFIG_DIR = REPO_ROOT / "ha-config"

# Within ha-config/, plugins are stored here and served at /local/dashboard/...
PLUGIN_SUBDIR = Path("www") / "dashboard"

# The resources YAML file included by configuration.yaml
RESOURCES_FILE = "lovelace_resources.yaml"

# Matches "owner/repo" where both parts are valid GitHub name segments.
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_repo(repo: str) -> None:
    """Raise SystemExit if *repo* does not look like a valid ``owner/repo`` slug."""
    if not _REPO_RE.match(repo):
        sys.exit(
            f"Invalid repository format: {repo!r}. "
            "Expected 'owner/repo', e.g. 'custom-cards/button-card'."
        )


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------


def _github_get(path: str) -> dict | list:
    url = f"{API_BASE}{path}"
    req = Request(url, headers={"Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=30) as resp:  # noqa: S310 - known-safe URL
        return json.loads(resp.read())


def _download_bytes(url: str, timeout: int = 60) -> bytes:
    req = Request(url)
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 - known-safe URL
        return resp.read()


# ---------------------------------------------------------------------------
# Version resolution
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


def resolve_version(repo: str, version: str | None) -> tuple[str, list[dict]]:
    """Return ``(tag, assets)`` for the requested version.

    When *version* is ``None`` the latest release is used.  ``assets`` is the
    list of release asset objects from the GitHub API.
    """
    _validate_repo(repo)
    if version is None:
        try:
            data = _github_get(f"/repos/{repo}/releases/latest")
        except HTTPError as exc:
            sys.exit(f"Could not fetch latest release for {repo}: {exc}")
    else:
        # Try the version string as-is first, then with a 'v' prefix, because
        # different repositories use different tagging conventions.
        candidates = [version] if version.startswith("v") else [f"v{version}", version]
        data = None
        for tag in candidates:
            try:
                data = _github_get(f"/repos/{repo}/releases/tags/{tag}")
                break
            except HTTPError:
                continue
        if data is None:
            sys.exit(
                f"Release '{version}' not found for {repo}. "
                "Run with --list to see available tags."
            )

    return data["tag_name"], data.get("assets", [])


# ---------------------------------------------------------------------------
# JS discovery
# ---------------------------------------------------------------------------


def _js_files_from_zip(zip_bytes: bytes) -> dict[str, bytes]:
    """Return ``{filename: content}`` for all ``.js`` files in *zip_bytes*.

    Files in ``dist/`` are preferred; if none are found there, all ``.js``
    files in the archive root and ``src/`` are returned.  If still nothing is
    found, every ``.js`` file in the archive is returned.
    """
    found: dict[str, bytes] = {}
    dist_found: dict[str, bytes] = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.endswith(".js"):
                continue
            parts = name.split("/")
            basename = parts[-1]
            if not basename:
                continue
            content = zf.read(name)
            # Prefer files from dist/ or a top-level dist-like path.
            if "dist" in parts:
                dist_found[basename] = content
            found[basename] = content

    return dist_found if dist_found else found


def _find_js_in_release(
    repo: str,
    tag: str,
    assets: list[dict],
) -> dict[str, bytes]:
    """Download and return ``{filename: content}`` for JS files in the release.

    Strategy (in priority order):
    1. Direct ``.js`` release assets.
    2. ``.zip`` release assets containing ``.js`` files.
    3. GitHub source archive (fallback).
    """
    # 1 — direct .js assets
    js_assets = [a for a in assets if a["name"].endswith(".js")]
    if js_assets:
        result: dict[str, bytes] = {}
        for asset in js_assets:
            print(f"  Downloading asset: {asset['name']} …")
            result[asset["name"]] = _download_bytes(asset["browser_download_url"])
        return result

    # 2 — .zip assets
    zip_assets = [a for a in assets if a["name"].endswith(".zip")]
    for asset in zip_assets:
        print(f"  Scanning zip asset: {asset['name']} …")
        zip_bytes = _download_bytes(asset["browser_download_url"])
        js_files = _js_files_from_zip(zip_bytes)
        if js_files:
            return js_files

    # 3 — source archive fallback
    source_url = f"https://github.com/{repo}/archive/refs/tags/{tag}.zip"
    print(f"  No JS assets found; falling back to source archive …")
    zip_bytes = _download_bytes(source_url)
    js_files = _js_files_from_zip(zip_bytes)
    if not js_files:
        sys.exit(
            f"No JavaScript files found in the {tag} release of {repo}.\n"
            "This repository may not be a frontend plugin, or JS files are not "
            "included in its releases."
        )
    return js_files


# ---------------------------------------------------------------------------
# Lovelace resources YAML management
# ---------------------------------------------------------------------------


def _load_resources(resources_path: Path) -> list[dict[str, str]]:
    """Parse ``lovelace_resources.yaml`` and return a list of resource dicts.

    Only ``url`` and ``type`` keys are preserved.  Lines that cannot be parsed
    are silently ignored so the file can include comments and blank lines.
    """
    if not resources_path.exists():
        return []

    resources: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for raw in resources_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "[]":
            continue
        # New list item
        if line.startswith("- "):
            if current:
                resources.append(current)
            current = {}
            line = line[2:]
        # key: value pair
        if ":" in line:
            key, _, val = line.partition(":")
            current[key.strip()] = val.strip()

    if current:
        resources.append(current)

    return resources


def _save_resources(resources_path: Path, resources: list[dict[str, str]]) -> None:
    """Write *resources* back to *resources_path* in a tidy YAML list format."""
    lines = [
        "# Lovelace frontend resources - managed by scripts/fetch_plugin.py",
        "# Add plugins with:  python scripts/fetch_plugin.py owner/repo",
        "# Remove entries manually or re-run the script.",
        "#",
    ]
    if not resources:
        lines.append("[]")
    else:
        for entry in resources:
            lines.append(f"- url: {entry['url']}")
            lines.append(f"  type: {entry['type']}")

    resources_path.write_text("\n".join(lines) + "\n")


def _register_resource(
    resources_path: Path,
    url: str,
    resource_type: str,
) -> None:
    """Add or update the *url* entry in ``lovelace_resources.yaml``."""
    resources = _load_resources(resources_path)

    # Replace existing entry with the same URL, or append a new one.
    existing = next((r for r in resources if r.get("url") == url), None)
    if existing:
        existing["type"] = resource_type
        print(f"  Updated resource: {url}")
    else:
        resources.append({"url": url, "type": resource_type})
        print(f"  Registered resource: {url}")

    _save_resources(resources_path, resources)


# ---------------------------------------------------------------------------
# Main fetch logic
# ---------------------------------------------------------------------------


def fetch(
    repo: str,
    version: str | None = None,
    config_dir: Path | None = None,
    plugin_name: str | None = None,
    resource_type: str = "module",
) -> None:
    """Download a frontend plugin and register it as a Lovelace resource.

    Parameters
    ----------
    repo:
        GitHub repository in ``owner/repo`` format.
    version:
        Release version string without a ``v`` prefix, e.g. ``'1.2.3'``.
        Defaults to the latest published release.
    config_dir:
        Path to the HA config directory that contains ``configuration.yaml``.
        Defaults to ``./ha-config/``.
    plugin_name:
        Sub-directory name under ``www/dashboard/`` where the JS file(s) will
        be placed.  Defaults to the repository name portion of *repo*, e.g.
        ``button-card`` for ``custom-cards/button-card``.
    resource_type:
        Lovelace resource type.  Almost always ``'module'`` (ES module).
        Use ``'js'`` for legacy non-module scripts.
    """
    if config_dir is None:
        config_dir = DEFAULT_CONFIG_DIR
    config_dir = Path(config_dir)

    if plugin_name is None:
        # Derive from the repo name, stripping common "lovelace-" prefix.
        plugin_name = repo.split("/")[-1].removeprefix("lovelace-")

    tag, assets = resolve_version(repo, version)
    print(f"Fetching plugin {repo}@{tag} …")

    js_files = _find_js_in_release(repo, tag, assets)

    # Write JS files into <config_dir>/www/dashboard/<plugin_name>/
    plugin_dir = config_dir / PLUGIN_SUBDIR / plugin_name
    if plugin_dir.exists():
        try:
            shutil.rmtree(plugin_dir)
        except OSError as exc:
            sys.exit(f"Could not remove existing plugin directory {plugin_dir}: {exc}")
    try:
        plugin_dir.mkdir(parents=True)
    except OSError as exc:
        sys.exit(f"Could not create plugin directory {plugin_dir}: {exc}")

    resources_path = config_dir / RESOURCES_FILE

    for filename, content in sorted(js_files.items()):
        dest = plugin_dir / filename
        dest.write_bytes(content)
        print(f"  ✓ {filename} → {dest.relative_to(REPO_ROOT)}")

        # Register each JS file as a separate Lovelace resource.
        local_url = f"/local/dashboard/{plugin_name}/{filename}"
        _register_resource(resources_path, local_url, resource_type)

    print(
        f"\nDone. {len(js_files)} file(s) installed from {repo}@{tag}.\n"
        f"Resources registered in: {resources_path.relative_to(REPO_ROOT)}\n"
        "\nMake sure configuration.yaml contains:\n"
        "  lovelace:\n"
        "    resources: !include lovelace_resources.yaml"
    )


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
        help="GitHub repository in owner/repo format, e.g. custom-cards/button-card",
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Version tag to download, e.g. '1.2.3' (without 'v' prefix). "
             "Defaults to the latest release.",
    )
    parser.add_argument(
        "--config-dir",
        metavar="DIR",
        default=None,
        help=f"HA config directory containing configuration.yaml "
             f"(default: {DEFAULT_CONFIG_DIR})",
    )
    parser.add_argument(
        "--plugin-name",
        metavar="NAME",
        default=None,
        help="Sub-directory name under www/dashboard/ for this plugin "
             "(default: derived from repo name)",
    )
    parser.add_argument(
        "--resource-type",
        choices=["module", "js"],
        default="module",
        help="Lovelace resource type: 'module' (ES module, default) or 'js' "
             "(legacy script)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available releases for the given repository and exit.",
    )
    args = parser.parse_args()

    config = Path(args.config_dir) if args.config_dir else None

    if args.list:
        list_releases(args.repo)
    else:
        fetch(
            args.repo,
            args.version,
            config_dir=config,
            plugin_name=args.plugin_name,
            resource_type=args.resource_type,
        )


if __name__ == "__main__":
    main()
