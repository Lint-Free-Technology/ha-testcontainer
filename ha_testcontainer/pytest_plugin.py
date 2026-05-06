"""ha_testcontainer pytest plugin.

Provides session-scoped fixtures for Home Assistant container management and
Playwright visual testing.  Registered automatically via the ``pytest11``
entry-point when ``ha-testcontainer[test]`` is installed — no ``conftest.py``
import is required.

Session fixtures
----------------
ha
    Session-scoped HA instance (Docker container or external pre-running server).
ha_url
    Base URL of the running HA instance.
ha_token
    Long-lived access token for the admin user.
ha_lovelace_url_path
    URL path of the dedicated Lovelace test dashboard (created once per session).

Visual fixtures (requires pytest-playwright)
--------------------------------------------
ha_browser_context
    Pre-authenticated Playwright browser context (session-scoped).
ha_page
    A fresh Playwright page inside the shared authenticated context (function-scoped).

Environment variables
---------------------
HA_VERSION
    Docker image tag (default: ``stable``).
HA_URL + HA_TOKEN
    When both are set, connect to a pre-running instance instead of starting Docker.
HA_CONFIG_PATH
    Host directory to mount as ``/config``.  When unset the container's built-in
    config is used (HA will start with demo data only).
HA_CUSTOM_COMPONENTS_PATH
    Host directory to mount as ``/config/custom_components``.
HA_EXTRA_CONFIG_DIR
    Directory whose contents are merged on top of ``HA_CONFIG_PATH`` before
    the container starts (component-specific themes, foundry files, etc.).
HA_PLUGINS_YAML
    Path to a ``plugins.yaml`` file listing Lovelace plugins to download.
    When unset, no plugins are downloaded.
HA_LOCAL_PLUGINS_DIR
    Path to a directory containing local ``.js`` plugin files to copy into
    ``www/`` and register as Lovelace resources.  Use this to serve your own
    dashboard plugin from the local repository without publishing a release.
HA_SETUP_INTEGRATION
    Integration domain to configure via the config-flow API after startup
    (e.g. ``uix``).  Leave unset to skip.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any

import pytest
import requests
import websocket
from ha_testcontainer import HATestContainer, HAVersion
from ha_testcontainer.plugins import download_lovelace_plugins
from ha_testcontainer.visual import PAGE_LOAD_TIMEOUT, inject_ha_token


# ---------------------------------------------------------------------------
# Proxy for a pre-running HA instance (HA_URL + HA_TOKEN env vars)
# ---------------------------------------------------------------------------


class _ExternalHA:
    """Thin proxy for a Home Assistant instance started externally (e.g. ha_server.py).

    Exposes the same interface used by the test fixtures (``get_url``,
    ``get_token``, ``api``, ``_ws_call``, ``setup_integration``) so the
    rest of the test infrastructure works unchanged when connecting to a
    pre-running container instead of spinning up a fresh one.
    """

    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token

    def get_url(self) -> str:
        return self._url

    def get_token(self) -> str:
        return self._token

    def api(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        if not path.startswith("/api/"):
            path = f"/api/{path.lstrip('/')}"
        url = f"{self._url}{path}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        headers.setdefault("Content-Type", "application/json")
        return requests.request(method, url, headers=headers, timeout=30, **kwargs)

    def _ws_call(self, command: dict[str, Any]) -> dict[str, Any]:
        ws_url = (
            self._url.replace("http://", "ws://").replace("https://", "wss://")
            + "/api/websocket"
        )
        ws = websocket.create_connection(ws_url, timeout=15)
        try:
            ws.recv()  # auth_required
            ws.send(json.dumps({"type": "auth", "access_token": self._token}))
            auth_result = json.loads(ws.recv())
            if auth_result.get("type") != "auth_ok":
                raise RuntimeError(f"WebSocket auth failed: {auth_result}")
            ws.send(json.dumps(command))
            return json.loads(ws.recv())
        finally:
            ws.close()

    def setup_integration(self, domain: str) -> dict[str, Any]:
        """Set up a HA integration — a no-op when it's already configured."""
        resp = self.api("POST", "/api/config/config_entries/flow", json={"handler": domain})
        if resp.status_code not in (200, 201, 400):
            resp.raise_for_status()
        return resp.json()

    def stop(self) -> None:
        """No-op — the caller is responsible for teardown."""

    def __repr__(self) -> str:
        return f"_ExternalHA({self._url!r})"


# ---------------------------------------------------------------------------
# Session-scoped HA container
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_version() -> str:
    return os.environ.get("HA_VERSION", HAVersion.STABLE)


@pytest.fixture(scope="session")
def ha(ha_version: str, tmp_path_factory):
    """Session-scoped HA instance with optional custom components and config.

    **Normal mode** (default): starts a fresh Docker container, copies the
    config directory (if ``HA_CONFIG_PATH`` is set) to a temporary location
    for isolation, optionally merges extra config (``HA_EXTRA_CONFIG_DIR``),
    downloads Lovelace plugins (``HA_PLUGINS_YAML``), mounts custom
    components (``HA_CUSTOM_COMPONENTS_PATH``), sets up an integration
    (``HA_SETUP_INTEGRATION``), and tears everything down at the end.

    **Fast-iteration mode**: when ``HA_URL`` *and* ``HA_TOKEN`` are both set,
    the fixture skips Docker entirely and connects to a pre-running instance::

        # Terminal 1 — start persistent HA
        HA_CONFIG_PATH=ha-config python -m ha_testcontainer.ha_server

        # Terminal 2 — iterate quickly
        source .ha_env
        pytest tests/visual/ -k my_scenario
    """
    ha_url_env = os.environ.get("HA_URL")
    ha_token_env = os.environ.get("HA_TOKEN")
    if ha_url_env and ha_token_env:
        yield _ExternalHA(ha_url_env, ha_token_env)
        return

    # ---- Normal Docker-container mode ----

    ha_tmp = tmp_path_factory.mktemp("ha-state")

    # Copy the base HA config into the temp dir (if configured).
    ha_config_env = os.environ.get("HA_CONFIG_PATH", "").strip()
    if ha_config_env:
        ha_config_dir = Path(ha_config_env)
        if ha_config_dir.exists():
            shutil.copytree(str(ha_config_dir), str(ha_tmp), dirs_exist_ok=True)

    # Merge any component-specific config on top (HA_EXTRA_CONFIG_DIR).
    extra_config_env = os.environ.get("HA_EXTRA_CONFIG_DIR", "").strip()
    if extra_config_env:
        extra_config = Path(extra_config_env)
        if extra_config.exists():
            shutil.copytree(str(extra_config), str(ha_tmp), dirs_exist_ok=True)

    # Download Lovelace plugins (HA_PLUGINS_YAML override).
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

    # Mount local custom_components (HA_CUSTOM_COMPONENTS_PATH).
    custom_components_env = os.environ.get("HA_CUSTOM_COMPONENTS_PATH", "").strip()
    if custom_components_env:
        custom_components_dir = Path(custom_components_env)
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

    yield container
    container.stop()


# ---------------------------------------------------------------------------
# Derived fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_url(ha) -> str:
    """Base URL of the running HA instance, e.g. ``http://localhost:8123``."""
    return ha.get_url()


@pytest.fixture(scope="session")
def ha_token(ha) -> str:
    """Long-lived access token for the admin user."""
    return ha.get_token()


# ---------------------------------------------------------------------------
# Named Lovelace test dashboard
# ---------------------------------------------------------------------------

#: URL path for the dedicated Lovelace test dashboard created at session start.
LOVELACE_TEST_DASHBOARD_URL_PATH = "ha-tests"


def _create_dashboard(ha, url_path: str, title: str) -> None:
    """Create a named Lovelace dashboard via the WebSocket API.

    Any existing dashboard with the same ``url_path`` is silently ignored so
    the fixture is idempotent across sessions.
    """
    result: dict[str, Any] = {}
    exc_holder: list[BaseException] = []

    def _run() -> None:
        try:
            result.update(
                ha._ws_call(
                    {
                        "id": 1,
                        "type": "lovelace/dashboards/create",
                        "url_path": url_path,
                        "title": title,
                        "show_in_sidebar": False,
                        "require_admin": False,
                    }
                )
            )
        except BaseException as e:  # noqa: BLE001
            exc_holder.append(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=30)
    if t.is_alive():
        raise TimeoutError("lovelace/dashboards/create timed out after 30 seconds")
    if exc_holder:
        raise exc_holder[0]
    if not result.get("success"):
        error = result.get("error") or {}
        already_exists = error.get("code") == "url_path_already_in_use" or (
            error.get("code") == "home_assistant_error"
            and error.get("translation_key") == "url_already_exists"
        )
        if not already_exists:
            raise RuntimeError(f"lovelace/dashboards/create failed: {result}")


@pytest.fixture(scope="session")
def ha_lovelace_url_path(ha) -> str:
    """URL path of the dedicated Lovelace test dashboard.

    Creates the dashboard once per session and returns its ``url_path`` so
    individual test fixtures can push configs to it and navigate to its views.
    """
    _create_dashboard(ha, LOVELACE_TEST_DASHBOARD_URL_PATH, "Lovelace Tests")
    return LOVELACE_TEST_DASHBOARD_URL_PATH


# ---------------------------------------------------------------------------
# Playwright fixtures
# ---------------------------------------------------------------------------
# These require pytest-playwright.  They are defined unconditionally here —
# if pytest-playwright is not installed, the fixtures simply won't be usable,
# but the plugin itself will still load and provide the HA container fixtures.


@pytest.fixture(scope="session")
def ha_browser_context(browser, ha_url: str, ha_token: str):
    """A Playwright browser context pre-authenticated with HA.

    Uses :func:`~ha_testcontainer.visual.inject_ha_token` to seed the
    ``hassTokens`` localStorage entry before the first navigation, bypassing
    the HA login screen for all pages in this context.
    """
    from playwright.sync_api import BrowserContext  # noqa: PLC0415

    context: BrowserContext = browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = context.new_page()
    inject_ha_token(page, ha_url, ha_token)
    page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
    page.close()
    yield context
    context.close()


@pytest.fixture()
def ha_page(ha_browser_context):
    """A fresh Playwright page inside the pre-authenticated browser context.

    Auth state (localStorage ``hassTokens``) is inherited from the shared
    browser context seeded by ``ha_browser_context``.
    """
    from playwright.sync_api import Page  # noqa: PLC0415

    page: Page = ha_browser_context.new_page()
    yield page
    page.close()
