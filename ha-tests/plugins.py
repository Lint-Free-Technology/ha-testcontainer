"""Shim — delegates to ha_testcontainer.plugins.

The authoritative implementation has moved into the ha_testcontainer package.
Import from there directly::

    from ha_testcontainer.plugins import download_lovelace_plugins
"""

from ha_testcontainer.plugins import *  # noqa: F401, F403
from ha_testcontainer.plugins import download_lovelace_plugins  # noqa: F401

