# ha-tests

Visual and integration tests for Home Assistant custom components using
[ha-testcontainer](https://github.com/Lint-Free-Technology/ha-testcontainer)
and [Playwright](https://playwright.dev/python/).

These test scripts were migrated from
[Lint-Free-Technology/uix](https://github.com/Lint-Free-Technology/uix/tree/main/tests)
and are designed to be reusable by **any** custom component author, not just UIX.

---

## What the tests do

| File | Purpose |
|------|---------|
| `conftest.py` | Session-scoped HA Docker container fixture, Lovelace dashboard creation, external-HA proxy for fast iteration |
| `ha_server.py` | Start a long-lived HA container once for rapid iterative development (`make ha-tests-up`) |
| `plugins.py` | Download third-party Lovelace JS plugins (listed in `plugins.yaml`) into the HA container's `www/` directory |
| `plugins.yaml` | Registry of frontend plugins to download (defaults tuned for UIX) |
| `test_doc_audit.py` | Verify every PNG/GIF referenced in your docs is covered by a scenario or explicitly excluded |
| `visual/conftest.py` | Playwright browser-context fixture pre-authenticated against HA |
| `visual/lovelace_helpers.py` | WebSocket helper to push Lovelace config to a named dashboard |
| `visual/cursors.py` | SVG cursor overlays for annotated screenshots (arrow, pointer) |
| `visual/scenario_runner.py` | YAML-driven scenario engine: loads `.yaml` files, pushes Lovelace config, runs interactions and assertions |
| `visual/test_scenarios.py` | Parametrised test that runs every scenario in `visual/scenarios/` |
| `visual/test_doc_images.py` | Parametrised test that generates/verifies doc PNG/GIF assets from scenarios with `doc_image:`/`doc_animation:` keys |
| `visual/test_uix_styling.py` | UIX-specific smoke tests (HA boots, UIX integration visible, no console errors) |

---

## Prerequisites

- **Docker** — required to run the HA container.
- **Python ≥ 3.11**

```bash
# Install Python dependencies
pip install -e ".[test]"
playwright install chromium
```

---

## Running the tests

### Via Makefile (recommended)

```bash
# Run all non-browser tests in ha-tests/
make ha-tests

# Run visual (Playwright) tests
make ha-tests-visual

# Refresh all snapshot baselines
make ha-tests-update-snapshots

# Doc-image audit
make ha-tests-doc-audit
```

### Directly with pytest

```bash
# All non-visual tests
pytest ha-tests/ --ignore=ha-tests/visual -v

# All visual tests
pytest ha-tests/visual/ -v

# A single scenario by id
pytest ha-tests/visual/test_scenarios.py -k my_scenario_id -v

# UIX-specific smoke tests
LOVELACE_SETUP_INTEGRATION=uix pytest ha-tests/visual/test_uix_styling.py -v
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HA_VERSION` | `stable` | Docker image tag: `stable`, `beta`, `dev`, or a pinned version like `2024.6.0` |
| `HA_URL` | *(not set)* | URL of a pre-running HA instance (skips Docker startup when set with `HA_TOKEN`) |
| `HA_TOKEN` | *(not set)* | Long-lived access token for the pre-running instance |
| `LOVELACE_SETUP_INTEGRATION` | *(empty)* | Integration domain to auto-configure on container startup, e.g. `uix` |
| `SNAPSHOT_UPDATE` | `0` | Set to `1` to create/overwrite snapshot baselines |
| `DOC_IMAGE_UPDATE` | `0` | Set to `1` to regenerate all doc images |
| `DOCS_SOURCE_DIR` | `docs/source/` | Override the docs directory scanned by `test_doc_audit.py` |
| `GITHUB_TOKEN` | *(not set)* | GitHub token for fetching plugin releases (avoids rate limiting) |

---

## Fast-iteration mode

Start HA once and re-run pytest instantly — no Docker startup overhead:

```bash
# Terminal 1 — keep running
LOVELACE_SETUP_INTEGRATION=uix make ha-tests-up
# or: python ha-tests/ha_server.py

# Terminal 2 — iterate quickly
source .ha_env
pytest ha-tests/visual/test_scenarios.py -k my_scenario -v
pytest ha-tests/visual/test_scenarios.py -k my_scenario -v   # instant!
```

---

## Installing a component to test

Use `make setup` to fetch any component into `custom_components/`:

```bash
make setup COMPONENT=Lint-Free-Technology/uix
make setup COMPONENT=Lint-Free-Technology/uix VERSION=5.3.1
```

The `custom_components/` directory is automatically mounted into the HA
container when it is not empty.

---

## Adding scenarios

Create a `.yaml` file anywhere under `ha-tests/visual/scenarios/`.  No Python
changes are needed — the runner discovers all YAML files automatically.

### Minimal scenario

```yaml
id: my_card_default
view_path: my-card-test
card:
  type: tile
  entity: light.bed_light
assertions:
  - type: snapshot
    name: my_card_default
```

### With interactions and theme

```yaml
id: my_card_hover
view_path: my-card-hover
card:
  type: tile
  entity: light.bed_light
theme: uix-test-theme
interactions:
  - type: hover
    root: hui-tile-card
    selector: ha-tile-icon
    settle_ms: 800
assertions:
  - type: snapshot
    name: my_card_hover
```

### With a doc image

```yaml
id: my_card_doc
view_path: my-card-doc
card:
  type: tile
  entity: light.bed_light
doc_image:
  output: docs/source/assets/my_card.png
  root: hui-tile-card
  padding: 16
  threshold: 0.02
```

See `visual/scenario_runner.py` for the full schema reference, including all
interaction types (`hover`, `click`, `ha_service`, `add_foundry`, etc.) and
assertion types (`snapshot`, `element_visible`, `text_content`, etc.).

---

## Snapshot baselines

Baselines are stored in `visual/snapshots/` alongside the test files:

- `my_card.png` — baseline (committed to the repo)
- `my_card.actual.png` — transient capture (gitignored)

To create or update baselines:

```bash
SNAPSHOT_UPDATE=1 pytest ha-tests/visual/ -v
# or:
make ha-tests-update-snapshots
```

---

## Doc-image audit

`test_doc_audit.py` checks that every PNG/GIF referenced in your docs is
either generated by a scenario or explicitly excluded:

```bash
DOCS_SOURCE_DIR=docs/source pytest ha-tests/test_doc_audit.py -v
# or:
make ha-tests-doc-audit
```

Add hand-crafted images (diagrams, logos) to
`ha-tests/doc-image-audit-exclusions.txt` to silence false positives.

---

## ha-config directory

`ha-tests/ha-config/` contains the Home Assistant configuration mounted into
the test container:

| File | Purpose |
|------|---------|
| `configuration.yaml` | Main HA config: `demo` entities, `input_boolean`, `person`, Lovelace in `storage` mode |
| `customize.yaml` | Entity customisations (entity picture for person entity) |
| `lovelace_resources.yaml` | Auto-generated by `plugins.py`; registers downloaded JS as Lovelace resources |
| `themes.yaml` | Test themes used by UIX scenarios |
| `uix_test_foundries.yaml` | Example UIX foundry file for file-based foundry tests |
| `uix_test_foundries_anchors.yaml` | Example UIX foundry file demonstrating YAML anchors |
| `uix/` | UIX-specific component YAML files included by foundry configs |
| `www/media/` | Media assets served at `/local/media/`; populate with image/video files as needed |

The `themes.yaml` and foundry files are UIX-specific.  When testing a different
component you can simplify `configuration.yaml` to remove UIX-specific config
blocks.

---

## Follow-up in UIX repo

After this PR lands in ha-testcontainer, a follow-up PR in
`Lint-Free-Technology/uix` should:

1. Remove `tests/conftest.py`, `tests/ha_server.py`, `tests/plugins.py`,
   `tests/plugins.yaml`, `tests/test_doc_audit.py`,
   `tests/visual/conftest.py`, `tests/visual/cursors.py`,
   `tests/visual/lovelace_helpers.py`, `tests/visual/scenario_runner.py`,
   `tests/visual/test_doc_images.py`, `tests/visual/test_scenarios.py`,
   `tests/visual/test_uix_styling.py` from the UIX repo.
2. Add `ha-testcontainer` as a Python dependency in the UIX test extras:
   ```toml
   [project.optional-dependencies]
   test = [
       "ha-testcontainer[test]",
       ...
   ]
   ```
3. Replace the deleted test files with thin wrappers that import from
   `ha-testcontainer`'s `ha-tests/` scripts, or configure pytest to discover
   `ha-testcontainer`'s `ha-tests/` directory directly.
4. Update `tests/README.md` to point to this directory for infrastructure docs.
