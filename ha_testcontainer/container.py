"""Home Assistant test container.

Provides :class:`HATestContainer`, a :class:`~testcontainers.core.container.DockerContainer`
subclass that:

* Starts the official Home Assistant Docker image (stable / beta / dev / pinned version).
* Performs the HA onboarding flow programmatically so tests don't need to touch the UI.
* Creates and exposes a long-lived API token for REST and WebSocket access.
* Optionally mounts a custom config directory and/or a ``custom_components`` directory.
* Works as a context manager or with explicit ``start()`` / ``stop()`` calls.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Registry prefix for the official Home Assistant image.
HA_IMAGE = "ghcr.io/home-assistant/home-assistant"

#: Port that Home Assistant listens on inside the container.
HA_PORT = 8123

#: How long (seconds) to wait for the web-server to become reachable.
STARTUP_TIMEOUT = 120

#: Default credentials used for the programmatic onboarding step.
DEFAULT_USERNAME = "testadmin"
DEFAULT_PASSWORD = "testpassword123"  # noqa: S105 - test-only credential


class HAVersion:
    """Convenience constants for well-known HA image tags."""

    STABLE = "stable"
    BETA = "beta"
    DEV = "dev"


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class HATestContainer(DockerContainer):
    """Disposable Home Assistant container for automated tests.

    Parameters
    ----------
    version:
        Docker image tag.  Use :class:`HAVersion` constants or pass a
        specific release string such as ``"2024.6.0"``.
    config_path:
        Host path to mount as ``/config`` inside the container.  When
        omitted HA creates a minimal default configuration at start-up.
    custom_components_path:
        Host path to mount as ``/config/custom_components``.  Ignored when
        *config_path* is given and already contains a ``custom_components``
        sub-directory (HA will pick it up automatically from the config
        volume).
    username:
        Admin username created during programmatic onboarding.
    password:
        Admin password created during programmatic onboarding.
    port:
        Container port to expose (default: 8123).
    """

    def __init__(
        self,
        version: str = HAVersion.STABLE,
        config_path: str | Path | None = None,
        custom_components_path: str | Path | None = None,
        username: str = DEFAULT_USERNAME,
        password: str = DEFAULT_PASSWORD,
        port: int = HA_PORT,
    ) -> None:
        image = f"{HA_IMAGE}:{version}"
        super().__init__(image=image)

        self._ha_port = port
        self._username = username
        self._password = password
        self._token: str | None = None

        self.with_exposed_ports(port)
        self.with_env("TZ", "UTC")

        if config_path is not None:
            resolved = Path(config_path).resolve()
            self.with_volume_mapping(str(resolved), "/config", "rw")
        elif custom_components_path is not None:
            resolved_cc = Path(custom_components_path).resolve()
            self.with_volume_mapping(str(resolved_cc), "/config/custom_components", "rw")

    # ------------------------------------------------------------------
    # Context-manager helpers
    # ------------------------------------------------------------------

    def __enter__(self) -> "HATestContainer":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> "HATestContainer":
        """Start the container and complete onboarding."""
        super().start()
        self._wait_for_ha()
        self._perform_onboarding()
        return self

    def get_url(self) -> str:
        """Return the base URL of the running HA instance."""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self._ha_port)
        return f"http://{host}:{port}"

    def get_token(self) -> str:
        """Return the long-lived access token for the admin user.

        Raises :class:`RuntimeError` if the container has not been started yet.
        """
        if self._token is None:
            raise RuntimeError(
                "No token available – call start() first or use as a context manager."
            )
        return self._token

    def api(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an authenticated REST API call.

        Parameters
        ----------
        method:
            HTTP verb (``"GET"``, ``"POST"``, …).
        path:
            API path, with or without a leading ``/api/``.
            E.g. ``"states"`` or ``"/api/states"``.
        **kwargs:
            Forwarded to :func:`requests.request` (``json``, ``params``, …).

        Returns
        -------
        requests.Response
        """
        if not path.startswith("/api/"):
            path = f"/api/{path.lstrip('/')}"
        url = f"{self.get_url()}{path}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.get_token()}"
        headers.setdefault("Content-Type", "application/json")
        return requests.request(method, url, headers=headers, timeout=30, **kwargs)

    def setup_integration(self, domain: str) -> dict[str, Any]:
        """Set up a HA integration via the config-flow API.

        Initiates the config flow for *domain* and, if it completes in one
        step (e.g. UIX), returns the resulting entry data.

        Parameters
        ----------
        domain:
            Integration domain, e.g. ``"uix"``.

        Returns
        -------
        dict
            The response JSON from the config-flow endpoint.
        """
        resp = self.api(
            "POST",
            "/api/config/config_entries/flow",
            json={"handler": domain},
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_ha(self) -> None:
        """Block until HA's web server responds (or *STARTUP_TIMEOUT* elapses)."""
        # First wait for the "Home Assistant is running" log line so we know
        # the internal startup sequence is complete.
        try:
            wait_for_logs(self, "Home Assistant is running", timeout=STARTUP_TIMEOUT)
        except Exception:  # noqa: BLE001
            pass  # fall through to the HTTP poll below

        # Then confirm the HTTP endpoint is reachable.
        url = f"{self.get_url()}/api/"
        deadline = time.monotonic() + STARTUP_TIMEOUT
        last_exc: Exception | None = None
        while time.monotonic() < deadline:
            try:
                resp = requests.get(url, timeout=5)
                # 200 = already set up, 401 = running but needs auth,
                # 403 = forbidden (onboarding state)
                if resp.status_code in (200, 401, 403):
                    return
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
            time.sleep(2)

        raise TimeoutError(
            f"Home Assistant did not become ready within {STARTUP_TIMEOUT}s."
            + (f"  Last error: {last_exc}" if last_exc else "")
        )

    def _needs_onboarding(self) -> bool:
        """Return True when the HA onboarding wizard has not been completed."""
        try:
            resp = requests.get(
                f"{self.get_url()}/api/onboarding",
                timeout=10,
            )
            if resp.status_code == 200:
                steps = resp.json()
                return any(not s.get("done", False) for s in steps)
        except requests.exceptions.RequestException:
            pass
        return False

    def _perform_onboarding(self) -> None:
        """Run through the HA onboarding API to create the admin user and token."""
        if not self._needs_onboarding():
            # Already onboarded (e.g. pre-populated .storage files).
            # Try to authenticate with the supplied credentials.
            self._token = self._password_login()
            return

        base_url = self.get_url()
        client_id = f"{base_url}/"

        # Step 1 – create the first admin user.
        resp = requests.post(
            f"{base_url}/api/onboarding/users",
            json={
                "client_id": client_id,
                "name": "Test Admin",
                "username": self._username,
                "password": self._password,
                "language": "en",
            },
            timeout=30,
        )
        resp.raise_for_status()
        auth_code = resp.json()["auth_code"]

        # Step 2 – exchange the auth code for an access token.
        token_resp = requests.post(
            f"{base_url}/auth/token",
            data=urlencode(
                {
                    "client_id": client_id,
                    "grant_type": "authorization_code",
                    "code": auth_code,
                }
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        token_resp.raise_for_status()
        short_lived_token = token_resp.json()["access_token"]

        # Step 3 – complete remaining onboarding steps (core_config, analytics,
        # integration).  These are optional from an API standpoint but HA marks
        # them as required before the UI proceeds.
        for step in ("core_config", "analytics", "integration"):
            requests.post(
                f"{base_url}/api/onboarding/{step}",
                json={"client_id": client_id},
                headers={"Authorization": f"Bearer {short_lived_token}"},
                timeout=15,
            )

        # Step 4 – mint a long-lived token so tests are not time-limited.
        llt_resp = requests.post(
            f"{base_url}/api/auth/long_lived_access_token",
            json={"lifespan": 3650, "client_name": "ha-testcontainer"},
            headers={"Authorization": f"Bearer {short_lived_token}"},
            timeout=15,
        )
        llt_resp.raise_for_status()
        self._token = llt_resp.json()["token"]

    def _password_login(self) -> str:
        """Authenticate with username/password and return a long-lived token.

        Used when the container is started with a pre-populated config that
        already has a user (i.e. onboarding is skipped).
        """
        base_url = self.get_url()
        client_id = f"{base_url}/"

        # Initiate login flow.
        flow_resp = requests.post(
            f"{base_url}/auth/login_flow",
            json={
                "client_id": client_id,
                "handler": ["homeassistant", None],
                "redirect_uri": client_id,
            },
            timeout=15,
        )
        flow_resp.raise_for_status()
        flow_id = flow_resp.json()["flow_id"]

        # Submit credentials.
        cred_resp = requests.post(
            f"{base_url}/auth/login_flow/{flow_id}",
            json={"username": self._username, "password": self._password},
            timeout=15,
        )
        cred_resp.raise_for_status()
        auth_code = cred_resp.json()["result"]

        # Exchange code for token.
        token_resp = requests.post(
            f"{base_url}/auth/token",
            data=urlencode(
                {
                    "client_id": client_id,
                    "grant_type": "authorization_code",
                    "code": auth_code,
                }
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        token_resp.raise_for_status()
        short_lived_token = token_resp.json()["access_token"]

        # Mint a long-lived token.
        llt_resp = requests.post(
            f"{base_url}/api/auth/long_lived_access_token",
            json={"lifespan": 3650, "client_name": "ha-testcontainer"},
            headers={"Authorization": f"Bearer {short_lived_token}"},
            timeout=15,
        )
        llt_resp.raise_for_status()
        return llt_resp.json()["token"]
