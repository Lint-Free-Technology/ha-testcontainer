"""Visual regression tests for UIX (UI eXtension).

These tests demonstrate how UIX would use ha-testcontainer for repeatable
visual testing.  UIX's own legacy test/ directory can be retired in favour
of this pattern.

Test structure
--------------
Each test:
  1. Navigates to a relevant HA page (dashboard, entity, settings …).
  2. Optionally injects UIX CSS via the HA config-flow / REST API.
  3. Waits for the UI to settle.
  4. Takes a screenshot and compares it against a stored baseline.

Running
-------
    # First run – creates baselines in tests/visual/snapshots/
    pytest tests/visual/ --headed          # optional: watch in browser

    # Subsequent runs – compares against baselines
    pytest tests/visual/

    # Refresh baselines after an intentional UIX change
    SNAPSHOT_UPDATE=1 pytest tests/visual/
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.visual.conftest import assert_snapshot, PAGE_LOAD_TIMEOUT


def _goto_dashboard(page: Page, ha_url: str, path: str = "/lovelace/0") -> None:
    page.goto(f"{ha_url}{path}", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)


# ---------------------------------------------------------------------------
# Dashboard presence tests
# ---------------------------------------------------------------------------


class TestDashboardLoads:
    """Basic smoke tests: HA frontend renders without errors."""

    def test_lovelace_title_visible(self, ha_page: Page, ha_url: str):
        _goto_dashboard(ha_page, ha_url)
        # The HA shell should be present.
        expect(ha_page.locator("home-assistant")).to_be_visible(timeout=PAGE_LOAD_TIMEOUT)

    def test_sidebar_renders(self, ha_page: Page, ha_url: str):
        _goto_dashboard(ha_page, ha_url)
        sidebar = ha_page.locator("ha-sidebar")
        expect(sidebar).to_be_visible(timeout=PAGE_LOAD_TIMEOUT)

    def test_dashboard_screenshot(self, ha_page: Page, ha_url: str):
        """Baseline screenshot of the default Lovelace dashboard."""
        _goto_dashboard(ha_page, ha_url)
        assert_snapshot(ha_page, "01_dashboard_default")


# ---------------------------------------------------------------------------
# UIX-specific visual tests
# ---------------------------------------------------------------------------


class TestUIXLoaded:
    """Verify UIX is active and applies CSS to the HA frontend."""

    def test_uix_js_injected(self, ha_page: Page, ha_url: str):
        """UIX registers itself as an extra module URL; check the script tag."""
        _goto_dashboard(ha_page, ha_url)
        # UIX adds a <script> or custom-element that can be detected in the DOM.
        # We look for the 'uix' custom element or a data attribute it sets.
        uix_present = ha_page.evaluate(
            "() => !!(window.customElements && window.customElements.get('uix-controller') "
            "        || document.querySelector('uix-controller'))"
        )
        assert uix_present, (
            "UIX controller element not found. "
            "Ensure UIX is installed in custom_components/ and its config entry is set up."
        )

    def test_uix_no_console_errors(self, ha_page: Page, ha_url: str):
        """UIX should not produce any console errors on the main dashboard."""
        errors: list[str] = []
        ha_page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        _goto_dashboard(ha_page, ha_url)
        ha_page.wait_for_timeout(3_000)
        uix_errors = [e for e in errors if "uix" in e.lower()]
        assert not uix_errors, f"UIX produced console errors: {uix_errors}"

    def test_settings_integrations_shows_uix(self, ha_page: Page, ha_url: str):
        """UIX should appear as a configured integration in the Settings UI."""
        ha_page.goto(
            f"{ha_url}/config/integrations",
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        # The integration card should show "UI eXtension".
        uix_card = ha_page.get_by_text("UI eXtension", exact=False)
        expect(uix_card).to_be_visible(timeout=30_000)

    def test_uix_integrations_screenshot(self, ha_page: Page, ha_url: str):
        """Baseline screenshot of the Integrations page with UIX configured."""
        ha_page.goto(
            f"{ha_url}/config/integrations",
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        assert_snapshot(ha_page, "02_integrations_with_uix")


# ---------------------------------------------------------------------------
# UIX CSS application tests (card_mod style injection)
# ---------------------------------------------------------------------------


class TestUIXCSSApplication:
    """Test that UIX correctly applies card_mod CSS to Lovelace cards.

    These tests push a minimal Lovelace config via the REST API, then verify
    that the CSS specified in ``card_mod.style`` is applied to the rendered
    card.  This is the core UIX behaviour under test.
    """

    @pytest.fixture(autouse=True)
    def _push_test_dashboard(self, ha, ha_page: Page, ha_url: str):
        """Push a minimal test dashboard with a UIX-styled card, then clean up."""
        # Push a temporary lovelace config with a UIX-styled entities card.
        test_config = {
            "title": "UIX Visual Test",
            "views": [
                {
                    "title": "CSS Test",
                    "path": "uix-css-test",
                    "cards": [
                        {
                            "type": "entities",
                            "title": "UIX Styled Card",
                            "entities": ["light.bed_light", "light.ceiling_lights"],
                            "card_mod": {
                                "style": (
                                    "ha-card { "
                                    "--ha-card-border-color: rgb(255, 0, 0); "
                                    "border-width: 3px; "
                                    "}"
                                )
                            },
                        },
                        {
                            "type": "entities",
                            "title": "Unstyled Reference Card",
                            "entities": ["light.bed_light", "light.ceiling_lights"],
                        },
                    ],
                }
            ],
        }
        ha.api("POST", "lovelace/config?force=true", json=test_config)
        yield
        # Restore to an empty config after the test.
        ha.api("POST", "lovelace/config?force=true", json={"title": "Home", "views": []})

    def test_styled_card_screenshot(self, ha_page: Page, ha_url: str):
        """Screenshot the UIX-styled card for visual regression baseline."""
        _goto_dashboard(ha_page, ha_url, "/lovelace/uix-css-test")
        assert_snapshot(ha_page, "03_uix_styled_card")

    def test_red_border_applied(self, ha_page: Page, ha_url: str):
        """The UIX-injected CSS variable should produce a red border on the card.

        We evaluate the computed style inside HA's shadow DOM to confirm UIX
        has applied the CSS custom property.
        """
        _goto_dashboard(ha_page, ha_url, "/lovelace/uix-css-test")
        ha_page.wait_for_timeout(3_000)

        border_color = ha_page.evaluate(
            """() => {
                const root = document.querySelector('home-assistant');
                if (!root || !root.shadowRoot) return null;
                const panel = root.shadowRoot.querySelector('ha-panel-lovelace');
                if (!panel || !panel.shadowRoot) return null;
                const hui = panel.shadowRoot.querySelector('hui-root');
                if (!hui || !hui.shadowRoot) return null;
                const card = hui.shadowRoot.querySelector('ha-card');
                if (!card) return null;
                return getComputedStyle(card).getPropertyValue('--ha-card-border-color').trim();
            }"""
        )
        # If UIX is working, the CSS variable should be set to our red value.
        assert border_color is not None, "Could not traverse shadow DOM to ha-card"
        assert "255, 0, 0" in border_color or border_color == "rgb(255, 0, 0)", (
            f"Expected red border color from UIX CSS, got: {border_color!r}"
        )
