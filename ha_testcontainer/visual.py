"""Visual testing helpers for ha-testcontainer.

This module provides the Playwright-based helpers that component authors import
in their own test files.  The key exports are:

- :data:`PAGE_LOAD_TIMEOUT`  — ms to wait for HA to fully render
- :data:`HA_SETTLE_MS`       — additional settle time before snapshotting
- :func:`inject_ha_token`    — bypass the HA login screen via localStorage
- :func:`assert_snapshot`    — take a screenshot and compare to a baseline

Usage in a component's test file::

    from ha_testcontainer.visual import PAGE_LOAD_TIMEOUT, assert_snapshot

    def test_my_card(ha_page, ha_url):
        ha_page.goto(f"{ha_url}/lovelace/0", wait_until="networkidle",
                     timeout=PAGE_LOAD_TIMEOUT)
        assert_snapshot(ha_page, "my_card_baseline")

Where baselines are stored
--------------------------
Baseline PNGs are placed in a ``snapshots/`` sub-directory **next to the
calling test file** in the **consumer's own repository**.  They are part of
the consumer project's version history — not part of ha-testcontainer.

ha-testcontainer itself does not commit any snapshot files.  Any PNGs that
are generated locally (e.g. when running the example tests) are gitignored
inside this repository.

Run with ``SNAPSHOT_UPDATE=1`` (or pass ``update=True``) to create or refresh
baselines in the consumer's project.
"""

from __future__ import annotations

import inspect
import os
import shutil
from pathlib import Path

from playwright.sync_api import Page

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Milliseconds to allow for HA's frontend to fully paint before asserting
#: or screenshotting.  Applies to ``page.goto`` wait and explicit waits.
PAGE_LOAD_TIMEOUT: int = 60_000

#: Additional settle time (ms) between page load and snapshot capture, to let
#: animations and async HA state updates complete.
HA_SETTLE_MS: int = 3_000


# ---------------------------------------------------------------------------
# Authentication helper
# ---------------------------------------------------------------------------


def inject_ha_token(page: Page, ha_url: str, token: str) -> None:
    """Bypass the HA login screen by injecting a long-lived token into localStorage.

    Home Assistant reads ``hassTokens`` from localStorage on page load.
    Injecting it before the first navigation skips the onboarding/login flow.

    Parameters
    ----------
    page:
        An unnavigated Playwright :class:`~playwright.sync_api.Page`.
    ha_url:
        Base URL of the running HA instance, e.g. ``http://localhost:8123``.
    token:
        Long-lived access token obtained from :meth:`HATestContainer.get_token`.
    """
    import time

    page.goto(ha_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
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
# Snapshot helper
# ---------------------------------------------------------------------------


def assert_snapshot(
    page: Page,
    name: str,
    *,
    snapshots_dir: Path | str | None = None,
    update: bool = False,
) -> None:
    """Take a screenshot and compare it to a stored baseline PNG.

    On the **first run** (or when *update* is ``True`` / ``SNAPSHOT_UPDATE=1``),
    the screenshot is saved as the baseline.  Subsequent runs compare the new
    screenshot against the baseline; any pixel difference fails the test.

    Baseline PNGs (``<name>.png``) are placed in the ``snapshots/`` directory
    next to the calling test file in the **consumer's own repository** and
    should be committed there.
    Actual screenshots (``<name>.actual.png``) are transient and should be
    gitignored in the consumer's project.

    Parameters
    ----------
    page:
        Playwright page to screenshot.
    name:
        Filename stem for the PNG, e.g. ``"01_dashboard"``.
    snapshots_dir:
        Directory in which to store baseline and actual PNGs.
        Defaults to a ``snapshots/`` sub-directory **next to the calling
        test file** so baselines live alongside the tests that create them.
    update:
        When ``True``, overwrite the baseline instead of comparing.
        Also triggered by the ``SNAPSHOT_UPDATE=1`` environment variable.
    """
    resolved_dir = _resolve_snapshots_dir(snapshots_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    baseline = resolved_dir / f"{name}.png"
    actual = resolved_dir / f"{name}.actual.png"

    page.wait_for_timeout(HA_SETTLE_MS)
    page.screenshot(path=str(actual), full_page=False)

    should_update = update or os.environ.get("SNAPSHOT_UPDATE") == "1"

    baseline_existed = baseline.exists()

    if not baseline_existed or should_update:
        shutil.copy(actual, baseline)
        print(f"\n[snapshot] baseline {'updated' if baseline_existed else 'created'}: {baseline}")
        return

    # Pixel-level comparison using Pillow when available, falling back to bytes.
    try:
        from PIL import Image, ImageChops  # type: ignore[import]

        img_base = Image.open(baseline).convert("RGB")
        img_actual = Image.open(actual).convert("RGB")
        diff = ImageChops.difference(img_base, img_actual)
        bbox = diff.getbbox()
        assert bbox is None, (
            f"Snapshot mismatch for '{name}'. "
            f"Differing region: {bbox}. "
            "Run with SNAPSHOT_UPDATE=1 to accept new baseline."
        )
    except ImportError:
        # Pillow not installed — byte-level fallback.
        assert baseline.read_bytes() == actual.read_bytes(), (
            f"Snapshot mismatch for '{name}'. "
            "Run with SNAPSHOT_UPDATE=1 to accept new baseline."
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_snapshots_dir(snapshots_dir: Path | str | None) -> Path:
    """Return the resolved snapshots directory path.

    When *snapshots_dir* is ``None`` (the default), walk the call stack to
    find the first frame outside this module and place the ``snapshots/``
    sub-directory next to that file.  This means snapshot baselines
    automatically live alongside the test file that calls
    :func:`assert_snapshot`, with no configuration required.
    """
    if snapshots_dir is not None:
        return Path(snapshots_dir)

    this_file = Path(__file__).resolve()
    for frame_info in inspect.stack()[2:]:
        caller_file = Path(frame_info.filename).resolve()
        if caller_file != this_file:
            return caller_file.parent / "snapshots"

    # Fallback: use the current working directory.
    return Path.cwd() / "snapshots"
