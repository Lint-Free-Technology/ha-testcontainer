"""ha_testcontainer – Test container for Home Assistant.

Usage::

    from ha_testcontainer import HATestContainer, HAVersion

    with HATestContainer(version=HAVersion.STABLE, config_path="ha-config") as ha:
        print(ha.get_url())
        resp = ha.api("GET", "states")
        print(resp.json())
"""

from .container import HATestContainer, HAVersion

__all__ = ["HATestContainer", "HAVersion"]
