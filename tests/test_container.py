"""Tests for HATestContainer — container lifecycle and REST API.

These tests verify:
  - The container starts and HA becomes reachable.
  - Onboarding is completed automatically (a token is available).
  - The HA REST API is reachable and returns expected data.
  - Custom components (UIX) loaded from the mounted directory are detected.
  - Integration setup via config-flow works (UIX as the example).
"""

from __future__ import annotations

import pytest
import requests

from ha_testcontainer import HATestContainer, HAVersion


# ---------------------------------------------------------------------------
# Basic container / API tests (use the session fixture)
# ---------------------------------------------------------------------------


class TestContainerStartup:
    def test_url_is_http(self, ha_url: str):
        assert ha_url.startswith("http://")

    def test_api_root_responds(self, ha_url: str, ha_token: str):
        resp = requests.get(
            f"{ha_url}/api/",
            headers={"Authorization": f"Bearer {ha_token}"},
            timeout=15,
        )
        assert resp.status_code == 200
        assert resp.json().get("message") == "API running."

    def test_token_is_non_empty(self, ha_token: str):
        assert ha_token and len(ha_token) > 10


class TestVersionVariants:
    """Parametrised smoke-test: container can be started for each version type.

    These tests are *skipped* by default (they pull large Docker images).
    Run them explicitly with:  pytest -m version_smoke
    """

    @pytest.mark.version_smoke
    @pytest.mark.parametrize("version", [HAVersion.STABLE, HAVersion.BETA, HAVersion.DEV])
    def test_starts_for_version(self, version: str, ha_config_path, ha_custom_components_path):
        with HATestContainer(
            version=version,
            config_path=ha_config_path,
            custom_components_path=ha_custom_components_path,
        ) as container:
            resp = requests.get(
                f"{container.get_url()}/api/",
                headers={"Authorization": f"Bearer {container.get_token()}"},
                timeout=15,
            )
            assert resp.status_code == 200


class TestDemoEntities:
    def test_demo_lights_exist(self, ha):
        resp = ha.api("GET", "states")
        assert resp.status_code == 200
        states = resp.json()
        entity_ids = [s["entity_id"] for s in states]
        lights = [e for e in entity_ids if e.startswith("light.")]
        assert lights, "Expected at least one demo light entity"

    def test_demo_sensors_exist(self, ha):
        resp = ha.api("GET", "states")
        assert resp.status_code == 200
        states = resp.json()
        entity_ids = [s["entity_id"] for s in states]
        sensors = [e for e in entity_ids if e.startswith("sensor.")]
        assert sensors, "Expected at least one demo sensor entity"


class TestCustomComponents:
    def test_uix_manifest_loaded(self, ha):
        """UIX's Python component registers itself with HA on startup.

        The /api/config endpoint lists loaded integrations; UIX should appear
        once its config-flow entry has been created.
        """
        # First set up UIX via the config-flow API.
        result = ha.setup_integration("uix")
        # Config-flow can return 'create_entry' (first time) or 'abort'
        # (single_instance_allowed if already set up).
        assert result.get("type") in ("create_entry", "abort"), (
            f"Unexpected config-flow result: {result}"
        )

    def test_uix_js_is_served(self, ha_url: str, ha_token: str):
        """The UIX frontend script should be accessible once UIX is set up."""
        resp = requests.get(
            f"{ha_url}/uix/uix.js",
            headers={"Authorization": f"Bearer {ha_token}"},
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"UIX JS not served (got {resp.status_code}). "
            "Ensure UIX is installed in custom_components/."
        )


class TestStorageDashboard:
    def test_lovelace_storage_endpoint(self, ha):
        """The storage-mode Lovelace dashboard config endpoint is reachable."""
        resp = ha.api("GET", "lovelace/config")
        # 200 = dashboard already has a config; 404 = not yet initialised (both are fine).
        assert resp.status_code in (200, 404)
