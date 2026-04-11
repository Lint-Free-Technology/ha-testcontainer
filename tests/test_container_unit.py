"""Unit tests for HATestContainer — no Docker required.

These tests exercise the Python logic of :class:`~ha_testcontainer.HATestContainer`
(URL construction, token handling, API path normalization) using mocks so
that a running Docker daemon is not needed.

For integration tests that actually start a Home Assistant container, see
:mod:`tests.test_container`.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from testcontainers.core.container import DockerContainer

from ha_testcontainer import HATestContainer, HAVersion
from ha_testcontainer.container import HA_IMAGE, HA_PORT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def container() -> HATestContainer:
    """Return an :class:`HATestContainer` instance without touching Docker.

    All Docker-related methods on :class:`~testcontainers.core.container.DockerContainer`
    are mocked so the test can inspect pure Python logic.
    """
    with (
        patch.object(DockerContainer, "__init__", return_value=None),
        patch.object(DockerContainer, "with_exposed_ports", return_value=None),
        patch.object(DockerContainer, "with_env", return_value=None),
    ):
        c = HATestContainer(version=HAVersion.STABLE)
    return c


# ---------------------------------------------------------------------------
# HAVersion constants
# ---------------------------------------------------------------------------


class TestHAVersion:
    """HAVersion provides the expected string constants."""

    def test_stable(self):
        assert HAVersion.STABLE == "stable"

    def test_beta(self):
        assert HAVersion.BETA == "beta"

    def test_dev(self):
        assert HAVersion.DEV == "dev"


# ---------------------------------------------------------------------------
# Container initialisation
# ---------------------------------------------------------------------------


class TestHATestContainerInit:
    """HATestContainer.__init__ sets up attributes correctly."""

    def test_image_name_format(self):
        """The Docker image name is <HA_IMAGE>:<version>."""
        assert HA_IMAGE == "ghcr.io/home-assistant/home-assistant"
        for version in (HAVersion.STABLE, HAVersion.BETA, HAVersion.DEV, "2024.6.0"):
            assert f"{HA_IMAGE}:{version}" == f"ghcr.io/home-assistant/home-assistant:{version}"

    def test_token_starts_as_none(self, container: HATestContainer):
        """The token is None before :meth:`start` is called."""
        assert container._token is None  # noqa: SLF001


# ---------------------------------------------------------------------------
# get_token()
# ---------------------------------------------------------------------------


class TestGetToken:
    def test_raises_before_start(self, container: HATestContainer):
        """get_token() raises RuntimeError when the container has not been started."""
        with pytest.raises(RuntimeError, match="No token available"):
            container.get_token()

    def test_returns_token_after_set(self, container: HATestContainer):
        """get_token() returns the stored token once it is available."""
        container._token = "my-long-lived-token"  # noqa: SLF001
        assert container.get_token() == "my-long-lived-token"


# ---------------------------------------------------------------------------
# get_url()
# ---------------------------------------------------------------------------


class TestGetUrl:
    def test_returns_http_url(self, container: HATestContainer):
        """get_url() returns an http:// URL with the correct host and port."""
        container.get_container_host_ip = MagicMock(return_value="127.0.0.1")
        container.get_exposed_port = MagicMock(return_value="8123")
        assert container.get_url() == "http://127.0.0.1:8123"

    def test_uses_container_port(self, container: HATestContainer):
        """get_url() queries the exposed port for the HA port."""
        container.get_container_host_ip = MagicMock(return_value="localhost")
        container.get_exposed_port = MagicMock(return_value="49152")
        url = container.get_url()
        assert url.startswith("http://localhost:")
        container.get_exposed_port.assert_called_once_with(HA_PORT)


# ---------------------------------------------------------------------------
# api() — path normalization and authentication header
# ---------------------------------------------------------------------------


class TestApi:
    """api() correctly constructs the request URL and injects the token."""

    @pytest.fixture(autouse=True)
    def _setup(self, container: HATestContainer):
        container._token = "test-token"  # noqa: SLF001
        container.get_url = MagicMock(return_value="http://localhost:8123")
        self.container = container

    def _call_api(self, method: str, path: str) -> str:
        """Call api() and return the URL that was passed to requests.request."""
        with patch("ha_testcontainer.container.requests.request") as mock_req:
            mock_req.return_value = MagicMock()
            self.container.api(method, path)
            return mock_req.call_args[0][1]

    def test_prepends_api_prefix_to_bare_path(self):
        """A bare path like ``"states"`` becomes ``"/api/states"``."""
        url = self._call_api("GET", "states")
        assert url == "http://localhost:8123/api/states"

    def test_prepends_api_prefix_to_slash_path(self):
        """A path like ``"/states"`` becomes ``"/api/states"``."""
        url = self._call_api("GET", "/states")
        assert url == "http://localhost:8123/api/states"

    def test_does_not_double_prefix(self):
        """A path that already starts with ``/api/`` is not prefixed again."""
        url = self._call_api("GET", "/api/states")
        assert url == "http://localhost:8123/api/states"

    def test_injects_bearer_token(self):
        """The Authorization: Bearer header is always injected."""
        with patch("ha_testcontainer.container.requests.request") as mock_req:
            mock_req.return_value = MagicMock()
            self.container.api("GET", "states")
            headers = mock_req.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-token"

    def test_passes_json_kwargs(self):
        """Extra keyword arguments (e.g. ``json=``) are forwarded to requests."""
        with patch("ha_testcontainer.container.requests.request") as mock_req:
            mock_req.return_value = MagicMock()
            self.container.api("POST", "lovelace/config", json={"title": "Test"})
            assert mock_req.call_args[1]["json"] == {"title": "Test"}


# ---------------------------------------------------------------------------
# push_lovelace_config()
# ---------------------------------------------------------------------------


class TestPushLovelaceConfig:
    """push_lovelace_config() sends lovelace/config/save via WebSocket."""

    @pytest.fixture(autouse=True)
    def _setup(self, container: HATestContainer):
        container._token = "test-token"  # noqa: SLF001
        container.get_url = MagicMock(return_value="http://localhost:8123")
        self.container = container

    def _make_ws_mock(self, result_payload: dict) -> MagicMock:
        """Return a mock websocket that replays the HA auth handshake."""
        ws = MagicMock()
        ws.recv.side_effect = [
            '{"type": "auth_required"}',
            '{"type": "auth_ok"}',
            __import__("json").dumps(result_payload),
        ]
        return ws

    def test_success(self):
        """A successful save resolves without error."""
        ws_mock = self._make_ws_mock({"id": 1, "type": "result", "success": True, "result": None})
        with patch("ha_testcontainer.container.websocket.create_connection", return_value=ws_mock):
            self.container.push_lovelace_config({"title": "Dashboard", "views": []})
        ws_mock.close.assert_called_once()

    def test_sends_correct_command(self):
        """The lovelace/config/save command is sent with the config payload."""
        import json as _json
        config = {"title": "My Board", "views": [{"path": "default"}]}
        ws_mock = self._make_ws_mock({"id": 1, "type": "result", "success": True, "result": None})
        with patch("ha_testcontainer.container.websocket.create_connection", return_value=ws_mock):
            self.container.push_lovelace_config(config)
        # The third send() call carries the command (after auth_required recv + auth send).
        sent_calls = ws_mock.send.call_args_list
        # First send is auth, second is the command.
        command = _json.loads(sent_calls[1][0][0])
        assert command["type"] == "lovelace/config/save"
        assert command["config"] == config

    def test_raises_on_failure(self):
        """RuntimeError is raised when the WebSocket result reports failure."""
        ws_mock = self._make_ws_mock(
            {"id": 1, "type": "result", "success": False, "error": {"code": "unknown_error", "message": "oops"}}
        )
        with patch("ha_testcontainer.container.websocket.create_connection", return_value=ws_mock):
            with pytest.raises(RuntimeError, match="lovelace/config/save failed"):
                self.container.push_lovelace_config({"title": "Bad"})

    def test_raises_on_auth_failure(self):
        """RuntimeError is raised when WebSocket authentication is rejected."""
        ws = MagicMock()
        ws.recv.side_effect = [
            '{"type": "auth_required"}',
            '{"type": "auth_invalid"}',
        ]
        with patch("ha_testcontainer.container.websocket.create_connection", return_value=ws):
            with pytest.raises(RuntimeError, match="WebSocket auth failed"):
                self.container.push_lovelace_config({"title": "Bad"})
