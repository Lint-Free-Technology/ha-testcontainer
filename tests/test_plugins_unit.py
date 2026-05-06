"""Unit tests for ha_testcontainer.plugins — no network or Docker required.

Covers the local-plugin paths introduced to allow consumers to register their
own dashboard plugin JS files:

* ``local_path`` entries in ``plugins.yaml``
* ``local_plugins_dir`` parameter / ``HA_LOCAL_PLUGINS_DIR`` env var
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ha_testcontainer.plugins import download_lovelace_plugins


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_www(tmp_path: Path) -> Path:
    """Return a fresh www_dir inside tmp_path (not yet created)."""
    return tmp_path / "ha-state" / "www"


def _read_resources(www_dir: Path) -> str:
    return (www_dir.parent / "lovelace_resources.yaml").read_text()


# ---------------------------------------------------------------------------
# local_path entry in plugins.yaml
# ---------------------------------------------------------------------------


class TestLocalPathInYaml:
    """plugins.yaml entries with a ``local_path`` key are copied, not downloaded."""

    def test_absolute_local_path_is_copied(self, tmp_path: Path) -> None:
        js_src = tmp_path / "my-plugin.js"
        js_src.write_text("/* my plugin */")

        yaml_file = tmp_path / "plugins.yaml"
        yaml_file.write_text(
            f"- local_path: {js_src}\n"
            "  filename: my-plugin.js\n"
        )

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, plugins_yaml=yaml_file)

        assert (www_dir / "my-plugin.js").read_text() == "/* my plugin */"

    def test_relative_local_path_resolved_from_yaml_dir(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "dist"
        src_dir.mkdir()
        (src_dir / "card.js").write_text("/* card */")

        yaml_file = tmp_path / "plugins.yaml"
        yaml_file.write_text(
            "- local_path: dist/card.js\n"
            "  filename: card.js\n"
        )

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, plugins_yaml=yaml_file)

        assert (www_dir / "card.js").read_text() == "/* card */"

    def test_missing_local_path_raises_file_not_found(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "plugins.yaml"
        yaml_file.write_text(
            "- local_path: does-not-exist.js\n"
            "  filename: does-not-exist.js\n"
        )

        www_dir = _make_www(tmp_path)
        with pytest.raises(FileNotFoundError, match="does-not-exist.js"):
            download_lovelace_plugins(www_dir, plugins_yaml=yaml_file)

    def test_local_plugin_registered_in_lovelace_resources(self, tmp_path: Path) -> None:
        js_src = tmp_path / "widget.js"
        js_src.write_text("/* widget */")

        yaml_file = tmp_path / "plugins.yaml"
        yaml_file.write_text(
            f"- local_path: {js_src}\n"
            "  filename: widget.js\n"
        )

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, plugins_yaml=yaml_file)

        resources = _read_resources(www_dir)
        assert "/local/widget.js" in resources
        assert "type: module" in resources


# ---------------------------------------------------------------------------
# local_plugins_dir parameter
# ---------------------------------------------------------------------------


class TestLocalPluginsDir:
    """JS files in local_plugins_dir are copied and registered."""

    def test_js_files_are_copied(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "alpha.js").write_text("/* alpha */")
        (plugin_dir / "beta.js").write_text("/* beta */")

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, local_plugins_dir=plugin_dir)

        assert (www_dir / "alpha.js").read_text() == "/* alpha */"
        assert (www_dir / "beta.js").read_text() == "/* beta */"

    def test_non_js_files_are_ignored(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.js").write_text("/* js */")
        (plugin_dir / "README.md").write_text("docs")

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, local_plugins_dir=plugin_dir)

        assert (www_dir / "plugin.js").exists()
        assert not (www_dir / "README.md").exists()

    def test_dir_plugins_registered_in_lovelace_resources(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "my-card.js").write_text("/* card */")

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, local_plugins_dir=plugin_dir)

        resources = _read_resources(www_dir)
        assert "/local/my-card.js" in resources
        assert "type: module" in resources

    def test_empty_dir_produces_empty_resource_list(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, local_plugins_dir=plugin_dir)

        resources = _read_resources(www_dir)
        assert "[]" in resources

    def test_local_dir_and_yaml_plugins_combined(self, tmp_path: Path) -> None:
        # yaml has a local_path entry
        js_src = tmp_path / "from-yaml.js"
        js_src.write_text("/* yaml */")
        yaml_file = tmp_path / "plugins.yaml"
        yaml_file.write_text(
            f"- local_path: {js_src}\n"
            "  filename: from-yaml.js\n"
        )

        # dir has another plugin
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "from-dir.js").write_text("/* dir */")

        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir, plugins_yaml=yaml_file, local_plugins_dir=plugin_dir)

        assert (www_dir / "from-yaml.js").exists()
        assert (www_dir / "from-dir.js").exists()

        resources = _read_resources(www_dir)
        assert "/local/from-yaml.js" in resources
        assert "/local/from-dir.js" in resources


# ---------------------------------------------------------------------------
# www_dir is created automatically
# ---------------------------------------------------------------------------


class TestWwwDirCreation:
    def test_www_dir_created_when_missing(self, tmp_path: Path) -> None:
        www_dir = tmp_path / "nested" / "www"
        assert not www_dir.exists()
        download_lovelace_plugins(www_dir)
        assert www_dir.is_dir()

    def test_lovelace_resources_written_with_no_plugins(self, tmp_path: Path) -> None:
        www_dir = _make_www(tmp_path)
        download_lovelace_plugins(www_dir)
        resources = _read_resources(www_dir)
        assert "[]" in resources
