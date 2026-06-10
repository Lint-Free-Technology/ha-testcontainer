"""Unit tests for the pytest plugin helpers — no network or Docker required."""

from __future__ import annotations

from unittest.mock import MagicMock

import ha_testcontainer.pytest_plugin as plugin


class TestDashboardExistenceCheck:
    def test_detects_existing_dashboard(self):
        ha = MagicMock()
        ha._ws_call.return_value = {
            "success": True,
            "result": {
                "dashboards": [
                    {"url_path": "ha-tests"},
                    {"url_path": "other"},
                ]
            },
        }

        assert plugin._dashboard_url_path_exists(ha, "ha-tests") is True
        ha._ws_call.assert_called_once_with({"id": 1, "type": "config/lovelace/dashboards/list"})

    def test_missing_dashboard_returns_false(self):
        ha = MagicMock()
        ha._ws_call.return_value = {"success": True, "result": {"dashboards": []}}

        assert plugin._dashboard_url_path_exists(ha, "ha-tests") is False


class TestCreateDashboard:
    def test_skips_create_when_dashboard_already_exists(self, monkeypatch):
        ha = MagicMock()
        monkeypatch.setattr(plugin, "_dashboard_url_path_exists", lambda _ha, _url_path: True)

        plugin._create_dashboard(ha, "ha-tests", "Lovelace Tests")

        ha._ws_call.assert_not_called()

    def test_creates_dashboard_when_missing(self, monkeypatch):
        ha = MagicMock()
        monkeypatch.setattr(plugin, "_dashboard_url_path_exists", lambda _ha, _url_path: False)
        ha._ws_call.return_value = {"success": True, "result": None}

        plugin._create_dashboard(ha, "ha-tests", "Lovelace Tests")

        ha._ws_call.assert_called_once_with(
            {
                "id": 1,
                "type": "lovelace/dashboards/create",
                "url_path": "ha-tests",
                "title": "Lovelace Tests",
                "show_in_sidebar": False,
                "require_admin": False,
            }
        )
