"""Visual conftest shim for ha-tests/.

The Playwright fixtures (ha_browser_context, ha_page) and the session fixtures
(ha, ha_url, ha_token, ha_lovelace_url_path) are now provided automatically by
the ha_testcontainer pytest plugin via the ``pytest11`` entry-point.

This file exists to allow consumers to add ha-tests/-specific overrides.
"""

