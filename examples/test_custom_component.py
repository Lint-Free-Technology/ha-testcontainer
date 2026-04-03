"""Boilerplate visual regression tests for a Home Assistant custom component.

Copy this file into your component's ``tests/visual/`` directory and replace
the placeholder values marked with ``TODO`` comments to create repeatable
visual tests against a real Home Assistant instance managed by ha-testcontainer.

Quickstart
----------
1. Install ha-testcontainer and its visual extras in your project::

       pip install ha-testcontainer[test]
       playwright install chromium

2. Fetch your custom component into ``custom_components/``::

       python scripts/fetch_component.py owner/your-repo

3. Copy this file to ``tests/visual/test_<your_component>.py`` and fill in
   the TODO sections.

4. Run::

       # First run — creates PNG baselines in tests/visual/snapshots/
       pytest tests/visual/ -v

       # Subsequent runs — compares screenshots against the baselines
       pytest tests/visual/ -v

       # Refresh baselines after an intentional visual change
       SNAPSHOT_UPDATE=1 pytest tests/visual/ -v

Fixtures available (from ha-testcontainer's conftest)
------------------------------------------------------
ha          HATestContainer session instance — call ha.api(...) for REST calls
ha_url      base URL of the running HA instance, e.g. http://localhost:<port>
ha_token    long-lived access token for the admin user
ha_page     pre-authenticated Playwright Page (new page per test)

See ha-testcontainer's tests/visual/conftest.py for the full fixture source.
"""

from __future__ import annotations

# TODO: replace with your component's domain string, e.g. "my_component"
COMPONENT_DOMAIN = "my_component"

# TODO: replace with the human-readable integration name shown in HA Settings,
#       e.g. "My Awesome Component"
COMPONENT_DISPLAY_NAME = "My Component"

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import pytest
from playwright.sync_api import Page, expect

# PAGE_LOAD_TIMEOUT and assert_snapshot come from ha-testcontainer's visual conftest.
# Your project's conftest.py should import or re-export them, or copy the helper.
from ha_testcontainer.visual import PAGE_LOAD_TIMEOUT, assert_snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _goto_dashboard(page: Page, ha_url: str, path: str = "/lovelace/0") -> None:
    """Navigate to a Lovelace dashboard path and wait for the network to settle."""
    page.goto(f"{ha_url}{path}", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)


# ---------------------------------------------------------------------------
# 1. Smoke tests — dashboard loads without errors
# ---------------------------------------------------------------------------


class TestDashboardLoads:
    """Verify that the HA frontend renders correctly with the component installed."""

    def test_ha_shell_present(self, ha_page: Page, ha_url: str):
        """The <home-assistant> custom element must be present in the DOM."""
        _goto_dashboard(ha_page, ha_url)
        expect(ha_page.locator("home-assistant")).to_be_visible(timeout=PAGE_LOAD_TIMEOUT)

    def test_sidebar_renders(self, ha_page: Page, ha_url: str):
        """The HA sidebar must be visible (confirms full frontend boot)."""
        _goto_dashboard(ha_page, ha_url)
        expect(ha_page.locator("ha-sidebar")).to_be_visible(timeout=PAGE_LOAD_TIMEOUT)

    def test_no_critical_console_errors(self, ha_page: Page, ha_url: str):
        """No JavaScript errors related to the component should appear."""
        errors: list[str] = []
        # Register before navigation so early errors during page load are captured.
        ha_page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        _goto_dashboard(ha_page, ha_url)
        ha_page.wait_for_timeout(3_000)
        # Filter to errors that mention the component domain.
        component_errors = [e for e in errors if COMPONENT_DOMAIN.lower() in e.lower()]
        assert not component_errors, f"{COMPONENT_DOMAIN} produced console errors: {component_errors}"

    def test_dashboard_screenshot(self, ha_page: Page, ha_url: str):
        """Baseline screenshot of the default Lovelace dashboard."""
        _goto_dashboard(ha_page, ha_url)
        assert_snapshot(ha_page, "01_dashboard_default")


# ---------------------------------------------------------------------------
# 2. Integration setup tests — component is loaded in HA Settings
# ---------------------------------------------------------------------------


class TestComponentLoaded:
    """Verify the component appears as a configured integration in HA Settings."""

    def test_integration_appears_in_settings(self, ha_page: Page, ha_url: str):
        """The component integration card must be visible on the Integrations page."""
        ha_page.goto(
            f"{ha_url}/config/integrations",
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        # TODO: update COMPONENT_DISPLAY_NAME to the exact label shown in the UI.
        card = ha_page.get_by_text(COMPONENT_DISPLAY_NAME, exact=False)
        expect(card).to_be_visible(timeout=30_000)

    def test_integrations_page_screenshot(self, ha_page: Page, ha_url: str):
        """Baseline screenshot of the Integrations page with the component configured."""
        ha_page.goto(
            f"{ha_url}/config/integrations",
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        assert_snapshot(ha_page, "02_integrations_page")


# ---------------------------------------------------------------------------
# 3. Component behaviour tests — push a Lovelace config and verify the result
# ---------------------------------------------------------------------------


class TestComponentBehaviour:
    """Push a minimal Lovelace dashboard via the REST API and verify the component.

    This pattern is useful for components that modify the appearance or
    behaviour of Lovelace cards (e.g. CSS injectors, card wrappers, etc.).
    """

    @pytest.fixture(autouse=True)
    def _push_test_dashboard(self, ha, ha_url: str):
        """Push a minimal test Lovelace config, yield, then restore."""
        # TODO: customise this dashboard config to exercise your component.
        #       Add card_mod styles, custom card types, or whatever your
        #       component provides.
        test_config = {
            "title": f"{COMPONENT_DISPLAY_NAME} Visual Test",
            "views": [
                {
                    "title": "Component Test",
                    "path": "component-test",
                    "cards": [
                        {
                            # TODO: replace with a card that exercises your component.
                            "type": "entities",
                            "title": "Test Card",
                            "entities": ["light.bed_light", "light.ceiling_lights"],
                        },
                        {
                            "type": "entities",
                            "title": "Reference Card (unstyled)",
                            "entities": ["light.bed_light", "light.ceiling_lights"],
                        },
                    ],
                }
            ],
        }
        ha.api("POST", "lovelace/config?force=true", json=test_config)
        yield
        # Restore an empty config after the test.
        ha.api("POST", "lovelace/config?force=true", json={"title": "Home", "views": []})

    def test_component_card_screenshot(self, ha_page: Page, ha_url: str):
        """Baseline screenshot of the component's test view."""
        _goto_dashboard(ha_page, ha_url, "/lovelace/component-test")
        assert_snapshot(ha_page, "03_component_test_view")

    # TODO: add component-specific assertions below.
    #
    # Example: check that a CSS variable was applied by the component:
    #
    #   def test_css_variable_applied(self, ha_page: Page, ha_url: str):
    #       _goto_dashboard(ha_page, ha_url, "/lovelace/component-test")
    #       ha_page.wait_for_timeout(3_000)
    #       value = ha_page.evaluate(
    #           "() => getComputedStyle(document.querySelector('ha-card'))"
    #           "      .getPropertyValue('--my-css-variable').trim()"
    #       )
    #       assert value == "expected-value", f"CSS variable not applied: {value!r}"
