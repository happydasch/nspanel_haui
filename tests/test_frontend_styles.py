"""Regression tests for the frontend style guard."""

from __future__ import annotations

from pathlib import Path

from scripts.check_frontend_styles import _duplicate_style_adoptions, check, check_css_sources


def test_frontend_styles_follow_shared_rules() -> None:
    assert check() == []


def test_guard_reports_off_scale_values_and_raw_colors(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "bad.js"
    css = (
        ".bad { font-size: 15px; gap: 6px; }"
        ".bad { color: rgb(1 2 3); background: #abc; }"
        ".bad { margin: .5rem; }"
    )

    errors = check_css_sources([(style, css)], frontend, root)

    assert any("off-scale font-size" in error for error in errors)
    assert any("off-scale gap" in error for error in errors)
    assert any("off-scale margin" in error for error in errors)
    assert any("raw color function rgb" in error for error in errors)
    assert any("raw color #abc" in error for error in errors)


def test_guard_allows_theme_fallback_colors_and_pinned_fills(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "safe.js"
    css = ".safe { color: var(--secondary-text-color, #666); }.safe { background: #fff; }"

    assert check_css_sources([(style, css)], frontend, root) == []


def test_guard_rejects_haui_aliases_outside_tokens(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "bad.js"
    css = ".bad { --haui-local: 1; }"

    errors = check_css_sources([(style, css)], frontend, root)

    assert any("define --haui-* aliases in styles/tokens.js" in error for error in errors)


def test_guard_rejects_cross_fragment_selector_duplicates(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    first = frontend / "styles" / "one.js"
    second = frontend / "styles" / "two.js"

    errors = check_css_sources(
        [
            (first, ".repeated { display: block; }"),
            (second, ".repeated { display: flex; }"),
        ],
        frontend,
        root,
    )

    assert any("duplicate selector '.repeated'" in error for error in errors)


def test_guard_rejects_duplicate_style_adoption(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "component.js").write_text(
        "static get styles() { return [sharedStyles, sharedStyles]; }", encoding="utf-8"
    )

    errors = _duplicate_style_adoptions(frontend, tmp_path)

    assert any("sharedStyles is adopted more than once" in error for error in errors)


def test_guard_requires_reduced_motion_for_transitions(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "motion.js"

    errors = check_css_sources(
        [(style, ".animated { transition: opacity 150ms; }")], frontend, root
    )

    assert any("prefers-reduced-motion" in error for error in errors)


def test_guard_allows_motion_with_reduced_motion_override(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "motion.js"
    css = ".animated { transition: opacity 150ms; } @media (prefers-reduced-motion: reduce) { .animated { transition: none; } }"

    assert check_css_sources([(style, css)], frontend, root) == []
