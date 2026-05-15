"""Unit tests for scenario_runner interaction types — no Docker or browser required.

Covers interaction dispatch logic using mocks so that a running Playwright
browser is not needed.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, call

import pytest
from PIL import Image, ImageSequence

import ha_testcontainer.visual.scenario_runner as sr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page() -> MagicMock:
    """Return a lightweight mock that records Playwright Page calls."""
    return MagicMock()


# ---------------------------------------------------------------------------
# set_viewport interaction
# ---------------------------------------------------------------------------


class TestSetViewportInteraction:
    """run_interactions dispatches set_viewport correctly."""

    def test_set_viewport_calls_set_viewport_size(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": 375, "height": 812},
            ]
        }
        sr.run_interactions(page, scenario)
        page.set_viewport_size.assert_called_once_with({"width": 375, "height": 812})

    def test_set_viewport_no_settle_ms_by_default(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": 1280, "height": 800},
            ]
        }
        sr.run_interactions(page, scenario)
        page.wait_for_timeout.assert_not_called()

    def test_set_viewport_settle_ms_waits(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": 768, "height": 1024, "settle_ms": 300},
            ]
        }
        sr.run_interactions(page, scenario)
        page.set_viewport_size.assert_called_once_with({"width": 768, "height": 1024})
        page.wait_for_timeout.assert_called_once_with(300)

    def test_set_viewport_coerces_string_dimensions(self):
        """width/height may arrive as strings from YAML and must be coerced to int."""
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "set_viewport", "width": "390", "height": "844"},
            ]
        }
        sr.run_interactions(page, scenario)
        page.set_viewport_size.assert_called_once_with({"width": 390, "height": 844})

    def test_unknown_type_raises(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {"type": "not_a_real_type"},
            ]
        }
        with pytest.raises(ValueError, match="Unknown interaction type"):
            sr.run_interactions(page, scenario)


def _png_bytes(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    """Return an in-memory PNG of the requested size and solid RGB color."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _read_gif_frames(path) -> list[Image.Image]:
    """Return frames from the GIF at *path* as per-frame RGB Pillow images."""
    with Image.open(path) as gif:
        if gif.format != "GIF":
            raise ValueError(f"Expected GIF file, got: {gif.format}")
        return [f.copy().convert("RGB") for f in ImageSequence.Iterator(gif)]


class TestDocAnimationViewportNormalization:
    """doc_animation normalizes variable-size viewport frames to one canvas."""

    def test_large_to_small_viewport_clears_uncovered_area(self, tmp_path, monkeypatch):
        page = _make_page()
        page.screenshot.side_effect = [
            _png_bytes(8, 6, (255, 0, 0)),
            _png_bytes(4, 3, (0, 255, 0)),
        ]

        save_kwargs: dict[str, object] = {}
        orig_save = Image.Image.save

        def _save_with_capture(self, file_obj, format=None, **params):
            save_kwargs.update(params)
            return orig_save(self, file_obj, format=format, **params)

        monkeypatch.setattr(Image.Image, "save", _save_with_capture)
        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")

        scenario = {
            "doc_animation": {
                "output": "docs/assets/viewport-large-small.gif",
                "interval_ms": 1,
                "dither": False,
                "segments": [
                    {"interactions": [{"type": "set_viewport", "width": 8, "height": 6}], "frames": 1},
                    {"interactions": [{"type": "set_viewport", "width": 4, "height": 3}], "frames": 1},
                ],
            }
        }

        sr.capture_doc_animation(page, scenario)

        output = tmp_path / "docs/assets/viewport-large-small.gif"
        frames = _read_gif_frames(output)
        assert [f.size for f in frames] == [(8, 6), (8, 6)]
        # (6,4) sits outside the 4x3 second frame; it must be cleared to white.
        assert frames[1].getpixel((6, 4)) == (255, 255, 255)
        assert save_kwargs.get("disposal") == 2
        assert page.set_viewport_size.call_args_list == [
            call({"width": 8, "height": 6}),
            call({"width": 4, "height": 3}),
        ]

    def test_small_to_large_viewport_uses_max_canvas(self, tmp_path, monkeypatch):
        page = _make_page()
        page.screenshot.side_effect = [
            _png_bytes(4, 3, (0, 255, 0)),
            _png_bytes(8, 6, (0, 0, 255)),
        ]

        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")

        scenario = {
            "doc_animation": {
                "output": "docs/assets/viewport-small-large.gif",
                "interval_ms": 1,
                "dither": False,
                "segments": [
                    {"interactions": [{"type": "set_viewport", "width": 4, "height": 3}], "frames": 1},
                    {"interactions": [{"type": "set_viewport", "width": 8, "height": 6}], "frames": 1},
                ],
            }
        }

        sr.capture_doc_animation(page, scenario)

        output = tmp_path / "docs/assets/viewport-small-large.gif"
        frames = _read_gif_frames(output)
        assert [f.size for f in frames] == [(8, 6), (8, 6)]
        # (6,4) sits outside the 4x3 first frame; it must be cleared to white.
        assert frames[0].getpixel((6, 4)) == (255, 255, 255)

    def test_mixed_segment_interactions_keep_consistent_frame_size(self, tmp_path, monkeypatch):
        page = _make_page()
        page.screenshot.side_effect = [
            _png_bytes(8, 6, (255, 0, 0)),
            _png_bytes(5, 4, (0, 255, 0)),
            _png_bytes(3, 2, (0, 0, 255)),
        ]

        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")

        scenario = {
            "doc_animation": {
                "output": "docs/assets/viewport-mixed-segments.gif",
                "interval_ms": 1,
                "dither": False,
                "segments": [
                    {"interactions": [{"type": "set_viewport", "width": 8, "height": 6}], "frames": 1},
                    {"interactions": [{"type": "set_viewport", "width": 5, "height": 4}], "frames": 1},
                    {"interactions": [{"type": "set_viewport", "width": 3, "height": 2}], "frames": 1},
                ],
            }
        }

        sr.capture_doc_animation(page, scenario)

        output = tmp_path / "docs/assets/viewport-mixed-segments.gif"
        frames = _read_gif_frames(output)
        assert [f.size for f in frames] == [(8, 6), (8, 6), (8, 6)]
        # (7,5) is outside both smaller later frames and must be white.
        assert frames[1].getpixel((7, 5)) == (255, 255, 255)
        assert frames[2].getpixel((7, 5)) == (255, 255, 255)

    def test_raises_when_no_frames_captured(self, tmp_path, monkeypatch):
        page = _make_page()
        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")

        scenario = {
            "doc_animation": {
                "output": "docs/assets/no-frames.gif",
                "frames": 0,
            }
        }

        with pytest.raises(AssertionError, match="captured 0 frames"):
            sr.capture_doc_animation(page, scenario)
