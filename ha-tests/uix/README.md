# ha-tests/uix — PARKED: to be migrated to the UIX repo

> **This directory is a temporary migration artifact.**
>
> Once the follow-up PR in `Lint-Free-Technology/uix` copies these files
> into the UIX repo and updates the UIX test suite to consume them, a
> cleanup PR will **delete this entire `ha-tests/uix/` directory from
> ha-testcontainer**.  Nothing in this folder is intended to be a permanent
> part of ha-testcontainer.

---

## What is parked here?

| File / Directory | Destination in UIX repo | Purpose |
|---|---|---|
| `extensions.py` | `tests/visual/uix_extensions.py` | Registers UIX interaction types (`add_foundry`, `delete_foundry`, `add_foundry_file`, `remove_foundry_file`, `reload_foundry_files`) with the ha-tests `scenario_runner` |
| `ha-config/themes.yaml` | `tests/ha-config/themes.yaml` | UIX test themes (replaces the empty generic one) |
| `ha-config/uix_test_foundries.yaml` | `tests/ha-config/uix_test_foundries.yaml` | File-based foundry for `add_foundry_file` scenarios |
| `ha-config/uix_test_foundries_anchors.yaml` | `tests/ha-config/uix_test_foundries_anchors.yaml` | Demonstrates YAML anchor pattern in foundry files |
| `ha-config/uix/test_forge_style.yaml` | `tests/ha-config/uix/test_forge_style.yaml` | Included by forge style scenarios |
| `ha-config/uix/test_tile_container.yaml` | `tests/ha-config/uix/test_tile_container.yaml` | Included by forge style scenarios |
| `plugins.yaml` | merged into `tests/plugins.yaml` | UIX-specific Lovelace plugin registry |

---

## How the UIX follow-up PR should consume these

### 1. Update `pyproject.toml` dependencies

```toml
[project.optional-dependencies]
test = [
    "ha-testcontainer[test]>=1.1",
    # ... other deps
]
```

### 2. Copy files to UIX repo

```bash
# From the UIX repo root, assuming ha-testcontainer is checked out at ../ha-testcontainer

# UIX-specific scenario runner extensions
cp ../ha-testcontainer/ha-tests/uix/extensions.py tests/visual/uix_extensions.py

# UIX-specific HA config additions (themes, foundries)
cp ../ha-testcontainer/ha-tests/uix/ha-config/themes.yaml         tests/ha-config/themes.yaml
cp ../ha-testcontainer/ha-tests/uix/ha-config/uix_test_foundries.yaml         tests/ha-config/uix_test_foundries.yaml
cp ../ha-testcontainer/ha-tests/uix/ha-config/uix_test_foundries_anchors.yaml tests/ha-config/uix_test_foundries_anchors.yaml
cp ../ha-testcontainer/ha-tests/uix/ha-config/uix/test_forge_style.yaml    tests/ha-config/uix/test_forge_style.yaml
cp ../ha-testcontainer/ha-tests/uix/ha-config/uix/test_tile_container.yaml tests/ha-config/uix/test_tile_container.yaml

# UIX plugin registry
cp ../ha-testcontainer/ha-tests/uix/plugins.yaml tests/plugins.yaml
```

### 3. Activate UIX extensions in UIX's `tests/conftest.py`

In the UIX repo's top-level `tests/conftest.py`, add one import that registers the UIX interaction handlers with the scenario runner:

```python
# tests/conftest.py (UIX repo)
import sys
from pathlib import Path

# Make ha-tests/ importable so scenario_runner, lovelace_helpers, etc. are found.
# Adjust this path to wherever ha-testcontainer is installed or checked out.
_HA_TESTS = Path(__file__).parent.parent / "ha-tests"  # or use importlib if installed
sys.path.insert(0, str(_HA_TESTS / "visual"))
sys.path.insert(0, str(_HA_TESTS))

# Import the UIX extensions — registers add_foundry, delete_foundry, etc.
# with scenario_runner at import time.
import uix_extensions  # noqa: F401, E402
```

### 4. Wire up `LOVELACE_EXTRA_CONFIG_DIR` and `LOVELACE_SETUP_INTEGRATION`

The UIX conftest (or a `pytest.ini` / `pyproject.toml` `[tool.pytest.ini_options]`) should
set the environment variables that tell ha-tests where to find UIX-specific config:

```bash
# .env or CI environment
LOVELACE_SETUP_INTEGRATION=uix
LOVELACE_EXTRA_CONFIG_DIR=tests/ha-config   # path to UIX's own ha-config dir
LOVELACE_PLUGINS_YAML=tests/plugins.yaml    # path to UIX's plugin registry
```

Or override them in a session-scoped fixture in `tests/conftest.py`.

### 5. Run the tests

```bash
LOVELACE_SETUP_INTEGRATION=uix pytest ha-tests/visual/ -v
```

---

## Cleanup PR (ha-testcontainer)

Once the UIX follow-up PR is merged and UIX's CI is green, open a PR in
**this** repo (ha-testcontainer) that simply deletes `ha-tests/uix/`:

```bash
git rm -r ha-tests/uix/
git commit -m "chore: remove parked UIX migration artifacts (UIX repo now owns these)"
```

The `ha-tests/` generic framework (everything outside `uix/`) remains
unchanged.
