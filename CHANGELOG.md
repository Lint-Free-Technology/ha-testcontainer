# CHANGELOG

<!-- version list -->

## v2.1.0 (2026-05-06)

### Features

- Add local plugin registration for dashboard plugin testing
  ([`be2c85d`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/be2c85da45bcd9f69b8697b97ac9f84580ebe131))


## v2.0.0 (2026-05-06)

### Breaking Changes

- **Renamed environment variables**: `LOVELACE_EXTRA_CONFIG_DIR` → `HA_EXTRA_CONFIG_DIR`,
  `LOVELACE_PLUGINS_YAML` → `HA_PLUGINS_YAML`, `LOVELACE_SETUP_INTEGRATION` → `HA_SETUP_INTEGRATION`.
  Update any scripts, Makefiles, or CI config that set these variables.
- **pytest plugin auto-registered**: `ha_testcontainer[test]` now registers a `pytest11` entry-point
  (`ha_testcontainer.pytest_plugin`) that provides the `ha`, `ha_url`, `ha_token`,
  `ha_lovelace_url_path`, `ha_browser_context`, and `ha_page` fixtures automatically.
  Consumers who previously copied conftest.py from ha-tests/ should remove those copies.

### Features

- Ship the visual test framework as `ha_testcontainer.visual.*` sub-modules:
  `ha_testcontainer.visual.scenario_runner`, `ha_testcontainer.visual.lovelace_helpers`,
  `ha_testcontainer.visual.cursors`.
- Add `ha_testcontainer.plugins` — `download_lovelace_plugins()` for downloading Lovelace JS plugins.
- Add `ha_testcontainer.ha_server` — persistent HA dev server for fast iterative testing
  (`python -m ha_testcontainer.ha_server`).
- Add `ha_testcontainer.pytest_plugin` — session/visual fixtures as a registered pytest plugin.
- Add `PyYAML>=6.0` to `[test]` and `[visual]` extras (required by `scenario_runner` and `plugins`).
- Convert `ha-tests/` files to thin shims that import from `ha_testcontainer.*`.

## v1.1.0 (2026-05-06)

### Bug Fixes

- Move UIX-specific LICENSES.md from generic ha-config to ha-tests/uix parking lot
  ([`ed630df`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/ed630df6aeac11d963529890ca787994e0697300))

### Features

- Add ha-tests generic Lovelace test framework with UIX parked for migration
  ([`ef55b1b`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/ef55b1b7289800acdec3b7b24de92649dbdc22da))


## v1.0.2 (2026-04-12)

### Bug Fixes

- Replace deprecated wait_for_logs with LogMessageWaitStrategy
  ([`227f219`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/227f219be9e26e4054a2c5c23915626ccae2aae9))


## v1.0.1 (2026-04-12)

### Bug Fixes

- Trigger PyPI publish
  ([`6bc4bd2`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/6bc4bd29e956f743e3bb58525e277c4ef99ac432))


## v1.0.0 (2026-04-12)

- Initial Release
