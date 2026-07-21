# CHANGELOG

<!-- version list -->

## v2.7.0 (2026-07-21)

### Features

- Add javascript object property assertions
  ([`7542d49`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/7542d4978a5bfafe864c65d0043e12955cc8a724))

- Support MP4 format in doc-animation
  ([`2d3d92d`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/2d3d92d3f414305e88f56d8f317011224edd8d0a))


## v2.6.0 (2026-07-15)

### Chores

- **docs**: Update README to remove UIX testing instructions
  ([`ad89763`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/ad89763e1f7a065f90c3e1f8b75fbe236cb711c2))

### Features

- Add input_text interaction and documentation(#26)
  ([`bdd3920`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/bdd3920f4d88022587745d6aebf9e88ee0b88368))


## v2.5.3 (2026-06-10)

### Bug Fixes

- Correct fix for not creating dashboard when already exists. Incorrect api call was used.
  ([`97a24c6`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/97a24c67ada2014fb8bdb355e4571394bf93ed31))


## v2.5.2 (2026-06-10)

### Bug Fixes

- Avoid duplicate Lovelace dashboard creation which cause Home Assistant log errors
  ([#24](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/24),
  [`7f4b829`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/7f4b829bf5ecb8c5bcbe7251023accbd92aea2e4))

### Chores

- Bump upload-artifact to v5
  ([#22](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/22),
  [`0bd5e93`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/0bd5e933568b65d931d3e4db2b593a9ccaa03cb9))

- Remove obsolete UIX parked artifacts from ha-tests
  ([#21](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/21),
  [`fae88d0`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/fae88d0b3ac459d6c23605748516120fcc677a9d))

- Remove parked UIX test artifacts
  ([#21](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/21),
  [`fae88d0`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/fae88d0b3ac459d6c23605748516120fcc677a9d))

- **docs**: Add `ha-tests/integrations.yaml` placeholder and document it in repo file trees
  ([#23](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/23),
  [`0066040`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/0066040a47d1d57806d4552234acb06d49304440))

- **docs**: Update README to remove UIX reference and simplify version info
  ([`b82ce1c`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/b82ce1c09df01e7e855c499ce7e7e2d6b759d54f))

### Documentation

- Add integrations.yaml placeholder to ha-tests
  ([#23](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/23),
  [`0066040`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/0066040a47d1d57806d4552234acb06d49304440))

- Clarify empty integrations.yaml placeholder list
  ([#23](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/23),
  [`0066040`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/0066040a47d1d57806d4552234acb06d49304440))

- Remove migrated-tests origin note from ha-tests README
  ([#21](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/21),
  [`fae88d0`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/fae88d0b3ac459d6c23605748516120fcc677a9d))


## v2.5.1 (2026-06-03)

### Bug Fixes

- Upgrade workflow actions for Node 24 compatibility
  ([#20](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/20),
  [`0835f2b`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/0835f2b2426646e20e0c9f79412be0fcfa478a8d))


## v2.5.0 (2026-06-03)

### Bug Fixes

- Polish integration yaml startup handling
  ([#19](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/19),
  [`b652eb4`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/b652eb43532004d927b79e42382bd939bb9a073d))

### Chores

- **docs**: Change crop area behavior from locked to updated
  ([`eb139f5`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/eb139f587775a2cfa62b30df8c4e373f53869513))

### Features

- Add integrations yaml installer
  ([#19](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/19),
  [`b652eb4`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/b652eb43532004d927b79e42382bd939bb9a073d))

- Add YAML-driven integration provisioning for HA test startup
  ([#19](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/19),
  [`b652eb4`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/b652eb43532004d927b79e42382bd939bb9a073d))


## v2.4.0 (2026-06-01)

### Chores

- **deps**: Bump pypa/gh-action-pypi-publish in /.github/workflows
  ([#15](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/15),
  [`a5269f7`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/a5269f75415c6d27cd2c72492d4cd660a56ebf6f))

### Features

- Recompute animation root bounds per frame
  ([#18](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/18),
  [`07f29d1`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/07f29d1a9233e00ca5a988e7848d1063270ef18e))


## v2.3.0 (2026-05-15)

### Bug Fixes

- Guard doc_animation against zero captured frames
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

- Normalize doc_animation frames across viewport changes
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

### Chores

- Address final review nits for doc animation tests
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

- Finalize doc_animation ghost-frame fix polish
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

- Finalize style nits for doc animation fix
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

- Start doc_animation viewport ghost-frame fix
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

### Documentation

- Add set_viewport interaction to README_SCENARIOS.md
  ([#16](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/16),
  [`74043ad`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/74043ada7a1765dd0e2f86447b9c9d5a9d7ee928))

### Features

- Normalize doc_animation frames across viewport changes to eliminate GIF ghosting
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

### Testing

- Address review feedback in doc_animation regression tests
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))

- Simplify mixed segment viewport regression case
  ([#17](https://github.com/Lint-Free-Technology/ha-testcontainer/pull/17),
  [`450f13a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/450f13a330f41448c774282de8eaa424ed2069fa))


## v2.2.0 (2026-05-15)

### Documentation

- Add README_SCENARIOS.md and link from README.md
  ([`c620b18`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/c620b181577a5cbac1eb0f456de10c9fb84233c6))

- Fix css_property example (camelCase), add README_DOC_IMAGES.md, cross-link guides
  ([`6f1c37a`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/6f1c37a2b5536625280f4ba76dd5e60fde37212b))

### Features

- Add set_viewport interaction step for responsive testing
  ([`b2537d8`](https://github.com/Lint-Free-Technology/ha-testcontainer/commit/b2537d880c9e7cf81559325067993d36df83bf84))


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
