"""Tests for HATestContainer — container lifecycle and REST API.

These tests verify:
  - The container starts and HA becomes reachable.
  - Onboarding is completed automatically (a token is available).
  - The HA REST API is reachable and returns expected data.
  - Demo entities are available via the built-in demo integration.
  - The storage-mode Lovelace API endpoint is reachable.
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


class TestStorageDashboard:
    def test_lovelace_storage_endpoint(self, ha):
        """The storage-mode Lovelace dashboard config endpoint is reachable."""
        result = ha._ws_call({"id": 1, "type": "lovelace/config"})
        assert result.get("success") is True or (
            result.get("success") is False and result.get("error", {}).get("code") == "config_not_found"
        )

    def test_push_lovelace_config(self, ha):
        """A Lovelace config can be pushed via the WebSocket API."""
        config = {"title": "Test", "views": [{"title": "Test View", "path": "test"}]}
        ha.push_lovelace_config(config)
        result = ha._ws_call({"id": 1, "type": "lovelace/config"})
        assert result.get("success") is True
        assert result.get("result", {}).get("title") == "Test"

