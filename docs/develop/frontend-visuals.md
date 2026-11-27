---
title: Visual foundations
description: The editor's colour, type, spacing, radius, elevation, icon, motion and focus rules, its breakpoints and its text size scale
---

# Visual foundations

The editor draws with Home Assistant's live theme variables and their legacy aliases, never with copied colour ramps or `prefers-color-scheme` overrides. `styles/tokens.js` is the single home of the `--haui-*` aliases and the measured scale; `styles.js` composes the fragments of `styles/`, and an element-local style is reserved for layout specific to that element.

## Tokens

| Token group | Rule |
|---|---|
| Color | HA primary, text, secondary, disabled, surface, divider, error, warning and success tokens, plus a small `--haui-*` alias layer for the meanings HA lacks, each with a fallback. Tonal text uses `--haui-good-text`, `-warn-text`, `-bad-text` and `-accent-text`: the tone mixed with `--primary-text-color` as far as 4.5:1 allows (65% good, 50% warn, 70% bad, 55% accent). An icon in a tone is a graphic and keeps more of it, for 3:1: `--haui-good-icon` at 94%, `--haui-warn-icon` at 71%, `--haui-bad-icon` plain |
| Typography | HA body font, which `styles.js` also gives native buttons and inputs; `--haui-mono` for node, key, IP and versions. The sizes are the 11/13/14/16/18/20/24px scale, each following HA's font size setting, and which one a text takes is its role in [Text sizes](#text-sizes). Weights are 400 for text, 500 for headings, names, labels, values and `strong` (`styles.js` replaces the browser's 700), and 600 only for 11–13px uppercase labels and count bubbles, which track `.05em`. Line heights: `--haui-line-height-tight`, `--haui-line-height-copy` and `--haui-line-height` |
| Spacing | 4/8/12/16/20/24/28/32/40px through `--haui-space-1` to `--haui-space-8` and `--haui-space-10`, mapped onto HA's spacing variables where they exist |
| Radius | `--haui-radius-control` for 8px controls and thumbs, `--haui-card-radius` for 12px cards, `--haui-radius-pill` for pills, `--haui-radius-round` for dots |
| Elevation | `--haui-shadow-card` for cards and `--haui-shadow-overlay` for popovers and sidebars; the preview bezel and the Device screen's cards sit flat on their borders |
| Icon | Home Assistant `<ha-icon>` with MDI names, 18px by default and 14–16px compact, the HAUI brand icon for the mark. Never build SVG `<use>` sprites, which cannot cross shadow roots |
| Motion | 120–150ms hover and colour transitions; the scrim and sidebar entrance keep their 140/180ms timing; every animation is paired with `prefers-reduced-motion` |
| Focus | `--haui-focus-ring` and `--haui-focus-offset`: a visible 2px primary outline with a 2px offset, never suppressed |
| Hover | An item whose border turns `--primary-color` on hover also takes `color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color))`, 10% on small pill controls, never the border alone; a preview filled by a render and a text field keep their own background |
| Surface | `--haui-surface-soft` is the band above a body: a card's heading, the Device screen's workspace strip, a sidebar's title strip and the panel groups all take it, so a card reads title band, then content, then its rows — never one flat ground. A heading that opens a card takes the card's top corners with it, because three cards cannot clip their own contents |

## Breakpoints

`:host` in `styles.js` is the responsive root (`container-name: haui-editor`), because descendant container queries cannot leave a shadow tree.

| Width | What changes |
|---|---|
| 1120px | The inventory simplifies |
| 980px | The two-column screens collapse to one; the Device screen's four side actions pair up two by two |
| 870px | Toolbar spacing |
| 720px | Less row and card detail, stacked role controls |
| 600px | A sidebar becomes a full-screen page |
| 560px | Compact Fleet facts, no inventory heading or TFT column; the Device side actions become one row of tiles |

Elements that follow their own width declare their own containers (`haui-workspace`, `haui-panel-info`, `haui-action-card`); anchored popovers float at every width, clamped to the viewport. The panel is registered with `handle_safe_area`, so the title header takes the top inset and the editor host the side and bottom insets.

## Text sizes

A text's size comes from what it is, not from how important it feels: pick its role below and use that token. The levels nest, so a heading stays one level above what it heads and a row's name never matches the card title.

| Level | Token | Size and weight | Used for |
|---|---|---|---|
| Title bar, page | `--haui-text-headline` | 20px / 400, page title 500 | The title bar (Home Assistant's own is 20px regular), the device screen's title, dialog titles |
| Sidebar | `--haui-text-title` | 18px / 500 | A sidebar's title in its header strip, above the sections it holds |
| Card, section | `--haui-text-body` | 16px / 500 | Card and section titles, a folding section heading, an Updates status headline, the title bar's context |
| Name, value | `--haui-text-label` | 14px / 500 | Device, panel and item names, tile and fact values, group headings inside a card, form labels |
| Text | `--haui-text-label` | 14px / 400 | Running text, inputs and selects, button labels, a heading's description, menu items |
| Secondary | `--haui-text-caption` | 13px / 400 | Hints, meta lines, badges and chips, a field's error, timestamps, versions in tables |
| Eyebrow | `--haui-text-eyebrow` | 11px / 600 uppercase, `.05em` | Column heads, the small label over a figure, count bubbles |
| Hero figure | `--haui-text-display` | 24px / 500 | Reserved for a single large figure; no screen uses it today |

- **No size between the steps.** Use a token, never a pixel value or an `em`; `scripts/check_frontend_styles.py` refuses anything off the scale.
- **Weight separates text of one size.** A name or value is 14px at 500, the text around it 14px at 400, never 700.
- **Every heading element gets a size.** An `h1` to `h3` or a `summary` without a rule takes the browser's default, which for an `h2` is about 21px, off the scale.
- **Colour, not size, makes a text quieter.** Secondary text that keeps its role takes `--secondary-text-color` at the same size.
- **Visually hidden text** (`.haui-sr-only`) has no visible size and stays out of the table.
- **The simulator is not editor type.** The display preview draws the Nextion fonts at the display's scale; its text never follows these levels.

## The style guard

Typography utility classes in `styles.js` (`.haui-text-caption`, `.haui-text-label`, `.haui-text-body`, `.haui-text-title`, `.haui-text-display`, `.haui-eyebrow`, `.haui-text-mono`) keep repeated type choices consistent. To check a screen, measure the computed `font-size` and `font-weight` of its visible text: each value should sit in its role's level, and no heading should share size and weight with the rows below it.

`scripts/check_frontend_styles.py` guards the scale (the `font` shorthand and raw line heights included), raw colors, alias ownership, duplicate selectors, repeated style adoption and reduced-motion overrides; `tests/test_frontend_styles.py` covers valid styles and intentional violations. A fragment adopted on its own (`preview-styles.js`, `panel-editor-styles.js`) carries its own `prefers-reduced-motion` overrides, while one that `styles.js` composes into a sheet shares the universal rule of `styles/content.js`.
