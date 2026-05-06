"""Shim — delegates to ha_testcontainer.visual.cursors.

The authoritative implementation has moved into the ha_testcontainer package.
Import from there directly::

    from ha_testcontainer.visual.cursors import CURSOR_SVGS
"""

from ha_testcontainer.visual.cursors import *  # noqa: F401, F403
from ha_testcontainer.visual.cursors import CURSOR_SVGS  # noqa: F401
