"""Unit tests for ha_testcontainer.integrations."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from ha_testcontainer.integrations import install_integrations


def _make_release_zip(*component_names: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for component in component_names:
            base = f"example-1.0.0/custom_components/{component}/"
            zf.writestr(base, "")
            zf.writestr(f"{base}manifest.json", "{}")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, *, json_data=None, content: bytes = b"", status_code: int = 200):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._json_data


def test_infers_domain_for_single_component(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    integrations_yaml = tmp_path / "integrations.yaml"
    integrations_yaml.write_text("- repo: owner/repo\n")
    cc_dir = tmp_path / "custom_components"

    archive = _make_release_zip("uix")

    def _fake_get(url: str, **_kwargs):
        if url.endswith("/releases/latest"):
            return _FakeResponse(json_data={"tag_name": "v1.0.0"})
        if url.endswith("/archive/refs/tags/v1.0.0.zip"):
            return _FakeResponse(content=archive)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("ha_testcontainer.integrations.requests.get", _fake_get)

    domains = install_integrations(cc_dir, integrations_yaml=integrations_yaml)

    assert domains == ["uix"]
    assert (cc_dir / "uix" / "manifest.json").exists()


def test_uses_explicit_domain_and_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    integrations_yaml = tmp_path / "integrations.yaml"
    integrations_yaml.write_text(
        "- repo: owner/repo\n"
        "  domain: custom_domain\n"
        "  version: 2.3.4\n"
    )
    cc_dir = tmp_path / "custom_components"

    archive = _make_release_zip("from_archive")

    def _fake_get(url: str, **_kwargs):
        if url.endswith("/releases/tags/v2.3.4"):
            return _FakeResponse(json_data={"tag_name": "v2.3.4"})
        if url.endswith("/archive/refs/tags/v2.3.4.zip"):
            return _FakeResponse(content=archive)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("ha_testcontainer.integrations.requests.get", _fake_get)

    domains = install_integrations(cc_dir, integrations_yaml=integrations_yaml)

    assert domains == ["custom_domain"]
    assert (cc_dir / "from_archive" / "manifest.json").exists()


def test_requires_domain_for_multi_component_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    integrations_yaml = tmp_path / "integrations.yaml"
    integrations_yaml.write_text("- repo: owner/repo\n")
    cc_dir = tmp_path / "custom_components"

    archive = _make_release_zip("alpha", "beta")

    def _fake_get(url: str, **_kwargs):
        if url.endswith("/releases/latest"):
            return _FakeResponse(json_data={"tag_name": "v1.0.0"})
        if url.endswith("/archive/refs/tags/v1.0.0.zip"):
            return _FakeResponse(content=archive)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("ha_testcontainer.integrations.requests.get", _fake_get)

    with pytest.raises(ValueError, match="must include 'domain'"):
        install_integrations(cc_dir, integrations_yaml=integrations_yaml)
