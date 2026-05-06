#!/usr/bin/env python3
"""Shim — start a persistent HA test container for ha-tests/ development.

The authoritative implementation has moved into ``ha_testcontainer.ha_server``.
This shim sets the ha-tests/-specific default paths (HA_CONFIG_PATH,
HA_CUSTOM_COMPONENTS_PATH, HA_PLUGINS_YAML) before delegating.

Usage
-----
    python ha-tests/ha_server.py
    # or via the Makefile alias:
    make ha-tests-up

Environment variables (set by this shim if not already set)
------------------------------------------------------------
HA_CONFIG_PATH
    Defaults to ``ha-tests/ha-config/``.
HA_CUSTOM_COMPONENTS_PATH
    Defaults to ``custom_components/`` at the repository root.
HA_PLUGINS_YAML
    Defaults to ``ha-tests/plugins.yaml``.

All other env vars (HA_VERSION, HA_SETUP_INTEGRATION, HA_EXTRA_CONFIG_DIR,
HA_URL, HA_TOKEN) are passed through unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent

os.environ.setdefault("HA_CONFIG_PATH", str(_HERE / "ha-config"))
os.environ.setdefault("HA_CUSTOM_COMPONENTS_PATH", str(_REPO_ROOT / "custom_components"))
os.environ.setdefault("HA_PLUGINS_YAML", str(_HERE / "plugins.yaml"))

from ha_testcontainer.ha_server import main  # noqa: E402

if __name__ == "__main__":
    main()

