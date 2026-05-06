# Writing Scenarios

This guide explains how to write YAML scenario files for the
`ha_testcontainer` scenario runner and covers best practices for setting up
entity states, structuring test cards, and keeping the test environment
isolated from any locally-running Home Assistant instance.

---

## Contents

1. [What is a scenario?](#what-is-a-scenario)
2. [Directory layout](#directory-layout)
3. [Scenario skeleton](#scenario-skeleton)
4. [Dashboard configuration keys](#dashboard-configuration-keys)
5. [Setting entity states safely](#setting-entity-states-safely)
6. [Setup and teardown blocks](#setup-and-teardown-blocks)
7. [Interactions reference](#interactions-reference)
8. [Assertions reference](#assertions-reference)
9. [Snapshot assertions](#snapshot-assertions)
10. [Avoiding interference with a local HA instance](#avoiding-interference-with-a-local-ha-instance)
11. [Shadow-root traversal](#shadow-root-traversal)
12. [Complete annotated example](#complete-annotated-example)

---

## What is a scenario?

A scenario is a single `.yaml` file that describes:

1. **Which Lovelace card(s)** to push to the test dashboard.
2. **What entity states** need to be prepared before the page loads (`setup:`).
3. **What interactions** (hovers, clicks, service calls) to run after the page loads.
4. **What assertions** (CSS properties, snapshots, element presence) to verify.
5. Optionally, **teardown** steps to run after assertions — even when the test fails.

No Python code is required.  The test runner (`test_scenarios.py`) picks up
every `.yaml` file in your scenarios directory automatically.

---

## Directory layout

Point the scenario runner at your project's directories from `conftest.py`
**before** tests are collected:

```python
# tests/conftest.py
from pathlib import Path
import ha_testcontainer.visual.scenario_runner as sr

sr.SCENARIOS_DIR = Path(__file__).parent / "scenarios"
sr.SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
sr.REPO_ROOT     = Path(__file__).parent.parent
```

A typical project layout looks like this:

```
tests/
├── conftest.py             # sets sr.SCENARIOS_DIR / SNAPSHOTS_DIR / REPO_ROOT
├── visual/
│   ├── test_scenarios.py   # parametrised test (copy from ha-tests/visual/)
│   ├── scenarios/
│   │   ├── my_card_default.yaml
│   │   └── my_card_hover.yaml
│   └── snapshots/          # committed baseline PNGs live here
```

---

## Scenario skeleton

```yaml
# tests/visual/scenarios/my_card_default.yaml
id: my_card_default          # unique identifier — used by pytest -k filtering
description: "Default state of my-card with a light entity"   # optional, human-readable

view_path: my-card-test      # URL path segment appended to the Lovelace URL

card:                        # single card pushed to the test dashboard
  type: my-card
  entity: light.bed_light

setup:                       # state preparation — runs BEFORE page navigation
  - type: ha_service
    domain: light
    service: turn_on
    entity_id: light.bed_light

interactions:                # runs AFTER page navigation
  - type: hover
    root: my-card
    selector: ha-tile-icon
    settle_ms: 600

assertions:
  - type: snapshot
    name: my_card_default
```

---

## Dashboard configuration keys

Each scenario must have **exactly one** of the following top-level keys:

| Key | When to use |
|---|---|
| `card:` | A single card definition. Automatically wrapped in a `sections` view. |
| `cards:` | A list of cards, all placed in the same grid section. |
| `dashboard:` | A complete Lovelace dashboard dict (must contain `views:`). Pushed verbatim. |

`view_path:` is required in all three cases so the runner knows which URL to
navigate to.

### Single card

```yaml
view_path: tile-test
card:
  type: tile
  entity: light.bed_light
```

### Multiple cards

```yaml
view_path: tile-test
cards:
  - type: tile
    entity: light.bed_light
  - type: tile
    entity: light.ceiling_lights
```

### Full dashboard

Use this when you need multiple views, non-default view types, or precise
control over the dashboard layout:

```yaml
view_path: my-view
dashboard:
  title: My Test Dashboard
  views:
    - title: My View
      path: my-view
      type: sections
      sections:
        - type: grid
          cards:
            - type: tile
              entity: light.bed_light
```

---

## Setting entity states safely

### Use demo entities from the built-in `demo` integration

The test container's default `ha-config/configuration.yaml` enables the HA
`demo` integration, which provides a rich set of pre-populated entities
(`light.bed_light`, `light.ceiling_lights`, `sensor.outside_temperature`,
`weather.home`, etc.) with no extra setup.

**Prefer demo entities** over custom `input_*` helpers wherever possible.
They are always available, their initial states are deterministic, and they do
not pollute any real Home Assistant instance.

### Set a known state before the page loads — use `setup:`

Use `ha_service` calls inside a `setup:` block to put entities into the
exact state required by the test *before* the browser navigates to the
dashboard.  This avoids race conditions where the page renders before the
service call completes.

```yaml
setup:
  - type: ha_service
    domain: light
    service: turn_on
    entity_id: light.bed_light
    data:
      brightness: 255
      color_temp: 250

  - type: ha_service
    domain: light
    service: turn_off
    entity_id: light.ceiling_lights
```

> **Why `setup:` and not `interactions:`?**
> `interactions:` runs *after* navigation.  For entity states that affect the
> card's initial render, always use `setup:` so the state is already in place
> when the browser first loads the page.

### Reset state in `teardown:`

When a test changes entity state that another test might read, restore the
original state in `teardown:`.  The teardown block runs even if the test
fails, preventing state leakage between scenarios.

```yaml
teardown:
  - type: ha_service
    domain: light
    service: turn_off
    entity_id: light.bed_light
```

### Passing extra data to service calls

The shorthand `entity_id:` key maps to `data.entity_id`.  For any other
service data, use the `data:` sub-key:

```yaml
setup:
  - type: ha_service
    domain: light
    service: turn_on
    entity_id: light.bed_light
    data:
      rgb_color: [255, 100, 0]
      brightness: 200
```

---

## Setup and teardown blocks

| Block | Runs | Typical use |
|---|---|---|
| `setup:` | Before page navigation | `ha_service`, `device_registry_update`, `wait` |
| `interactions:` | After page navigation | `hover`, `click`, `ha_service`, `wait` |
| `teardown:` | After assertions (always, even on failure) | `ha_service` state reset, `wait` |

Only `ha_service`, `device_registry_update`, and `wait` are meaningful in
`setup:` and `teardown:` because there is no live browser page at those
points.

---

## Interactions reference

### `ha_service` — call a Home Assistant service

```yaml
- type: ha_service
  domain: light
  service: turn_on
  entity_id: light.bed_light      # shorthand for data.entity_id
  data:                           # optional extra service data
    brightness: 128
  settle_ms: 500                  # optional, default 0 — wait after the call
```

### `hover` — hover over a page element

Simple form (direct CSS selector, no shadow-root crossing):

```yaml
- type: hover
  selector: my-card
  settle_ms: 600
```

Shadow-root form:

```yaml
- type: hover
  root: hui-tile-card
  selector: ha-tile-icon
  settle_ms: 800
```

### `hover_away` — dismiss hover state

```yaml
- type: hover_away
  settle_ms: 500
```

### `click` — click an element

```yaml
- type: click
  root: hui-tile-card
  selector: ha-tile-icon
  settle_ms: 1500
```

### `wait` — unconditional pause

```yaml
- type: wait
  ms: 1000
```

### `device_registry_update` — assign a device to an area

```yaml
- type: device_registry_update
  entity_id: light.bed_light      # OR device_id: <id>
  area_name: Bedroom              # OR area_id: <id>
```

### `dispatch_window_event` — fire a browser-level custom event

```yaml
- type: dispatch_window_event
  event: config-refresh
  settle_ms: 1000
```

### `write_config_file` — write a file into the HA config directory

```yaml
- type: write_config_file
  path: my_config.yaml
  content: |
    my_key: my_value
```

---

## Assertions reference

### `snapshot` — pixel-diff screenshot comparison

```yaml
- type: snapshot
  name: my_card_hover             # baseline filename (without .png)
  root: my-card                   # optional — crop to this element
  padding: "20 8 8 8"            # optional — extra whitespace (top right bottom left)
  threshold: 0.001               # optional — pixel-diff tolerance (0.0–1.0)
```

### `element_present` / `element_absent`

```yaml
- type: element_present
  root: my-card
  selector: ha-tile-icon

- type: element_absent
  root: my-card
  selector: .error-badge
```

### `css_property`

The `property` value is read as a **JavaScript property** on the
`CSSStyleDeclaration` object returned by `getComputedStyle(el)`, so use
**camelCase** names (e.g. `backgroundColor`, not `background-color`).

```yaml
- type: css_property
  root: my-card
  selector: ha-card
  property: backgroundColor
  expected: "rgb(0, 200, 100)"
```

### `css_variable`

The `property` value is passed to `getComputedStyle(el).getPropertyValue(prop)`,
so use the CSS custom property name exactly as declared, including the `--` prefix
and any hyphens.

```yaml
- type: css_variable
  root: my-card
  selector: ha-card
  property: --ha-card-background
  expected: "rgba(0,0,0,0)"
```

### `text_equals` / `text_startswith`

```yaml
- type: text_equals
  root: my-card
  selector: .card-header
  expected: "Bedroom Light"

- type: text_startswith
  root: my-card
  selector: .state-info
  expected: "on"
```

---

## Snapshot assertions

Snapshots follow a **two-file convention**:

| File | Description |
|---|---|
| `snapshots/<name>.png` | Committed baseline — the ground truth |
| `snapshots/<name>.actual.png` | Generated on every run — gitignored |

On the **first run** (or with `SNAPSHOT_UPDATE=1`) the actual screenshot
becomes the baseline.  Subsequent runs diff the two; pixel differences beyond
the `threshold` cause the test to fail.

```bash
# Create or refresh baselines
SNAPSHOT_UPDATE=1 pytest tests/visual/

# Run against existing baselines
pytest tests/visual/
```

> **Important** — baselines are committed in the *consumer's* repository.
> They should never appear in ha-testcontainer's own history.  Add
> `tests/visual/snapshots/*.actual.png` (and any unreferenced `*.png` files)
> to `.gitignore`.

> **See also: [Generating Documentation Images guide](README_DOC_IMAGES.md)** — use
> `doc_image:` and `doc_animation:` in scenario YAML to also capture documentation
> screenshots and animated GIFs as part of the same test run.

---

## Avoiding interference with a local HA instance

### The test container is isolated by default

When you run `pytest`, the `ha` fixture starts a **fresh Docker container** on
a random host port.  It is completely separate from any Home Assistant
instance you may be running locally (e.g. on port 8123).  Scenario YAML files
push their Lovelace configuration to this ephemeral container; nothing is
written to your personal HA configuration.

### Never hard-code `localhost:8123`

Do not reference `http://localhost:8123` anywhere in test code or YAML.
Always use the `ha_url` fixture value (or the `${HA_URL}` environment
variable), which resolves to the correct port for the test container.

### Use the `HA_URL` / `HA_TOKEN` variables only for CI pre-provisioned instances

If you set `HA_URL` and `HA_TOKEN` environment variables, the plugin skips
Docker and connects to that external instance instead.  **Do not point this at
your personal Home Assistant** — scenario tests *will* overwrite the Lovelace
dashboard configuration on whatever instance they connect to.  Reserve this
mode for dedicated CI or staging instances.

### Avoid entities that exist only in your personal HA

Scenarios that reference entities like `light.living_room_lamp` will fail (or
produce incorrect snapshots) when run by another developer whose HA does not
have those entities.  Instead:

- Use **demo entities** (`light.bed_light`, `light.ceiling_lights`, etc.)
  which are always available because the `demo` integration is enabled in the
  test container's `ha-config/configuration.yaml`.
- Declare any custom `input_boolean`, `input_number`, or `input_text` helpers
  you need directly in your project's `ha-config/configuration.yaml` (or in a
  dedicated YAML file included from it) so that every developer gets the same
  set of entities.

### Use `setup:` to reach a deterministic initial state

Even if a demo entity's default state is appropriate for one test, the
*previous* test's teardown (or a concurrent test) could have changed it.
Always use `setup:` to explicitly set every entity state your scenario depends
on.  This makes scenarios **order-independent** and safe to run in parallel.

```yaml
# BAD — relies on whatever state the entity happens to be in
interactions:
  - type: hover
    root: hui-tile-card
    selector: ha-tile-icon

# GOOD — state is guaranteed before the page loads
setup:
  - type: ha_service
    domain: light
    service: turn_on
    entity_id: light.bed_light
interactions:
  - type: hover
    root: hui-tile-card
    selector: ha-tile-icon
```

### Keep `view_path` unique per scenario

Each scenario pushes its card config to a Lovelace view identified by
`view_path`.  If two scenarios share the same `view_path` they can overwrite
each other when run in parallel.  Use a value that is unique to the scenario,
for example `my-card-default` or `my-card-hover`.

---

## Shadow-root traversal

Home Assistant's frontend uses shadow DOM extensively.  The `root:` field in
interactions and assertions supports a **chain of shadow-piercing selectors**:

```yaml
# Single selector — found anywhere via shadow-piercing search
root: hui-tile-card
selector: ha-tile-icon

# Chain — each step resolved inside the previous element's shadowRoot
root:
  - my-card
  - hui-tile-card
selector: ha-tile-icon

# Target the second card when multiple identical cards are present
root:
  - div.card:nth-of-type(2) my-card
  - hui-tile-card
selector: ha-tile-icon
```

> **Note** — each step uses a depth-first shadow-piercing search.  Pseudo-
> classes such as `:nth-of-type` operate among siblings at the level where the
> element is found, not across shadow-root boundaries.  If two `my-card`
> elements are both direct children of the same grid section, wrap the
> positional selector together with the element tag in a single string (as in
> the third example above).

---

## Complete annotated example

The following scenario exercises a `tile` card with a light entity, verifies
its appearance in both the on and off states, and takes baseline snapshots.

```yaml
# tests/visual/scenarios/tile_card_light.yaml

id: tile_card_light
description: "Tile card with a light entity — on and off states"

view_path: tile-light-test

card:
  type: tile
  entity: light.bed_light

# --- State preparation ---
# Runs before the browser navigates to the page.
# Guarantees a deterministic starting state regardless of what previous
# tests may have done.
setup:
  - type: ha_service
    domain: light
    service: turn_on
    entity_id: light.bed_light
    data:
      brightness: 255
    settle_ms: 300

# --- Assertions for the "on" state ---
assertions:
  - type: element_present
    root: hui-tile-card
    selector: ha-tile-icon

  - type: snapshot
    name: tile_light_on
    root: hui-tile-card
    padding: 8
    threshold: 0.002

# --- Interactions that change state mid-test ---
# Turn the light off via the card's toggle, then re-assert.
interactions:
  - type: ha_service
    domain: light
    service: turn_off
    entity_id: light.bed_light
    settle_ms: 800

# --- Cleanup ---
# Always restore the entity to a neutral state.
teardown:
  - type: ha_service
    domain: light
    service: turn_off
    entity_id: light.bed_light
```

> **Tip** — if you need to assert multiple states in a single scenario, split
> assertions and intermediate interactions across the `interactions:` list:
>
> ```yaml
> interactions:
>   - type: ha_service
>     domain: light
>     service: turn_off
>     entity_id: light.bed_light
>     settle_ms: 800
>
> assertions:
>   - type: snapshot
>     name: tile_light_off
>     root: hui-tile-card
>     padding: 8
> ```
>
> For more complex multi-state scenarios, consider splitting them into
> separate YAML files so each test is independently runnable and clearly named.
