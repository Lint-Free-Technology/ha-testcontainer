"""Playwright fixtures for visual regression tests.

These fixtures build on top of the session-scoped ``ha`` fixture from the
parent conftest and add Playwright browser automation helpers.

Snapshot baseline images live in ``tests/visual/snapshots/``.  On the first
run (or when ``--snapshot-update`` is passed) new baseline PNGs are written;
subsequent runs compare against them.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, BrowserContext

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
SNAPSHOTS_DIR.mkdir(exist_ok=True)

# How long (ms) to wait for HA to fully paint before snapshotting.
PAGE_LOAD_TIMEOUT = 60_000
HA_SETTLE_MS = 3_000


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------


def inject_ha_token(page: Page, ha_url: str, token: str) -> None:
    """Bypass the HA login screen by injecting a long-lived token into localStorage.

    Home Assistant reads ``hassTokens`` from localStorage on startup.
    Setting it before the first navigation skips the onboarding/login flow.
    """
    # Navigate to a blank page on the same origin so we can set localStorage.
    page.goto(ha_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)

    import time
    expires_ms = int(time.time() * 1000) + 365 * 24 * 3600 * 1000

    page.evaluate(
        """([url, tok, exp]) => {
            localStorage.setItem('hassTokens', JSON.stringify({
                access_token: tok,
                token_type: 'Bearer',
                expires_in: 31536000,
                refresh_token: null,
                hassUrl: url,
                clientId: url + '/',
                expires: exp
            }));
        }""",
        [ha_url, token, expires_ms],
    )


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
    # Inject the token on a fresh page and save the storage state.
    page = context.new_page()
    inject_ha_token(page, ha_url, ha_token)
    # Navigate to the main dashboard to trigger token validation.
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


# ---------------------------------------------------------------------------
# Snapshot helper
# ---------------------------------------------------------------------------


def assert_snapshot(page: Page, name: str, *, update: bool = False) -> None:
    """Take a screenshot and compare it to the stored baseline.

    Parameters
    ----------
    page:
        Playwright page to screenshot.
    name:
        Basename for the PNG file (without extension).
    update:
        When True, overwrite the baseline instead of comparing.
        Controlled by the ``SNAPSHOT_UPDATE`` environment variable or the
        ``--snapshot-update`` pytest option.
    """
    baseline = SNAPSHOTS_DIR / f"{name}.png"
    actual = SNAPSHOTS_DIR / f"{name}.actual.png"

    page.wait_for_timeout(HA_SETTLE_MS)
    page.screenshot(path=str(actual), full_page=False)

    should_update = update or os.environ.get("SNAPSHOT_UPDATE") == "1"

    if not baseline.exists() or should_update:
        import shutil
        shutil.copy(actual, baseline)
        print(f"\n[snapshot] baseline {'updated' if baseline.exists() else 'created'}: {baseline}")
        return

    # Pixel-level comparison using Pillow if available, otherwise byte compare.
    try:
        from PIL import Image, ImageChops  # type: ignore[import]
        img_base = Image.open(baseline).convert("RGB")
        img_actual = Image.open(actual).convert("RGB")
        diff = ImageChops.difference(img_base, img_actual)
        bbox = diff.getbbox()
        assert bbox is None, (
            f"Snapshot mismatch for '{name}'. "
            f"Differing region: {bbox}. "
            f"Run with SNAPSHOT_UPDATE=1 to accept new baseline."
        )
    except ImportError:
        # Fallback: byte-level comparison.
        assert baseline.read_bytes() == actual.read_bytes(), (
            f"Snapshot mismatch for '{name}'. "
            "Run with SNAPSHOT_UPDATE=1 to accept new baseline."
        )
