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
| Typography | HA body font, which `styles.js` also gives native buttons and inputs; `--haui-mono` for node, key, IP and versions. The sizes are the editor's own 10/12/13/14/15/17/19/23px scale — one step below Home Assistant's type, since its body text is 15px to HA's 16px — each following HA's font size setting, and which one a text takes is its role in [Text sizes](#text-sizes); the host's base is the label step, so an element without a rule reads as body text and never as a heading. Weights are 400 for text, 500 for headings, names, values, labels and `strong` (`styles.js` replaces the browser's 700), and 600 only inside the eyebrow step, which is uppercase and tracks `.05em`. A pill takes 400: its size alone sets it apart. Line heights: `--haui-line-height-tight`, `--haui-line-height-copy` and `--haui-line-height` |
| Spacing | 4/8/12/16/20/24/28/32/40px through `--haui-space-1` to `--haui-space-8` and `--haui-space-10`, mapped onto HA's spacing variables where they exist |
| Radius | `--haui-radius-control` for 8px controls and thumbs, `--haui-card-radius` for 12px cards, `--haui-radius-pill` for pills, `--haui-radius-round` for dots |
| Elevation | `--haui-shadow-card` for cards and `--haui-shadow-overlay` for popovers and sidebars; the preview bezel and the Device screen's cards sit flat on their borders |
| Icon | Home Assistant `<ha-icon>` with MDI names, 18px by default and 14–16px compact, the HAUI brand icon for the mark. Never build SVG `<use>` sprites, which cannot cross shadow roots |
| Motion | 120–150ms hover and colour transitions; the scrim and sidebar entrance keep their 140/180ms timing; every animation is paired with `prefers-reduced-motion` |
| Focus | `--haui-focus-ring` and `--haui-focus-offset`: a visible 2px primary outline with a 2px offset, never suppressed |
| Hover | An item whose border turns `--primary-color` on hover also takes `color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color))`, 10% on small pill controls, never the border alone; a preview filled by a render and a text field keep their own background |
| Surface | `--haui-surface-band` is the band that opens and closes a card — its heading and its footer, the Device screen's workspace strip, a sidebar's title strip and the panel groups — a neutral step of the theme's text colour (6%) in the card ground, so a card reads title band, then content, then its rows and ends where it began, never one flat ground, without the theme's secondary surface, which is heavy enough in a light theme to read as a bar. Its sticky column heads keep a paler half of the same band. `--haui-surface-soft` is the plain soft ground for what holds content (tiles, chips, whole sub-cards) and for hover fills. A heading that opens a card takes the card's top corners with it, because three cards cannot clip their own contents |

## Breakpoints

`:host` in `styles.js` is the responsive root (`container-name: haui-editor`), because descendant container queries cannot leave a shadow tree.

| Width | What changes |
|---|---|
| 1120px | The inventory simplifies |
| 980px | The two-column screens collapse to one; the Device screen's four side actions pair up two by two |
| 870px | Toolbar spacing |
| 720px | Less row and card detail, stacked role controls |
| 600px | A sidebar becomes a full-screen page |
| 560px | No inventory health sentence, no footer glyphs and no TFT column; the Device side actions become one row of tiles |

Elements that follow their own width declare their own containers (`haui-workspace`, `haui-panel-info`, `haui-action-card`); anchored popovers float at every width, clamped to the viewport. The panel is registered with `handle_safe_area`, so the title header takes the top inset and the editor host the side and bottom insets.

There is no breakpoint above the widest one: the screens' content column stops at `--haui-content-max-width` (1440px) and centres, because a monitor wider than that gives a card more width than it can use, while the titlebar and the footer keep the full width.

## Text sizes

A text's size comes from what it is, not from how important it feels: pick its role below and use that token. The levels nest, so a heading stays one level above what it heads and a row's name never matches the card title.

| Level | Token | Size and weight | Used for |
|---|---|---|---|
| Title bar, page | `--haui-text-headline` | 19px / 500 | The title bar (one step above Home Assistant's own 20px title), the device screen's title, dialog titles |
| Sidebar | `--haui-text-title` | 17px / 500 | A sidebar's title in its header strip, above the sections it holds |
| Card, section | `--haui-text-body` | 15px / 500 | Card and section titles, a folding section heading, an Updates status headline, the title bar's context, a settings tile's name |
| Name of a row or card | `--haui-text-subtitle` | 14px / 500 | The name a row or card is listed by, and what opens it: a Fleet card's device name and its **No panels yet** placeholder, an inventory row's device, a panel row's title, an item row's name, the dashboard card's device name, a quick start page's title, an entry's title |
| Name, value | `--haui-text-label` | 13px / 500 | Tile and fact values, table cell values, group headings inside a card, form labels, the name of a choice inside a control (a dropdown entity, a theme option, a colour, an update's version) |
| Text | `--haui-text-label` | 13px / 400 | Running text, event copy, inputs and selects, button labels, a heading's description, menu items |
| Badge, chip, count, compact control | `--haui-text-caption` | 12px / 400 | Every pill: status and update badges, count bubbles, the repeat count, the item type chip — the size is their only distinction, never a heavier weight; and the small controls that sit in a card's band — a compact button, a disclosure summary, an overlay tool |
| Secondary | `--haui-text-caption` | 12px / 400 | Hints, meta lines, the label beside a value, a field's error, timestamps |
| Meta list | `--haui-text-caption` + `--haui-mono` | 12px / 400 | Addresses, versions, node and key names in a `dl` |
| Eyebrow | `--haui-text-eyebrow` | 10px / 600 uppercase, `.05em` | Column heads, a small label over a figure |
| Hero figure | `--haui-text-display` | 23px / 500 | Reserved for a single large figure; no screen uses it today |

- **No size between the steps.** A `font-size` is a `--haui-text-*` token, never a pixel value, an `em` or the `font` shorthand; `scripts/check_frontend_styles.py` refuses anything else, raw line heights included.
- **The base is the label step.** The tokens' `:host` sets it, so an element without a type rule reads as body text; a heading that should be bigger says so.
- **Weight separates text of one size.** A value is 13px at 500, the text around it 13px at 400, never 700. 600 belongs to the eyebrow step alone.
- **The eyebrow step is one recipe.** Uppercase, 600 and `.05em` go together in the same rule, or the text is not an eyebrow: nothing else is uppercase, tracked or 600, and a translated label is never transformed by case.
- **A pill is one look, and it is quiet.** A badge, chip or count never takes a size of its own — whatever its class is called (`*-badge`, `*-chip`, `*-count`), the pill carries the badge step and its container never resizes it — and it keeps the text weight (400): a label on a tinted ground is not emphasis. A bare count in a row stays secondary text.
- **Every heading element gets a size.** An `h1` to `h3` or a `summary` without a rule takes the browser's default, which for an `h2` is about 21px, off the scale.
- **Colour, not size, makes a text quieter.** Secondary text that keeps its role takes `--secondary-text-color` at the same size and weight; a state that reads quieter says so with colour only, never by dropping the weight below its role's.
- **Visually hidden text** (`.haui-sr-only`) has no visible size and stays out of the table.
- **The simulator is not editor type.** The display preview draws the Nextion fonts at the display's scale; its text never follows these levels.

## The style guard

Typography utility classes in `styles.js` (`.haui-text-caption`, `.haui-text-label`, `.haui-text-body`, `.haui-text-title`, `.haui-text-display`, `.haui-eyebrow`, `.haui-text-mono`) keep repeated type choices consistent. To check a screen, measure the computed `font-size` and `font-weight` of its visible text: each value should sit in its role's level, and no heading should share size and weight with the rows below it.

`scripts/check_frontend_styles.py` guards the scale (a `font-size` that is not a `--haui-text-*` token, the `font` shorthand and raw line heights included), the eyebrow recipe (uppercase without 600 and `.05em`, 600 or tracking outside it, any other `text-transform`), the badge step, raw colors, alias ownership, duplicate selectors, repeated style adoption and reduced-motion overrides; `tests/test_frontend_styles.py` covers valid styles and intentional violations. A fragment adopted on its own (`preview-styles.js`, `panel-editor-styles.js`) carries its own `prefers-reduced-motion` overrides, while one that `styles.js` composes into a sheet shares the universal rule of `styles/content.js`.
