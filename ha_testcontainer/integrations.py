"""Download Home Assistant integrations from YAML configuration.

This module installs custom components into a ``custom_components`` directory
and returns the integration domains that should be configured via HA's
config-flow API.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import zipfile
from pathlib import Path

import requests
import yaml

_GITHUB_API = "https://api.github.com"
_ARCHIVE_BASE = "https://github.com"
_TIMEOUT = 30

# Matches "owner/repo" where both parts are valid GitHub name segments.
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def install_integrations(
    custom_components_dir: Path,
    *,
    integrations_yaml: Path | None = None,
) -> list[str]:
    """Install integrations from YAML into *custom_components_dir*.

    Returns the list of integration domains that should be configured via
    ``setup_integration`` after Home Assistant starts.
    """
    custom_components_dir.mkdir(parents=True, exist_ok=True)
    integrations = _load_integrations(integrations_yaml)

    domains: list[str] = []
    for item in integrations:
        repo = _read_repo(item)
        version = _read_optional_str(item, "version")
        explicit_domain = _read_optional_str(item, "domain")

        release = _get_release(repo, version)
        tag = release["tag_name"]
        archive_url = f"{_ARCHIVE_BASE}/{repo}/archive/refs/tags/{tag}.zip"
        downloaded_components = _extract_custom_components(
            archive_url,
            custom_components_dir,
            repo=repo,
            tag=tag,
        )

        if explicit_domain:
            domains.append(explicit_domain)
        elif len(downloaded_components) == 1:
            domains.append(next(iter(downloaded_components)))
        else:
            raise ValueError(
                f"Integration entry for {repo!r} must include 'domain' when the "
                f"release contains multiple custom_components: {sorted(downloaded_components)}"
            )

    return _dedupe_preserving_order(domains)


def _load_integrations(integrations_yaml: Path | None) -> list[dict[str, object]]:
    if integrations_yaml is None:
        return []
    with integrations_yaml.open() as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(
            f"{integrations_yaml} must contain a YAML list, got {type(data).__name__}"
        )
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"{integrations_yaml} item #{idx + 1} must be a mapping, got {type(item).__name__}"
            )
    return data


def _read_repo(item: dict[str, object]) -> str:
    repo = item.get("repo")
    if not isinstance(repo, str) or not repo.strip():
        raise ValueError("Each integration entry must define a non-empty 'repo' string.")
    repo = repo.strip()
    if not _REPO_RE.match(repo):
        raise ValueError(
            f"Invalid integration repo format: {repo!r}. Expected 'owner/repo'."
        )
    return repo


def _read_optional_str(item: dict[str, object], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Integration field {key!r} must be a string when provided.")
    stripped = value.strip()
    return stripped or None


def _github_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _get_release(repo: str, version: str | None) -> dict[str, object]:
    if version is None:
        url = f"{_GITHUB_API}/repos/{repo}/releases/latest"
    else:
        tag = version if version.startswith("v") else f"v{version}"
        url = f"{_GITHUB_API}/repos/{repo}/releases/tags/{tag}"

    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_github_headers())
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch release metadata for integration repo {repo!r}: {exc}"
        ) from exc
    data = resp.json()
    if not isinstance(data, dict) or "tag_name" not in data:
        raise RuntimeError(f"Unexpected release payload for {repo!r}: missing 'tag_name'.")
    return data


def _extract_custom_components(
    archive_url: str,
    custom_components_dir: Path,
    *,
    repo: str,
    tag: str,
) -> set[str]:
    try:
        resp = requests.get(archive_url, timeout=60, headers=_github_headers())
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to download integration archive for {repo}@{tag}: {exc}"
        ) from exc

    component_names: set[str] = set()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            parts = name.split("/")
            if "custom_components" not in parts:
                continue
            idx = parts.index("custom_components")
            if idx + 1 < len(parts) and parts[idx + 1]:
                component_names.add(parts[idx + 1])

        if not component_names:
            raise RuntimeError(
                f"No custom_components found in release archive for {repo}@{tag}."
            )

        for component in sorted(component_names):
            dest = custom_components_dir / component
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)

            prefix: str | None = None
            for name in zf.namelist():
                marker = f"custom_components/{component}/"
                if marker not in name:
                    continue
                if prefix is None:
                    prefix = name.split(marker, maxsplit=1)[0]
                rel = name[len(prefix) + len(marker):]
                if not rel:
                    continue
                target = dest / rel
                if name.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))

    print(f"[integrations] Installed {repo}@{tag} → {sorted(component_names)}", flush=True)
    return component_names


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
