"""Shim — delegates to ha_testcontainer.visual.scenario_runner.

The authoritative implementation has moved into the ha_testcontainer package.
Import from there directly::

    from ha_testcontainer.visual.scenario_runner import (
        load_all_scenarios,
        push_scenario,
        run_interactions,
        run_assertions,
        ...
    )

Paths (SCENARIOS_DIR, SNAPSHOTS_DIR, REPO_ROOT, DOCS_SCENARIOS_DIR) are
configured by ``ha-tests/conftest.py`` at collection time.
"""

from ha_testcontainer.visual.scenario_runner import *  # noqa: F401, F403
from ha_testcontainer.visual.scenario_runner import (  # noqa: F401
    load_all_scenarios,
    load_doc_scenarios,
    load_all_doc_image_scenarios,
    push_scenario,
    clear_scenario,
    goto_scenario,
    run_interactions,
    run_assertions,
    capture_doc_image,
    capture_doc_animation,
    register_interaction_type,
    register_assertion_type,
    set_theme,
    reset_theme,
)
