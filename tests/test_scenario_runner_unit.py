"""Unit tests for scenario_runner interaction types — no Docker or browser required.

Covers interaction dispatch logic using mocks so that a running Playwright
browser is not needed.
"""

from __future__ import annotations

import io
import shutil
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


class TestObjectPropertyAssertions:
    """Object-property assertion dispatch and missing-path handling."""

    @pytest.mark.parametrize(
        ("atype", "result"),
        [
            ("object_property_present", {"present": True, "text": "value"}),
            ("object_property_absent", {"present": False, "missingAtLast": True}),
            (
                "object_property_text_equals",
                {"present": True, "text": "Kitchen Light"},
            ),
            (
                "object_property_text_starts_with",
                {"present": True, "text": "Kitchen Light"},
            ),
        ],
    )
    def test_supported_types_accept_matching_properties(self, atype, result):
        page = _make_page()
        page.evaluate.return_value = result
        assertion = {
            "type": atype,
            "root": "my-card",
            "selector": "ha-card",
            "property": "hass.states",
            "expected": "Kitchen Light",
        }

        sr.run_assertions(page, {"assertions": [assertion]})

        script = page.evaluate.call_args.args[0]
        assert "missingAtLast" in script
        assert "hass.states" in script

    @pytest.mark.parametrize(
        ("atype", "result"),
        [
            ("object_property_present", {"present": False, "missing": "hass"}),
            (
                "object_property_text_equals",
                {"present": False, "missing": "hass.states"},
            ),
            (
                "object_property_text_starts_with",
                {"present": False, "missing": "hass.states"},
            ),
        ],
    )
    def test_missing_property_is_a_non_match(self, atype, result):
        page = _make_page()
        page.evaluate.return_value = result
        assertion = {
            "type": atype,
            "root": "my-card",
            "selector": "ha-card",
            "property": "hass.states",
            "expected": "on",
        }

        with pytest.raises(AssertionError):
            sr.run_assertions(page, {"assertions": [assertion]})

    def test_absent_requires_only_the_final_property_to_be_missing(self):
        page = _make_page()
        page.evaluate.return_value = {
            "present": False,
            "missing": "hass.states",
            "missingAtLast": False,
        }
        assertion = {
            "type": "object_property_absent",
            "root": "my-card",
            "selector": "ha-card",
            "property": "hass.states.legacy_value",
        }

        with pytest.raises(AssertionError, match="final property"):
            sr.run_assertions(page, {"assertions": [assertion]})


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


class TestInputTextInteraction:
    """run_interactions dispatches input_text correctly."""

    def test_input_text_with_selector(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {
                    "type": "input_text",
                    "selector": "#input-id",
                    "text": "Hello",
                    "delay_ms": 150,
                    "settle_ms": 400,
                }
            ]
        }
        sr.run_interactions(page, scenario)
        page.locator.assert_called_once_with("#input-id")
        page.locator("#input-id").click.assert_called_once()
        page.keyboard.type.assert_called_once_with("Hello", delay=150)
        page.wait_for_timeout.assert_called_once_with(400)

    def test_input_text_defaults(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {
                    "type": "input_text",
                    "selector": "#input-id",
                    "text": "Hello",
                }
            ]
        }
        sr.run_interactions(page, scenario)
        page.keyboard.type.assert_called_once_with("Hello", delay=100)
        page.wait_for_timeout.assert_called_once_with(500)

    def test_input_text_coerces_strings(self):
        page = _make_page()
        scenario = {
            "interactions": [
                {
                    "type": "input_text",
                    "selector": "#input-id",
                    "text": "Hello",
                    "delay_ms": "80",
                    "settle_ms": "300",
                }
            ]
        }
        sr.run_interactions(page, scenario)
        page.keyboard.type.assert_called_once_with("Hello", delay=80)
        page.wait_for_timeout.assert_called_once_with(300)

    def test_input_text_with_root(self, monkeypatch):
        page = _make_page()
        get_rect = MagicMock(return_value={"x": 10, "y": 20, "w": 30, "h": 40})
        monkeypatch.setattr(sr, "_get_element_rect", get_rect)

        scenario = {
            "interactions": [
                {
                    "type": "input_text",
                    "root": "my-root",
                    "selector": "input",
                    "text": "Hello",
                }
            ]
        }
        sr.run_interactions(page, scenario)
        get_rect.assert_called_once_with(page, scenario["interactions"][0])
        # Click should be called on the center: x + w/2 = 25, y + h/2 = 40
        page.mouse.click.assert_called_once_with(25, 40)
        page.keyboard.type.assert_called_once_with("Hello", delay=100)


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

    def test_root_clip_is_recomputed_for_each_frame(self, tmp_path, monkeypatch):
        page = _make_page()
        page.screenshot.side_effect = [
            _png_bytes(4, 3, (255, 0, 0)),
            _png_bytes(8, 6, (0, 255, 0)),
        ]

        get_rect = MagicMock(
            side_effect=[
                {"x": 10, "y": 20, "w": 4, "h": 3},
                {"x": 10, "y": 20, "w": 8, "h": 6},
            ]
        )
        monkeypatch.setattr(sr, "_get_doc_image_rect", get_rect)
        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")

        scenario = {
            "doc_animation": {
                "output": "docs/assets/root-expands.gif",
                "root": "$card",
                "interval_ms": 1,
                "dither": False,
                "frames": 2,
            }
        }

        sr.capture_doc_animation(page, scenario)

        assert get_rect.call_count == 2
        assert page.screenshot.call_args_list[0].kwargs["clip"] == {
            "x": 10,
            "y": 20,
            "width": 4,
            "height": 3,
        }
        assert page.screenshot.call_args_list[1].kwargs["clip"] == {
            "x": 10,
            "y": 20,
            "width": 8,
            "height": 6,
        }

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


class TestDocAnimationMp4:
    """doc_animation with .mp4 output format."""

    def test_mp4_generation_and_verification(self, tmp_path, monkeypatch):
        page = _make_page()
        # Side effect for screenshots
        page.screenshot.side_effect = [
            _png_bytes(8, 6, (255, 0, 0)),
            _png_bytes(8, 6, (0, 255, 0)),
        ]

        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")

        scenario = {
            "doc_animation": {
                "output": "docs/assets/animation.mp4",
                "interval_ms": 100,
                "frames": 2,
            }
        }

        # 1. Create/Update: This will compile MP4 via ffmpeg
        sr.capture_doc_animation(page, scenario)

        output_file = tmp_path / "docs/assets/animation.mp4"
        assert output_file.exists()
        # Verify it has some bytes (should be valid mp4 format)
        assert output_file.stat().st_size > 0

        # 2. Comparison: Run without update to verify frame extraction & exact/threshold check
        # We need to supply screenshots again since we run the test again
        page.screenshot.side_effect = [
            _png_bytes(8, 6, (255, 0, 0)),
            _png_bytes(8, 6, (0, 255, 0)),
        ]
        monkeypatch.delenv("DOC_IMAGE_UPDATE", raising=False)

        # Should pass because screenshots match existing mp4 frames closely (or exactly within threshold)
        sr.capture_doc_animation(page, scenario)

        # 3. Validation failure: Run with slightly different screenshots to trigger AssertionError
        page.screenshot.side_effect = [
            _png_bytes(8, 6, (0, 0, 255)),  # Blue instead of Red
            _png_bytes(8, 6, (0, 255, 0)),
        ]
        with pytest.raises(AssertionError, match="Doc animation mismatch"):
            sr.capture_doc_animation(page, scenario)

    def test_mp4_missing_ffmpeg_raises_runtime_error(self, tmp_path, monkeypatch):
        page = _make_page()
        monkeypatch.setattr(sr, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("DOC_IMAGE_UPDATE", "1")
        # Mock shutil.which to return None so ffmpeg is not found
        monkeypatch.setattr(shutil, "which", lambda _: None)

        scenario = {
            "doc_animation": {
                "output": "docs/assets/animation_no_ffmpeg.mp4",
                "frames": 2,
            }
        }

        with pytest.raises(RuntimeError, match="ffmpeg is required to capture MP4 animations"):
            sr.capture_doc_animation(page, scenario)

