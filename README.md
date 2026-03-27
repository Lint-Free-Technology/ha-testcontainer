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
| **Custom components** | Mount a `custom_components/` directory via `custom_components_path=` |
| **Storage-mode dashboard** | Default Lovelace dashboard in storage mode; a secondary YAML slot for component test views |
| **REST API helper** | `ha.api("GET", "states")` — authenticated calls with zero boilerplate |
| **Integration setup** | `ha.setup_integration("uix")` — drives config-flow programmatically |
| **Playwright visual tests** | Session-scoped browser context, token injection, snapshot comparison |

---

## Quick start

### 1 — Install

```bash
pip install -e ".[test]"
playwright install chromium
```

### 2 — Download UIX (or another custom component)

```bash
make setup                         # latest UIX release
python scripts/fetch_uix.py 5.3.1  # specific version
```

### 3 — Run tests

```bash
make test           # unit + integration tests (no browser)
make test-visual    # Playwright visual tests
```

### 4 — Explore locally with docker compose

```bash
make up             # starts HA at http://localhost:8123
make down
```

---

## Usage in your own project

```python
from ha_testcontainer import HATestContainer, HAVersion

# As a context manager (recommended)
with HATestContainer(
    version=HAVersion.STABLE,
    config_path="path/to/ha-config",
    custom_components_path="path/to/custom_components",
) as ha:
    # REST API
    states = ha.api("GET", "states").json()

    # Set up a custom component via config-flow
    ha.setup_integration("uix")

    print(ha.get_url())    # http://localhost:<random-port>
    print(ha.get_token())  # long-lived access token
```

### pytest fixture example

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

```python
from tests.visual.conftest import assert_snapshot

def test_my_card_looks_right(ha_page, ha_url):
    ha_page.goto(f"{ha_url}/lovelace/0", wait_until="networkidle")
    assert_snapshot(ha_page, "my_card_baseline")
```

Run `SNAPSHOT_UPDATE=1 pytest tests/visual/` to create or update baselines.

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

---

## Repository layout

```
ha-testcontainer/
├── ha_testcontainer/
│   ├── __init__.py          # public API: HATestContainer, HAVersion
│   └── container.py         # HATestContainer implementation
├── ha-config/
│   ├── configuration.yaml   # demo HA config (default_config + demo integration)
│   └── themes/              # theme YAML files (auto-loaded)
├── custom_components/
│   └── README.md            # populated by scripts/fetch_uix.py (gitignored)
├── scripts/
│   └── fetch_uix.py         # download UIX from GitHub releases
├── tests/
│   ├── conftest.py          # session-scoped ha / ha_url / ha_token fixtures
│   ├── test_container.py    # container lifecycle + REST API tests
│   └── visual/
│       ├── conftest.py      # Playwright fixtures + assert_snapshot helper
│       ├── test_uix.py      # UIX visual regression tests (example usage)
│       └── snapshots/       # baseline PNGs (committed); *.actual.png (gitignored)
├── docker-compose.yml        # local dev: docker compose up
├── Makefile                  # setup / test / update-snapshots targets
└── pyproject.toml
```

---

## Snapshot-based visual testing

Snapshot tests follow a two-file convention:

| File | Description |
|---|---|
| `snapshots/<name>.png` | **Committed baseline** — the ground truth |
| `snapshots/<name>.actual.png` | Generated on every run — gitignored |

On the **first run** (or when `SNAPSHOT_UPDATE=1` is set), the actual
screenshot becomes the baseline.  Subsequent runs diff the two; any pixel
difference causes the test to fail.

This makes it trivially easy for UIX to catch visual regressions caused by a
HA core update or a UIX CSS change.

---

## Migrating from UIX's legacy `test/` setup

UIX previously used a `test/docker-compose.yaml` + `test/configuration.yaml`
local stack.  The migration path is:

1. Add `ha-testcontainer` as a dev dependency.
2. Run `python scripts/fetch_uix.py` to populate `custom_components/uix/`.
3. Replace `docker compose -f test/docker-compose.yaml up` with `make up`.
4. Move UIX-specific Lovelace views into UIX's own `tests/` directory,
   using `HATestContainer` and the Playwright fixtures from this package.
5. Delete UIX's `test/` directory.

---

## License

MIT — see [LICENSE](LICENSE).
