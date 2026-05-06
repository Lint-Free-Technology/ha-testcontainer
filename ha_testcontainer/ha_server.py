#!/usr/bin/env python3
"""Start a persistent HA test container for fast iterative development.

Spin up Home Assistant once, then run pytest as many times as you like without
waiting for HA to boot on every invocation.

Usage
-----
In **Terminal 1** (keep running):

    python -m ha_testcontainer.ha_server
    # or via the Makefile alias:
    make ha-tests-up

The script prints two ``export`` lines as soon as HA is ready::

    export HA_URL=http://localhost:12345
    export HA_TOKEN=eyJ...

In **Terminal 2** (source and iterate):

    source .ha_env                                              # set HA_URL / HA_TOKEN
    pytest tests/visual/test_scenarios.py -k my_scenario       # fast – no boot wait
    pytest tests/visual/test_scenarios.py -k my_scenario       # iterate again instantly

Press **Ctrl-C** in Terminal 1 to stop HA and clean up.

Environment variables
---------------------
HA_VERSION
    Docker image tag to use.  Defaults to ``stable``.
    Set to ``beta``, ``dev``, or a pinned version such as ``2024.6.0``.
HA_CONFIG_PATH
    Path to the HA config directory to mount as ``/config``.
    Defaults to ``ha-config/`` in the current directory.
HA_CUSTOM_COMPONENTS_PATH
    Path to the custom components directory.
    Defaults to ``custom_components/`` in the current directory.
HA_SETUP_INTEGRATION
    Integration domain to configure after startup (e.g. ``uix``).
    Leave unset or empty to skip automatic integration setup.
HA_EXTRA_CONFIG_DIR
    Path to a directory whose contents are copied on top of the config
    directory before the container starts (e.g. component-specific themes).
HA_PLUGINS_YAML
    Path to a ``plugins.yaml`` file listing Lovelace plugins to download.
    When unset no plugins are downloaded.
HA_LOCAL_PLUGINS_DIR
    Path to a directory containing local ``.js`` plugin files to copy into
    ``www/`` and register as Lovelace resources.  Use this to serve your own
    dashboard plugin from the local repository without publishing a release.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
from pathlib import Path


def main() -> None:
    try:
        from ha_testcontainer import HATestContainer, HAVersion
        from ha_testcontainer.plugins import download_lovelace_plugins
    except ImportError:
        print(
            "ha_testcontainer is not installed.  Run:\n"
            "  pip install -e '.[test]'",
            file=sys.stderr,
        )
        sys.exit(1)

    ha_version = os.environ.get("HA_VERSION", HAVersion.STABLE)

    # Resolve paths from env vars, falling back to cwd-relative defaults.
    cwd = Path.cwd()
    ha_config_env = os.environ.get("HA_CONFIG_PATH", "").strip()
    ha_config_dir = Path(ha_config_env) if ha_config_env else cwd / "ha-config"

    custom_components_env = os.environ.get("HA_CUSTOM_COMPONENTS_PATH", "").strip()
    custom_components_dir = (
        Path(custom_components_env) if custom_components_env else cwd / "custom_components"
    )

    env_file = cwd / ".ha_env"

    print(f"Starting Home Assistant {ha_version} container…", file=sys.stderr)

    import tempfile

    ha_tmp = Path(tempfile.mkdtemp(prefix="ha-state-"))

    if ha_config_dir.exists():
        shutil.copytree(str(ha_config_dir), str(ha_tmp), dirs_exist_ok=True)

    # Merge component-specific config additions on top (HA_EXTRA_CONFIG_DIR).
    extra_config_env = os.environ.get("HA_EXTRA_CONFIG_DIR", "").strip()
    if extra_config_env:
        extra_config = Path(extra_config_env)
        if extra_config.exists():
            shutil.copytree(str(extra_config), str(ha_tmp), dirs_exist_ok=True)

    plugins_yaml_env = os.environ.get("HA_PLUGINS_YAML", "").strip()
    local_plugins_dir_env = os.environ.get("HA_LOCAL_PLUGINS_DIR", "").strip()
    download_lovelace_plugins(
        ha_tmp / "www",
        plugins_yaml=Path(plugins_yaml_env) if plugins_yaml_env else None,
        local_plugins_dir=Path(local_plugins_dir_env) if local_plugins_dir_env else None,
    )

    container = HATestContainer(
        version=ha_version,
        config_path=ha_tmp,
    )
    if custom_components_dir.exists() and any(custom_components_dir.iterdir()):
        container.with_volume_mapping(
            str(custom_components_dir.resolve()),
            "/config/custom_components",
            "rw",
        )

    container.start()

    integration = os.environ.get("HA_SETUP_INTEGRATION", "").strip()
    if integration:
        container.setup_integration(integration)

    url = container.get_url()
    token = container.get_token()

    env_content = (
        f"export HA_URL={url}\n"
        f"export HA_TOKEN={token}\n"
        f"export HA_CONFIG_DIR={ha_tmp}\n"
    )

    env_file.write_text(env_content)

    # Print a clean separator so the user can easily spot the env vars.
    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Home Assistant is ready at {url}", file=sys.stderr)
    print(f"  Env vars written to  {env_file.name}", file=sys.stderr)
    print(file=sys.stderr)
    print("  In another terminal run:", file=sys.stderr)
    print(f"    source {env_file.name}", file=sys.stderr)
    print("    pytest tests/visual/test_scenarios.py -k <scenario_id>", file=sys.stderr)
    print(file=sys.stderr)
    print("  Press Ctrl-C here to stop HA.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Also echo the env vars to stdout for scripting convenience.
    print(env_content, end="")

    def _shutdown(sig: int, _frame: object) -> None:
        print("\nStopping Home Assistant container…", file=sys.stderr)
        try:
            container.stop()
        except Exception:  # noqa: BLE001
            pass
        env_file.unlink(missing_ok=True)
        shutil.rmtree(ha_tmp, ignore_errors=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.pause()


if __name__ == "__main__":
    main()
