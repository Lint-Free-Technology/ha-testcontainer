"""Unit tests for scenario_runner interaction types — no Docker or browser required.

Covers interaction dispatch logic using mocks so that a running Playwright
browser is not needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

import ha_testcontainer.visual.scenario_runner as sr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page() -> MagicMock:
    """Return a lightweight mock that records Playwright Page calls."""
    return MagicMock()


# ---------------------------------------------------------------------------
# set_viewport interaction
# ---------------------------------------------------------------------------


class TestSetViewportInteraction:
    """run_interactions dispatches set_viewport correctly."""

    def test_set_viewport_calls_set_viewport_size(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": 375, "height": 812},
            ]
        }
        sr.run_interactions(page, scenario)
        page.set_viewport_size.assert_called_once_with({"width": 375, "height": 812})

    def test_set_viewport_no_settle_ms_by_default(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": 1280, "height": 800},
            ]
        }
        sr.run_interactions(page, scenario)
        page.wait_for_timeout.assert_not_called()

    def test_set_viewport_settle_ms_waits(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": 768, "height": 1024, "settle_ms": 300},
            ]
        }
        sr.run_interactions(page, scenario)
        page.set_viewport_size.assert_called_once_with({"width": 768, "height": 1024})
        page.wait_for_timeout.assert_called_once_with(300)

    def test_set_viewport_coerces_string_dimensions(self):
        """width/height may arrive as strings from YAML and must be coerced to int."""
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": "390", "height": "844"},
            ]
        }
        sr.run_interactions(page, scenario)
        page.set_viewport_size.assert_called_once_with({"width": 390, "height": 844})

    def test_unknown_type_raises(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "not_a_real_type"},
            ]
        }
        with pytest.raises(ValueError, match="Unknown interaction type"):
            sr.run_interactions(page, scenario)
