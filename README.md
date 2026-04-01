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
# Any GitHub-hosted HA custom component:
python scripts/fetch_component.py Lint-Free-Technology/uix
python scripts/fetch_component.py Lint-Free-Technology/uix 5.3.1   # pinned version
python scripts/fetch_component.py custom-cards/button-card

# Or via make (default component is Lint-Free-Technology/uix):
make setup
make setup COMPONENT=custom-cards/button-card
make setup COMPONENT=Lint-Free-Technology/uix VERSION=5.3.1
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
│   ├── __init__.py          # public API: HATestContainer, HAVersion, visual helpers
│   ├── container.py         # HATestContainer implementation
│   └── visual.py            # PAGE_LOAD_TIMEOUT, assert_snapshot, inject_ha_token
├── ha-config/
│   ├── configuration.yaml   # demo HA config (default_config + demo integration)
│   └── themes/              # theme YAML files (auto-loaded)
├── custom_components/
│   └── README.md            # populated by scripts/fetch_component.py (gitignored)
├── scripts/
│   └── fetch_component.py   # download any HA component from GitHub releases
├── examples/
│   └── test_custom_component.py  # boilerplate visual test — copy & customise
├── tests/
│   ├── conftest.py          # session-scoped ha / ha_url / ha_token fixtures
│   ├── test_container.py    # container lifecycle + REST API tests
│   └── visual/
│       ├── conftest.py      # Playwright fixtures (ha_page, ha_browser_context)
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

Baselines are placed **next to the calling test file** automatically — no
configuration needed.

---

## Migrating from UIX's legacy `test/` setup

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
