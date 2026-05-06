"""Reference conftest for ha-testcontainer's own integration test suite (ha-tests/).

Configures ha_testcontainer fixtures and the scenario runner to use ha-tests/'s
local directories.  The session fixtures (ha, ha_url, ha_token,
ha_lovelace_url_path, ha_browser_context, ha_page) are provided automatically
by the ha_testcontainer pytest plugin (registered via entry_points["pytest11"]).

Environment variables used by the plugin fixtures
--------------------------------------------------
HA_VERSION
    Docker image tag (default: ``stable``).
HA_URL + HA_TOKEN
    Connect to a pre-running HA instance instead of starting Docker.
HA_SETUP_INTEGRATION
    Integration domain to configure after startup (e.g. ``uix``).
    Replaces the old ``LOVELACE_SETUP_INTEGRATION`` variable.
HA_EXTRA_CONFIG_DIR
    Directory merged on top of the config dir before container start.
    Replaces the old ``LOVELACE_EXTRA_CONFIG_DIR`` variable.
HA_PLUGINS_YAML
    Path to an alternative ``plugins.yaml``.
    Replaces the old ``LOVELACE_PLUGINS_YAML`` variable.
"""

from __future__ import annotations

import os
from pathlib import Path

# Point ha_testcontainer.pytest_plugin to ha-tests/-specific resources.
# These are read by the plugin's session fixtures at call time, so setting them
# here (at module import time, before fixtures run) is sufficient.
os.environ.setdefault("HA_CONFIG_PATH", str(Path(__file__).parent / "ha-config"))
os.environ.setdefault("HA_CUSTOM_COMPONENTS_PATH", str(Path(__file__).parent.parent / "custom_components"))
os.environ.setdefault("HA_PLUGINS_YAML", str(Path(__file__).parent / "plugins.yaml"))

# Configure the scenario runner to use ha-tests/'s local directories.
# This must run before test_scenarios.py is imported (pytest loads conftest.py
# files before test modules, so this ordering is guaranteed).
import ha_testcontainer.visual.scenario_runner as _sr  # noqa: E402

_sr.SCENARIOS_DIR = Path(__file__).parent / "visual" / "scenarios"
_sr.SNAPSHOTS_DIR = Path(__file__).parent / "visual" / "snapshots"
_sr.REPO_ROOT = Path(__file__).parent.parent
_sr.DOCS_SCENARIOS_DIR = _sr.REPO_ROOT / "docs" / "scenarios"

