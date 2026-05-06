"""Download or copy Lovelace plugins for the HA test instance.

This module is responsible for making each Lovelace plugin available in the
``www/`` directory that will be served at ``/local/`` by the HA test container,
and for registering those resources in ``lovelace_resources.yaml`` so that
Home Assistant loads them automatically at start-up.

It is called by both ``conftest.py`` (pytest session) and ``ha_server.py``
(persistent dev server) immediately after the static ``ha-config/`` tree is
copied into a temporary directory, before the HA Docker container starts.

Adding a hosted (GitHub-released) plugin
-----------------------------------------
Add an entry to your ``plugins.yaml`` with:

``repo``
    GitHub repository in ``owner/name`` format.
``asset``
    Name of the JS file to download.  Resolved in this order:

    1. As a release asset attached to the latest GitHub release.
    2. As a raw file at the repo root for the release tag.
    3. As a raw file inside the ``dist/`` sub-directory for the release tag.
``filename``
    Filename to write inside *www_dir* (usually the same as ``asset``).

Adding a local plugin (your own dashboard plugin under development)
--------------------------------------------------------------------
Option A — ``local_path`` entry in ``plugins.yaml``:

.. code-block:: yaml

    - local_path: ../dist/my-plugin.js   # relative to the yaml file or absolute
      filename: my-plugin.js

The file is copied directly into *www_dir* without any network request.

Option B — ``HA_LOCAL_PLUGINS_DIR`` environment variable (or the
*local_plugins_dir* parameter of :func:`download_lovelace_plugins`):

    Point ``HA_LOCAL_PLUGINS_DIR`` at a directory that contains ``.js``
    files.  Every ``*.js`` file found there is copied into *www_dir* and
    registered as a Lovelace resource.
"""

from __future__ import annotations

import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Any

import requests
import yaml

# ---------------------------------------------------------------------------
# Plugin registry — loaded from plugins.yaml in the same directory
# ---------------------------------------------------------------------------

_PLUGINS_YAML: Path | None = None

_GITHUB_API = "https://api.github.com"
_RAW_BASE = "https://raw.githubusercontent.com"
_TIMEOUT = 30  # seconds

# Trusted hostnames for plugin asset downloads.
_TRUSTED_DOWNLOAD_HOSTS = frozenset(
    {
        "github.com",
        "objects.githubusercontent.com",
        "raw.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "githubusercontent.com",
    }
)


def _load_plugins(plugins_yaml: Path | None = None) -> list[dict[str, str]]:
    """Load the plugin registry from *plugins_yaml*.

    Defaults to :data:`_PLUGINS_YAML` when *plugins_yaml* is ``None``.
    Returns an empty list when no path is configured.
    """
    path = plugins_yaml if plugins_yaml is not None else _PLUGINS_YAML
    if path is None:
        return []
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a YAML list, got {type(data).__name__}")
    return data


def _github_headers() -> dict[str, str]:
    """Return request headers, adding Bearer auth when GITHUB_TOKEN is set."""
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def download_lovelace_plugins(
    www_dir: Path,
    *,
    plugins_yaml: Path | None = None,
    local_plugins_dir: Path | None = None,
) -> None:
    """Download or copy each registered plugin into *www_dir*.

    The plugin list is read from *plugins_yaml* (defaults to
    ``ha-tests/plugins.yaml`` in the same directory as this module).  Pass an
    explicit path to use a component-specific registry instead — for example
    ``ha-tests/uix/plugins.yaml`` for UIX tests.

    In addition to hosted (GitHub-released) plugins, the yaml file may contain
    entries with a ``local_path`` key that point to a JS file on disk.  Relative
    paths are resolved relative to the directory containing *plugins_yaml*.

    Extra local plugins can also be supplied via *local_plugins_dir*: every
    ``*.js`` file found at the top level of that directory is copied into
    *www_dir* and registered as a Lovelace resource.

    Creates *www_dir* if it does not exist.  Files are always overwritten so
    the latest version is guaranteed on every fresh container startup.

    Also writes ``lovelace_resources.yaml`` in the parent directory (the HA
    config root) so that Home Assistant registers the plugin JS files as
    Lovelace resources at startup — no WebSocket API calls required.

    Parameters
    ----------
    www_dir:
        The ``www/`` subdirectory inside the HA config temp dir.  Files
        placed here are served at ``/local/<filename>`` by Home Assistant.
    plugins_yaml:
        Override the default ``plugins.yaml`` path.  When ``None``, uses
        the ``plugins.yaml`` file next to this module.
    local_plugins_dir:
        Optional directory whose ``*.js`` files are copied into *www_dir*
        and registered as Lovelace resources.  Corresponds to the
        ``HA_LOCAL_PLUGINS_DIR`` environment variable.
    """
    www_dir.mkdir(parents=True, exist_ok=True)
    plugins = _load_plugins(plugins_yaml)

    yaml_dir = plugins_yaml.parent if plugins_yaml is not None else None
    for plugin in plugins:
        if "local_path" in plugin:
            _copy_local_plugin(www_dir, plugin, yaml_dir)
        else:
            _download_plugin(www_dir, plugin)

    dir_entries: list[dict[str, str]] = []
    if local_plugins_dir is not None:
        dir_entries = _copy_dir_plugins(www_dir, local_plugins_dir)

    _write_lovelace_resources(www_dir.parent, plugins + dir_entries)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_lovelace_resources(config_dir: Path, plugins: list[dict[str, str]]) -> None:
    """Write ``lovelace_resources.yaml`` in *config_dir* from *plugins*.

    Each plugin's JS file is served at ``/local/<filename>`` and registered
    as a ``module`` resource.  Home Assistant loads this file at startup via
    ``resources: !include lovelace_resources.yaml`` in ``configuration.yaml``,
    so no WebSocket API calls are needed for resource registration.
    """
    resources_path = config_dir / "lovelace_resources.yaml"
    lines = [
        "# Lovelace frontend resources — generated by plugins.py from plugins.yaml.",
        "# Do not edit manually; this file is overwritten at container startup.",
        "#",
    ]
    if not plugins:
        lines.append("[]")
    else:
        for plugin in plugins:
            lines.append(f"- url: /local/{plugin['filename']}")
            lines.append(f"  type: module")
    resources_path.write_text("\n".join(lines) + "\n")


def _download_plugin(www_dir: Path, plugin: dict[str, str]) -> None:
    """Fetch *plugin*'s latest release asset and write it to *www_dir*.

    Resolution order:
    1. Release asset attached to the latest GitHub release.
    2. Raw file at the repo root for the release tag.
    3. Raw file in the ``dist/`` folder for the release tag.
    """
    repo = plugin["repo"]
    asset_name = plugin["asset"]
    filename = plugin["filename"]

    release = _get_latest_release(repo)
    tag = release.get("tag_name", "unknown")

    asset_url = _find_asset_url(release, asset_name)
    if asset_url is None:
        asset_url = _find_raw_url(repo, tag, asset_name)

    dest = www_dir / filename
    _stream_download(asset_url, dest)
    print(f"[plugins] Downloaded {repo}@{tag} → {dest}", flush=True)


def _get_latest_release(repo: str) -> dict[str, Any]:
    """Return the latest release metadata from the GitHub API."""
    url = f"{_GITHUB_API}/repos/{repo}/releases/latest"
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_github_headers())
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch latest release for {repo!r} from GitHub API: {exc}"
        ) from exc
    return resp.json()


def _find_asset_url(release: dict[str, Any], asset_name: str) -> str | None:
    """Return the browser_download_url for *asset_name* in *release*, or ``None``."""
    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            return asset["browser_download_url"]
    return None


def _find_raw_url(repo: str, tag: str, asset_name: str) -> str:
    """Return the raw GitHub URL for *asset_name* in *repo* at *tag*.

    Tries the repo root first, then the ``dist/`` sub-directory.

    Raises ``RuntimeError`` if the file cannot be found at either location.
    """
    candidates = [
        f"{_RAW_BASE}/{repo}/{tag}/{asset_name}",
        f"{_RAW_BASE}/{repo}/{tag}/dist/{asset_name}",
    ]
    headers = _github_headers()
    for url in candidates:
        try:
            resp = requests.head(url, timeout=_TIMEOUT, headers=headers, allow_redirects=True)
            if resp.status_code == 200:
                return url
        except requests.RequestException:
            continue
    raise RuntimeError(
        f"Could not find {asset_name!r} for {repo}@{tag} as a release asset, "
        f"at the repo root, or in the dist/ folder."
    )


def _stream_download(url: str, dest: Path) -> None:
    """Stream-download *url* and write to *dest*.

    Raises ``ValueError`` if *url* is not on a trusted GitHub domain to
    prevent unexpected redirects to untrusted hosts.
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if not any(host == h or host.endswith(f".{h}") for h in _TRUSTED_DOWNLOAD_HOSTS):
        raise ValueError(
            f"Refusing to download plugin asset from untrusted host {host!r}. "
            f"Expected one of: {sorted(_TRUSTED_DOWNLOAD_HOSTS)}"
        )
    try:
        resp = requests.get(url, timeout=_TIMEOUT, stream=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download {url!r}: {exc}") from exc
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=65536):
            fh.write(chunk)


def _copy_local_plugin(
    www_dir: Path,
    plugin: dict[str, str],
    yaml_dir: Path | None,
) -> None:
    """Copy the local JS file referenced by *plugin* into *www_dir*.

    ``plugin["local_path"]`` may be absolute or relative; relative paths are
    resolved against *yaml_dir* (the directory containing ``plugins.yaml``).
    """
    local_path = Path(plugin["local_path"])
    if not local_path.is_absolute() and yaml_dir is not None:
        local_path = yaml_dir / local_path
    local_path = local_path.resolve()
    if not local_path.is_file():
        raise FileNotFoundError(
            f"Local plugin file not found: {local_path} "
            f"(specified as local_path={plugin['local_path']!r})"
        )
    filename = plugin["filename"]
    dest = www_dir / filename
    shutil.copy2(local_path, dest)
    print(f"[plugins] Copied local plugin {local_path} → {dest}", flush=True)


def _copy_dir_plugins(www_dir: Path, local_plugins_dir: Path) -> list[dict[str, str]]:
    """Copy every ``*.js`` file in *local_plugins_dir* into *www_dir*.

    Returns a list of plugin dicts (``{"filename": ...}``) suitable for
    inclusion in ``lovelace_resources.yaml``.
    """
    entries: list[dict[str, str]] = []
    for js_file in sorted(local_plugins_dir.glob("*.js")):
        dest = www_dir / js_file.name
        shutil.copy2(js_file, dest)
        print(f"[plugins] Copied local plugin {js_file} → {dest}", flush=True)
        entries.append({"filename": js_file.name})
    return entries
