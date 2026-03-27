"""Shared pytest fixtures for ha-testcontainer tests.

The session-scoped ``ha`` fixture starts one Home Assistant container for the
whole test run and tears it down at the end.  All tests that need a running HA
instance should request ``ha`` (or one of the derived fixtures below).

Environment variables
---------------------
HA_VERSION
    Docker image tag to use.  Defaults to ``stable``.
    Set to ``beta``, ``dev``, or a pinned version such as ``2024.6.0``.
HA_CONFIG_PATH
    Host path to mount as ``/config``.  Defaults to the ``ha-config/``
    directory at the repository root.
HA_CUSTOM_COMPONENTS_PATH
    Host path to mount as ``/config/custom_components``.  Defaults to the
    ``custom_components/`` directory at the repository root.
    Ignored when ``HA_CONFIG_PATH`` is set (the custom_components dir must
    live inside the mounted config tree in that case).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from ha_testcontainer import HATestContainer, HAVersion

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
HA_CONFIG_DIR = REPO_ROOT / "ha-config"
CUSTOM_COMPONENTS_DIR = REPO_ROOT / "custom_components"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_uix_present() -> None:
    """Download UIX if it is not already present in custom_components/."""
    uix_dir = CUSTOM_COMPONENTS_DIR / "uix"
    if uix_dir.is_dir() and (uix_dir / "manifest.json").exists():
        return
    print(
        "\n[conftest] UIX not found in custom_components/ — running fetch_uix.py …",
        flush=True,
    )
    script = REPO_ROOT / "scripts" / "fetch_uix.py"
    subprocess.run(
        [sys.executable, str(script)],
        check=True,
        cwd=REPO_ROOT,
    )


# ---------------------------------------------------------------------------
# Session-scoped HA container
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_version() -> str:
    return os.environ.get("HA_VERSION", HAVersion.STABLE)


@pytest.fixture(scope="session")
def ha_config_path() -> Path:
    return Path(os.environ.get("HA_CONFIG_PATH", str(HA_CONFIG_DIR)))


@pytest.fixture(scope="session")
def ha_custom_components_path() -> Path:
    return Path(os.environ.get("HA_CUSTOM_COMPONENTS_PATH", str(CUSTOM_COMPONENTS_DIR)))


@pytest.fixture(scope="session")
def ha(ha_version: str, ha_config_path: Path, ha_custom_components_path: Path):
    """Session-scoped HATestContainer.

    Mounts ``ha-config/`` as ``/config`` and ``custom_components/`` as
    ``/config/custom_components``.  UIX is automatically downloaded if it
    is not already present.
    """
    _ensure_uix_present()
    container = HATestContainer(
        version=ha_version,
        config_path=ha_config_path,
        custom_components_path=ha_custom_components_path,
    )
    container.start()
    yield container
    container.stop()


# ---------------------------------------------------------------------------
# Derived fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_url(ha: HATestContainer) -> str:
    """Base URL of the running HA instance, e.g. ``http://localhost:8123``."""
    return ha.get_url()


@pytest.fixture(scope="session")
def ha_token(ha: HATestContainer) -> str:
    """Long-lived access token for the admin user."""
    return ha.get_token()
