"""Playwright fixtures for ha-testcontainer's own visual tests.

This conftest wires up a Playwright browser context that is pre-authenticated
against the running HA instance.  The snapshot helpers and constants are
imported from ``ha_testcontainer.visual`` — the same module that component
authors use in their own tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, BrowserContext

from ha_testcontainer.visual import (
    PAGE_LOAD_TIMEOUT,
    HA_SETTLE_MS,
    inject_ha_token,
    assert_snapshot,
)

# Re-export for tests in this package that import directly from this conftest.
__all__ = ["PAGE_LOAD_TIMEOUT", "HA_SETTLE_MS", "assert_snapshot"]

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
SNAPSHOTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ha_browser_context(browser, ha_url: str, ha_token: str) -> BrowserContext:
    """A Playwright browser context pre-authenticated with HA."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = context.new_page()
    inject_ha_token(page, ha_url, ha_token)
    page.goto(f"{ha_url}/lovelace/0", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
    page.close()
    yield context
    context.close()


@pytest.fixture()
def ha_page(ha_browser_context: BrowserContext) -> Page:
    """A fresh Playwright page inside the pre-authenticated context."""
    page = ha_browser_context.new_page()
    yield page
    page.close()
