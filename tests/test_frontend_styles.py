"""Regression tests for the frontend style guard."""

from __future__ import annotations

from pathlib import Path

from scripts.check_frontend_styles import (
    _duplicate_style_adoptions,
    _unused_color_tokens,
    check,
    check_css_sources,
)


def test_frontend_styles_follow_shared_rules() -> None:
    assert check() == []


def test_guard_reports_unused_color_aliases(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    tokens = frontend / "styles" / "tokens.js"
    consumer = frontend / "consumer.js"
    tokens.parent.mkdir(parents=True)
    tokens.write_text(
        "export const tokens = css`:host { --haui-unused-color: #123456; "
        "--haui-used-color: #abcdef; }`;",
        encoding="utf-8",
    )
    consumer.write_text(".consumer { color: var(--haui-used-color); }", encoding="utf-8")

    assert _unused_color_tokens(frontend, root) == [
        "frontend/styles/tokens.js: unused color token --haui-unused-color"
    ]


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

    assert any("use a --haui-text-* token" in error for error in errors)
    assert any("off-scale gap" in error for error in errors)
    assert any("off-scale margin" in error for error in errors)
    assert any("raw color function rgb" in error for error in errors)
    assert any("raw color #abc" in error for error in errors)


def test_guard_requires_the_whole_eyebrow_recipe(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "labels.js"
    css = (
        ".half-uppercase { font-size: var(--haui-text-caption); text-transform: uppercase; }"
        ".half-sized { font-size: var(--haui-text-eyebrow); }"
        ".half-weighted { font-size: var(--haui-text-eyebrow); font-weight: 600; }"
    )

    errors = check_css_sources([(style, css)], frontend, root)

    assert any(
        ".half-uppercase is uppercase, so it is the eyebrow step" in error for error in errors
    )
    assert any(
        ".half-sized uses the eyebrow size without its uppercase recipe" in error
        for error in errors
    )
    assert any(
        ".half-weighted uses the eyebrow size without its uppercase recipe" in error
        for error in errors
    )


def test_guard_accepts_the_eyebrow_recipe(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "labels.js"
    css = (
        ".eyebrow { font-size: var(--haui-text-eyebrow); font-weight: 600;"
        " letter-spacing: .05em; text-transform: uppercase; }"
    )

    assert check_css_sources([(style, css)], frontend, root) == []


def test_guard_keeps_weight_tracking_and_case_in_their_steps(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "labels.js"
    css = (
        ".heavy { font-size: var(--haui-text-label); font-weight: 600; }"
        ".tracked { font-size: var(--haui-text-headline); letter-spacing: -.01em; }"
        ".lowered { font-size: var(--haui-text-caption); text-transform: lowercase; }"
    )

    errors = check_css_sources([(style, css)], frontend, root)

    assert any("weight 600" in error for error in errors)
    assert any("tracks '-.01em'" in error for error in errors)
    assert any("no text-transform but uppercase" in error for error in errors)


def test_guard_keeps_a_badge_on_the_badge_step(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "badges.js"
    css = (
        ".haui-device-row-actions .haui-badge { font-size: var(--haui-text-eyebrow);"
        " font-weight: 600; letter-spacing: .05em; text-transform: uppercase; }"
        ".haui-item-row-chip { font-size: var(--haui-text-label); }"
        ".haui-panel-row-badge { font-size: var(--haui-text-caption); }"
    )

    errors = check_css_sources([(style, css)], frontend, root)

    assert any("is a badge, chip or count" in error for error in errors)
    assert any("haui-item-row-chip" in error for error in errors)
    # The caption is the step a pill used to borrow; a pill has its own one below it.
    assert any(
        "haui-panel-row-badge is a badge, chip or count, so its text is"
        " var(--haui-text-badge) at 400" in error
        for error in errors
    )


def test_guard_keeps_a_pill_out_of_emphasis(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "badges.js"
    css = (
        ".haui-badge { font-size: var(--haui-text-badge); font-weight: 500; }"
        ".haui-item-row-chip { font-weight: 500; }"
    )

    errors = check_css_sources([(style, css)], frontend, root)

    assert any(".haui-badge is a badge, chip or count, so it is 400" in error for error in errors)
    assert any(
        ".haui-item-row-chip is a badge, chip or count, so it is 400" in error for error in errors
    )


def test_guard_accepts_a_quiet_pill(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "badges.js"
    css = (
        ".haui-badge { font-size: var(--haui-text-badge); font-weight: 400; }"
        ".haui-badge-danger { color: var(--haui-bad-text); }"
    )

    assert check_css_sources([(style, css)], frontend, root) == []


def test_guard_rejects_font_shorthand_and_raw_line_heights(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "bad.js"
    css = ".bad { font: 11px/1.4 monospace; line-height: 1.35; }"

    errors = check_css_sources([(style, css)], frontend, root)

    assert any("not the font shorthand" in error for error in errors)
    assert any("line-height must use a --haui-line-height token" in error for error in errors)


def test_guard_allows_line_height_tokens_and_box_values(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "safe.js"
    css = (
        ".safe { font: inherit; line-height: var(--haui-line-height-copy); }"
        ".safe { line-height: 1; }.safe { line-height: 20px; }"
    )

    assert check_css_sources([(style, css)], frontend, root) == []


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
    css = (
        ".animated { transition: opacity 150ms; }"
        " @media (prefers-reduced-motion: reduce) { .animated { transition: none; } }"
    )

    assert check_css_sources([(style, css)], frontend, root) == []


def test_guard_requires_reduced_motion_per_selector(tmp_path: Path) -> None:
    root = tmp_path
    frontend = root / "frontend"
    style = frontend / "styles" / "motion.js"
    css = (
        ".covered { transition: opacity 150ms; } .missed { transition: opacity 150ms; }"
        " @media (prefers-reduced-motion: reduce) { .covered { transition: none; } }"
    )

    errors = check_css_sources([(style, css)], frontend, root)

    assert any("'.missed'" in error for error in errors)
    assert not any("'.covered'" in error for error in errors)


def test_guard_accepts_catch_all_in_the_same_composed_sheet(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    (frontend / "styles").mkdir(parents=True)
    (frontend / "styles.js").write_text(
        "import { motionStyles } from './styles/motion.js';\n"
        "import { resetStyles } from './styles/reset.js';\n"
        "export const sharedStyles = css`${resetStyles}${motionStyles}`;\n",
        encoding="utf-8",
    )
    sources = [
        (frontend / "styles" / "motion.js", ".animated { transition: opacity 150ms; }"),
        (
            frontend / "styles" / "reset.js",
            "@media (prefers-reduced-motion: reduce) { :host * { transition: none !important; } }",
        ),
        (frontend / "styles" / "alone.js", ".alone { transition: opacity 150ms; }"),
    ]

    errors = check_css_sources(sources, frontend, tmp_path)

    assert errors == [
        "frontend/styles/alone.js: motion on '.alone' must respect prefers-reduced-motion"
    ]
