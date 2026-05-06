# ha-testcontainer

> A full, reusable test container for Home Assistant.

`ha-testcontainer` is a Python library that wraps the official Home Assistant
Docker image in a [Testcontainers](https://testcontainers.com/)-based class.
It handles all the plumbing — startup, programmatic onboarding, long-lived
token creation, and custom component mounting — so your tests can focus on
what matters.

[UIX (UI eXtension)](https://github.com/Lint-Free-Technology/uix) is the
primary consumer and uses this library as a replacement for its legacy local
test stack.

---

## Features

| Capability | Detail |
|---|---|
| **Version flexibility** | `stable`, `beta`, `dev`, or any pinned tag (`2024.6.0`) |
| **Automatic onboarding** | Creates an admin user and mints a long-lived API token with no manual interaction |
| **Demo entities** | Built-in HA `demo` integration gives you lights, sensors, weather objects immediately |
| **Custom config** | Mount any `configuration.yaml` tree via `config_path=` |
| **Custom components** | Mount any `custom_components/` directory via `custom_components_path=` |
| **Fetch any component** | `scripts/fetch_component.py owner/repo` — downloads any GitHub-hosted HA component |
| **Fetch any frontend plugin** | `scripts/fetch_plugin.py owner/repo` — downloads any JS dashboard plugin; registers it as a Lovelace resource |
| **Storage-mode dashboard** | Default Lovelace dashboard in storage mode; REST-pushable for tests |
| **REST API helper** | `ha.api("GET", "states")` — authenticated calls with zero boilerplate |
| **Integration setup** | `ha.setup_integration("my_domain")` — drives config-flow programmatically |
| **Playwright visual tests** | Session-scoped browser context, token injection, pixel-diff snapshot comparison |
| **Boilerplate example** | `examples/test_custom_component.py` — copy, fill in TODO values, done |

---

## Quick start

### 1 — Install

```bash
pip install -e ".[test]"
playwright install chromium
```

### 2 — Fetch a custom component

```bash
# Any GitHub-hosted HA custom component (Python, goes into custom_components/):
python scripts/fetch_component.py Lint-Free-Technology/uix
python scripts/fetch_component.py Lint-Free-Technology/uix 5.3.1   # pinned version

# Or via make (COMPONENT is required):
make setup COMPONENT=Lint-Free-Technology/uix
make setup COMPONENT=Lint-Free-Technology/uix VERSION=5.3.1
```

### 2b — Fetch a frontend plugin (optional)

Frontend plugins are JavaScript dashboard modules (Lovelace cards, etc.),
distinct from Python custom components.  They are downloaded into
`ha-config/www/dashboard/` and automatically served by HA at `/local/…`.

```bash
# Download and register a dashboard plugin:
python scripts/fetch_plugin.py custom-cards/button-card
python scripts/fetch_plugin.py thomasloven/lovelace-card-mod 3.4.4

# Or via make:
make fetch-plugin PLUGIN=custom-cards/button-card
make fetch-plugin PLUGIN=thomasloven/lovelace-card-mod VERSION=3.4.4
```

### 3 — Run tests

```bash
make test           # unit + integration tests (no browser)
make test-visual    # Playwright visual tests (requires Docker + Playwright)
```

See **[Testing](#testing)** below for a full breakdown of each tier.

### 4 — Explore locally with docker compose

```bash
make up             # starts HA at http://localhost:8123
make down
```

---

## Usage in your own project

```python
from ha_testcontainer import HATestContainer, HAVersion

with HATestContainer(
    version=HAVersion.STABLE,          # or "beta", "dev", "2024.6.0"
    config_path="ha-config",
    custom_components_path="custom_components",
) as ha:
    # Set up any custom component via config-flow
    ha.setup_integration("uix")

    # REST API — authenticated, zero boilerplate
    states = ha.api("GET", "states").json()

    print(ha.get_url())    # http://localhost:<random-port>
    print(ha.get_token())  # long-lived access token
```

### pytest plugin (zero-boilerplate visual testing)

When you install `ha-testcontainer[test]`, the package registers a pytest
plugin automatically via the `pytest11` entry-point.  The plugin provides the
following fixtures out-of-the-box — **no `conftest.py` import required**:

| Fixture | Scope | Description |
|---|---|---|
| `ha` | session | Running HA instance (Docker or external) |
| `ha_url` | session | Base URL, e.g. `http://localhost:8123` |
| `ha_token` | session | Long-lived access token |
| `ha_lovelace_url_path` | session | URL path of the test Lovelace dashboard |
| `ha_browser_context` | session | Pre-authenticated Playwright browser context |
| `ha_page` | function | Fresh Playwright page (auth inherited from context) |

Configure the plugin with environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `HA_VERSION` | `stable` | Docker image tag |
| `HA_CONFIG_PATH` | _(none)_ | Host config dir mounted as `/config` |
| `HA_CUSTOM_COMPONENTS_PATH` | _(none)_ | Host dir mounted as `/config/custom_components` |
| `HA_SETUP_INTEGRATION` | _(none)_ | Integration domain to configure via config-flow |
| `HA_EXTRA_CONFIG_DIR` | _(none)_ | Directory merged on top of `HA_CONFIG_PATH` |
| `HA_PLUGINS_YAML` | _(none)_ | Path to a `plugins.yaml` listing Lovelace plugins |
| `HA_URL` + `HA_TOKEN` | _(none)_ | Connect to a pre-running HA instance instead of Docker |

### pytest fixture example (manual, without plugin)

```python
# conftest.py
import pytest
from ha_testcontainer import HATestContainer

@pytest.fixture(scope="session")
def ha():
    with HATestContainer(config_path="ha-config", custom_components_path="custom_components") as c:
        c.setup_integration("uix")
        yield c

# test_my_component.py
def test_api(ha):
    resp = ha.api("GET", "states")
    assert resp.status_code == 200
```

### Playwright visual test example

See [`examples/test_custom_component.py`](examples/test_custom_component.py) for a
fully annotated boilerplate that any component author can copy.

```python
from ha_testcontainer.visual import PAGE_LOAD_TIMEOUT, assert_snapshot

def test_my_card(ha_page, ha_url):
    ha_page.goto(f"{ha_url}/lovelace/0", wait_until="networkidle",
                 timeout=PAGE_LOAD_TIMEOUT)
    assert_snapshot(ha_page, "my_card_baseline")
```

Run `SNAPSHOT_UPDATE=1 pytest tests/visual/` to create or update baselines.

### YAML-driven scenario tests

The scenario runner (`ha_testcontainer.visual.scenario_runner`) lets you write
visual tests as plain YAML files — no Python code required.  Configure it in
your `conftest.py` and it automatically picks up all `*.yaml` files in your
scenarios directory.

> **See also: [Writing Scenarios guide](README_SCENARIOS.md)** — best practices
> for setting entity states, structuring test cards, and keeping the test
> environment isolated from any locally-running Home Assistant instance.

```python
# tests/conftest.py
from pathlib import Path
import ha_testcontainer.visual.scenario_runner as sr

sr.SCENARIOS_DIR = Path(__file__).parent / "scenarios"
sr.SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
sr.REPO_ROOT = Path(__file__).parent.parent
```

```python
# tests/visual/test_scenarios.py
import pytest
from playwright.sync_api import Page
from ha_testcontainer.visual.scenario_runner import (
    load_all_scenarios, push_scenario, goto_scenario,
    run_interactions, run_assertions, clear_scenario,
)

_ALL = load_all_scenarios()

@pytest.mark.parametrize("scenario_id", [s["id"] for s in _ALL])
def test_scenario(scenario_id, ha, ha_page: Page, ha_url, ha_lovelace_url_path):
    scenario = next(s for s in _ALL if s["id"] == scenario_id)
    push_scenario(ha, ha_lovelace_url_path, scenario)
    try:
        goto_scenario(ha_page, ha_url, ha_lovelace_url_path, scenario["view_path"])
        run_interactions(ha_page, scenario, ha=ha)
        run_assertions(ha_page, scenario)
    finally:
        clear_scenario(ha, ha_lovelace_url_path)
```

---

## Fetching custom components

`scripts/fetch_component.py` works with **any** GitHub repository that follows
the standard HA custom-component layout (a `custom_components/<name>/` directory
in the repository root):

```
python scripts/fetch_component.py owner/repo             # latest release
python scripts/fetch_component.py owner/repo 5.3.1       # specific version
python scripts/fetch_component.py owner/repo --list      # list releases
python scripts/fetch_component.py owner/repo --target-dir /other/path
```

The script auto-discovers all `custom_components/` sub-directories in the
release archive, so multi-component repositories are handled correctly.

---

## Fetching frontend plugins (dashboard cards)

`scripts/fetch_plugin.py` downloads **JavaScript dashboard modules** — Lovelace
cards and similar frontend-only plugins — from GitHub releases.  These are
distinct from Python custom components: they live in `www/` rather than
`custom_components/`, and are loaded by the HA frontend via Lovelace resources.

```
python scripts/fetch_plugin.py owner/repo             # latest release
python scripts/fetch_plugin.py owner/repo 1.2.3       # specific version
python scripts/fetch_plugin.py owner/repo --list      # list releases
python scripts/fetch_plugin.py owner/repo --plugin-name custom-name
python scripts/fetch_plugin.py owner/repo --resource-type js   # legacy (default: module)
```

The script:
1. Downloads JS files from the release (assets, zip assets, or source archive fallback).
2. Places them at `ha-config/www/dashboard/<plugin-name>/<file>.js`.
3. Registers each file as a Lovelace resource in `ha-config/lovelace_resources.yaml`.

HA serves `ha-config/www/` at `/local/`, so the plugin is immediately available
to Lovelace dashboards as `/local/dashboard/<plugin-name>/<file>.js`.

---

## Configuration

### HA version

| Value | Image tag pulled |
|---|---|
| `HAVersion.STABLE` (default) | `ghcr.io/home-assistant/home-assistant:stable` |
| `HAVersion.BETA` | `ghcr.io/home-assistant/home-assistant:beta` |
| `HAVersion.DEV` | `ghcr.io/home-assistant/home-assistant:dev` |
| `"2024.6.0"` | `ghcr.io/home-assistant/home-assistant:2024.6.0` |

Override at runtime:

```bash
HA_VERSION=beta pytest tests/
HA_VERSION=2024.6.0 make test
```

### Config & custom components

| Environment variable | Default | Purpose |
|---|---|---|
| `HA_VERSION` | `stable` | Image tag |
| `HA_CONFIG_PATH` | `ha-config/` | Host dir mounted as `/config` |
| `HA_CUSTOM_COMPONENTS_PATH` | `custom_components/` | Host dir mounted as `/config/custom_components` |
| `HA_SETUP_INTEGRATION` | _(unset)_ | Integration domain to configure via config-flow |
| `HA_EXTRA_CONFIG_DIR` | _(unset)_ | Directory merged on top of `HA_CONFIG_PATH` before start |
| `HA_PLUGINS_YAML` | _(unset)_ | Path to a `plugins.yaml` listing Lovelace plugins to download |

---

## Repository layout

```
ha-testcontainer/
├── ha_testcontainer/
│   ├── __init__.py          # public API: HATestContainer, HAVersion, visual helpers
│   ├── container.py         # HATestContainer implementation
│   ├── plugins.py           # download_lovelace_plugins — fetch Lovelace JS plugins
│   ├── ha_server.py         # persistent HA dev server (python -m ha_testcontainer.ha_server)
│   ├── pytest_plugin.py     # pytest plugin: ha, ha_url, ha_token, ha_page fixtures
│   └── visual/
│       ├── __init__.py      # PAGE_LOAD_TIMEOUT, assert_snapshot, inject_ha_token
│       ├── cursors.py       # SVG cursor overlays for doc images/animations
│       ├── lovelace_helpers.py  # push_lovelace_config_to WS helper
│       └── scenario_runner.py   # YAML-driven scenario engine
├── ha-config/
│   ├── configuration.yaml        # demo HA config (default_config + demo integration)
│   ├── lovelace_resources.yaml   # Lovelace resources list (managed by fetch_plugin.py)
│   ├── www/                      # served at /local/ by HA; plugins downloaded here
│   └── themes/                   # theme YAML files (auto-loaded)
├── custom_components/
│   └── README.md                 # populated by scripts/fetch_component.py (gitignored)
├── scripts/
│   ├── fetch_component.py        # download any HA Python component from GitHub releases
│   └── fetch_plugin.py           # download any JS frontend plugin; register as resource
├── examples/
│   └── test_custom_component.py  # boilerplate visual test — copy & customise
├── ha-tests/                     # reference integration / thin shims (authoritative code is in ha_testcontainer/)
│   ├── conftest.py               # configures ha_testcontainer plugin paths for this test suite
│   ├── ha_server.py              # shim → ha_testcontainer.ha_server
│   ├── plugins.py                # shim → ha_testcontainer.plugins
│   ├── plugins.yaml              # Lovelace plugin registry for ha-tests/
│   ├── ha-config/                # HA config for the ha-tests/ suite
│   └── visual/
│       ├── conftest.py           # shim (fixtures come from the pytest plugin)
│       ├── scenario_runner.py    # shim → ha_testcontainer.visual.scenario_runner
│       ├── lovelace_helpers.py   # shim → ha_testcontainer.visual.lovelace_helpers
│       ├── cursors.py            # shim → ha_testcontainer.visual.cursors
│       ├── scenarios/            # YAML scenario files for this test suite
│       └── snapshots/            # gitignored baseline PNGs
├── tests/
│   ├── conftest.py               # session-scoped ha / ha_url / ha_token fixtures
│   ├── test_container_unit.py    # unit tests — no Docker needed (14 tests)
│   ├── test_container.py         # integration tests — requires Docker (10 tests)
│   └── visual/
│       ├── conftest.py      # Playwright fixtures (ha_page, ha_browser_context)
│       └── snapshots/       # gitignored — no baselines committed here (see below)
├── docker-compose.yml        # local dev: docker compose up
├── Makefile                  # setup / test / update-snapshots targets
└── pyproject.toml
```

---

## Snapshot-based visual testing

Snapshot tests follow a two-file convention:

| File | Description |
|---|---|
| `snapshots/<name>.png` | **Committed baseline** — the ground truth, lives in the **consumer's repo** |
| `snapshots/<name>.actual.png` | Generated on every run — gitignored |

On the **first run** (or when `SNAPSHOT_UPDATE=1` is set), the actual
screenshot becomes the baseline.  Subsequent runs diff the two; any pixel
difference causes the test to fail.

Baselines are placed **next to the calling test file** automatically — no
configuration needed.

> **Important — baselines are stored in the consumer's repo, not here.**
> ha-testcontainer is a reusable library; it does not commit any snapshot PNG
> files.  All `*.png` files under `tests/visual/snapshots/` are gitignored in
> this repository.  When you write visual tests for your own component, baselines
> are committed in *your* project's `tests/visual/snapshots/` directory.
> They will never appear in ha-testcontainer's history.

---

## Testing

The test suite has three tiers:

### Tier 1 — Unit tests (no Docker required)

These run in milliseconds and cover the Python logic of `HATestContainer`
in isolation (URL construction, token handling, API path normalisation):

```bash
pip install -e ".[test]"                   # install once
pytest tests/test_container_unit.py -v
```

Or via make:

```bash
make install
make test
```

`make test` runs **all** non-browser tests, including both unit and
integration tests, skipping the visual tier.

### Tier 2 — Integration tests (Docker required)

These start a real Home Assistant container and exercise the full lifecycle
(onboarding, REST API, demo entities, Lovelace push):

```bash
# Prerequisites: Docker daemon running, HA image available
pytest tests/test_container.py -v
```

The container is started once per pytest session (session-scoped fixture)
and reused across all tests in the file.  Startup takes ~60 s the first time
while HA initialises.

Environment variables let you control which image and config directory are
used:

| Variable | Default | Purpose |
|---|---|---|
| `HA_VERSION` | `stable` | Image tag (`stable`, `beta`, `dev`, `2024.6.0`, …) |
| `HA_CONFIG_PATH` | `ha-config/` | Host dir mounted as `/config` |
| `HA_CUSTOM_COMPONENTS_PATH` | `custom_components/` | Host dir mounted as `/config/custom_components` |

```bash
HA_VERSION=beta pytest tests/test_container.py -v
```

### Tier 3 — Visual (Playwright) tests (Docker + Playwright required)

```bash
pip install -e ".[test]"
playwright install chromium
pytest tests/visual/ -v
```

Or via make:

```bash
make install
make test-visual
```

Visual tests open a Chromium browser, log in to the running HA instance, and
compare screenshots against committed baselines.  Baselines are stored in the
**consumer's own repository** — see [Snapshot-based visual testing](#snapshot-based-visual-testing).

### Version smoke tests (slow, optional)

These pull the `stable`, `beta`, and `dev` images in sequence and verify that
the container starts for each:

```bash
pytest tests/test_container.py -v -m version_smoke
# or:
make test-smoke
```

They are skipped by default to avoid pulling large images on every run.

---



UIX's `test/docker-compose.yaml` + `test/configuration.yaml` + `test/lovelace.yaml`
are replaced by `make up` and UIX writing its own `tests/` using `HATestContainer`.

1. Add `ha-testcontainer` as a dev dependency.
2. Fetch UIX: `python scripts/fetch_component.py Lint-Free-Technology/uix`.
3. Replace `docker compose -f test/docker-compose.yaml up` with `make up`.
4. Copy `examples/test_custom_component.py` into UIX's `tests/visual/`, fill in
   UIX-specific TODO values, and add UIX-specific test cases.
5. Delete UIX's `test/` directory.

---

## License

MIT — see [LICENSE](LICENSE).
