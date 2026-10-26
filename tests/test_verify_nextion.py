"""Tests for the Nextion release gate (scripts/verify_nextion/)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "verify_nextion"))

from verify_nextion import (  # noqa: E402
    check_portrait,
    check_sendme_parity,
    check_t_time_sendme,
    check_tft_version,
    parse_dump,
)


def test_parse_dump_reads_page_files():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "clock.txt").write_text("page clock\nwidgets")
        (p / "system.txt").write_text("page system\nvars")
        pages = parse_dump(p)
        assert set(pages) == {"clock", "system"}
        assert "widgets" in pages["clock"]["text"]


def test_t_time_disabled_fails():
    page = {
        "text": "Text tTime\n    Attributes\n        ID: 3\n        Send Component ID: disabled\n"
    }  # noqa: E501
    ok, msg = check_t_time_sendme(page)
    assert not ok
    assert "disabled" in msg


def test_t_time_on_press_passes():
    page = {
        "text": "Text tTime\n    Attributes\n        ID: 3\n        Send Component ID: on press\n"
    }  # noqa: E501
    ok, _ = check_t_time_sendme(page)
    assert ok


def test_t_time_other_enabled_modes_pass():
    for mode in ("on release", "on press and release"):
        page = {
            "text": (  # noqa: E501
                f"Text tTime\n    Attributes\n        ID: 3\n        Send Component ID: {mode}\n"
            )
        }
        ok, _ = check_t_time_sendme(page)
        assert ok, mode


def test_t_time_ignores_other_widgets_settings():
    """A page where an earlier widget reports taps must not shadow tTime."""
    page = {
        "text": (
            "Text tTime\n"
            "    Attributes\n"
            "        ID: 3\n"
            "        Send Component ID: on press\n"
            "\n"
            "Button bNext\n"
            "    Attributes\n"
            "        ID: 9\n"
            "        Send Component ID: on press and release\n"
        )
    }
    ok, _ = check_t_time_sendme(page)
    assert ok


def test_t_time_missing_widget_block_fails():
    ok, msg = check_t_time_sendme(None)
    assert not ok
    assert "missing" in msg


def test_tft_version_matches():
    page = {
        "text": (  # noqa: E501
            "Variable (string) tftVersion\n    Attributes\n        ID: 14\n        Text: 0.4.0\n"
        )
    }
    ok, msg = check_tft_version(page, "0.4.0")
    assert ok, msg


def test_tft_version_mismatch_fails():
    page = {
        "text": (  # noqa: E501
            "Variable (string) tftVersion\n    Attributes\n        ID: 14\n        Text: 0.3.3\n"
        )
    }
    ok, msg = check_tft_version(page, "0.4.0")
    assert not ok
    assert "0.3.3" in msg


def test_portrait_required_when_missing(tmp_path):
    # A fake HMI without the portrait siblings must fail the check.
    hmi = tmp_path / "nspanel_haui.HMI"
    hmi.write_text("fake")
    ok, msg = check_portrait(hmi, None)
    assert not ok
    assert "portrait" in msg


def test_portrait_present_passes(tmp_path):
    hmi = tmp_path / "nspanel_haui.HMI"
    hmi.write_text("landscape-hmi")
    (tmp_path / "nspanel_haui.tft").write_text("landscape-tft")
    (tmp_path / "nspanel_haui_portrait.HMI").write_text("portrait-hmi-rotated")
    (tmp_path / "nspanel_haui_portrait.tft").write_text("portrait-tft-rotated")
    ok, _ = check_portrait(hmi, None)
    assert ok


def test_portrait_stub_copy_fails(tmp_path):
    """A byte-identical copy (un-rotated) is caught, not just the missing case."""
    hmi = tmp_path / "nspanel_haui.HMI"
    hmi.write_text("landscape-hmi")
    (tmp_path / "nspanel_haui.tft").write_text("landscape-tft")
    (tmp_path / "nspanel_haui_portrait.HMI").write_text("landscape-hmi")
    (tmp_path / "nspanel_haui_portrait.tft").write_text("landscape-tft")
    ok, msg = check_portrait(hmi, None)
    assert not ok
    assert "byte-identical copy" in msg


def test_portrait_copy_with_only_text_edits_fails_geometry(tmp_path):
    """A copy that edits the version text but keeps the layout is not a rotation."""
    hmi = tmp_path / "nspanel_haui.HMI"
    (tmp_path / "nspanel_haui.tft").write_text("landscape-tft")
    (tmp_path / "nspanel_haui_portrait.tft").write_text("portrait-tft-b")
    # Same widget geometry on every page — portrait is a copy.
    landscape_hmi = (
        "Text a\n    Attributes\n        ID: 1\n        x coordinate: 0\n"
        "        y coordinate: 0\n        Width: 100\n        Height: 50\n"
    )
    portrait_hmi = landscape_hmi.replace("x coordinate: 0", "x coordinate: 0")
    hmi.write_text(landscape_hmi)
    (tmp_path / "nspanel_haui_portrait.HMI").write_text(portrait_hmi)

    # A fake dump tree whose pages carry the same geometry.
    dump = tmp_path / "dumps"
    dump.mkdir()
    (dump / "clock.txt").write_text(landscape_hmi)
    assert (dump / "clock.txt-portrait").parent == dump
    portrait_dump = dump.with_name("dumps-portrait")
    portrait_dump.mkdir(exist_ok=True)
    (portrait_dump / "clock.txt").write_text(portrait_hmi)

    ok, msg = check_portrait(hmi, dump)
    assert not ok
    assert "rotate" in msg


# portrait touch parity


def _page(*widgets: tuple[str, str]) -> dict:
    text = "Page clock\n    Attributes\n        Send Component ID  : disabled\n"
    for decl, state in widgets:
        text += f"{decl}\n    Attributes\n        ID: 3\n        Send Component ID: {state}\n"
    return {"text": text}


def test_sendme_parity_passes_when_every_widget_matches():
    widgets = (("Text tTime", "on press"), ("Dual-state Button btMode1", "disabled"))
    landscape = {"clock": _page(*widgets)}
    portrait = {"clock": _page(*widgets)}
    ok, msg = check_sendme_parity(landscape, portrait)
    assert ok
    assert "identical" in msg


def test_sendme_parity_names_every_widget_that_differs():
    landscape = {"clock": _page(("Text tTime", "on press"), ("Text tDate", "disabled"))}
    portrait = {"clock": _page(("Text tTime", "disabled"), ("Text tDate", "on release"))}
    ok, msg = check_sendme_parity(landscape, portrait)
    assert not ok
    assert "clock.tTime ('on press' vs 'disabled')" in msg
    assert "clock.tDate ('disabled' vs 'on release')" in msg


def test_sendme_parity_ignores_widgets_present_on_one_side_only():
    landscape = {"clock": _page(("Text tTime", "on press"), ("Text tExtra", "on press"))}
    portrait = {
        "clock": _page(("Text tTime", "on press")),
        "about": _page(("Text tIP", "disabled")),
    }
    ok, _ = check_sendme_parity(landscape, portrait)
    assert ok


def test_nextion2text_creates_missing_output_tree(tmp_path):
    """Nextion2Text must create a nested output dir even when parents are absent.

    Regression: the release gate failed in a fresh CI checkout because the default
    dump target lives under git-ignored ``ref_src/``, which does not exist, and the
    output folder was created without ``parents=True``.
    """
    root = Path(__file__).resolve().parent.parent
    out_dir = tmp_path / "ref_src" / "nextion-out-visual"
    assert not out_dir.exists()

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "nextion2text" / "Nextion2Text.py"),
            "-i",
            str(root / "nextion" / "nspanel_haui.HMI"),
            "-o",
            str(out_dir),
            "-d",
            "-s",
            "-p",
            "visual",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert (out_dir / "clock.txt").exists()
