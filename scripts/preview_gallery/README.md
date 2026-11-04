# Preview Gallery

Render every panel card with sample data and browse the results in a browser.

The hub renders a panel of every type and every system panel with the sample
world in `sample_world.py` — the same render the editor's cards use — for a
landscape (`eu`) and a portrait (`us`) device. `gallery.html` replays those
renders in the editor's own `<nspanel-simulator-frame>`, so what you see is the
hub's output, not a separate renderer.

## Usage

Run from the repository root:

```bash
python scripts/preview_gallery/gen_preview_gallery.py           # render only
python scripts/preview_gallery/gen_preview_gallery.py --serve   # render and open the gallery
python scripts/preview_gallery/gen_preview_gallery.py --png     # render and write one PNG per card
python scripts/preview_gallery/gen_preview_gallery.py --docs    # render and write the docs screen overview
```

- `--serve` starts a local server (default port `8765`) and prints the gallery
  URL. Stop it with Ctrl+C.
- `--png` screenshots each card alone at the display's resolution. It needs
  Node 22+ and Chrome or Chromium; pass `--chrome PATH` if the browser is not
  found automatically.
- `--docs` writes the same PNGs to `docs/assets/screens/<orientation>/<card>.png`
  and the overview page `docs/screens.html`. The `Screens` workflow
  (`.github/workflows/screens.yml`) runs it after each dev firmware build and
  commits the result to `dev` when a screen changed; don't edit those files by
  hand.
- `--port N` changes the gallery port.

Every render runs at a fixed time (`time-machine`, in `requirements-dev.txt`),
so the clock screens, and with them the committed PNGs, stay the same from one
run to the next.

## Output

Everything is written to the git-ignored `scripts/preview_gallery/out/`:

| Path | Contents |
|------|----------|
| `renders.json` | `{orientation: {card: {page, before, commands}}}` — the hub's renders |
| `mdi/` | Material Design Icons webfont the gallery draws icons with |
| `png/<orientation>/<card>.png` | One screenshot per card, with `--png` |

## Files

| File | Purpose |
|------|---------|
| `gen_preview_gallery.py` | Renders the cards, writes `renders.json`, serves the gallery, drives the PNG capture |
| `sample_world.py` | Sample Home Assistant entities and the render loop; shared with `tests/test_card_renders.py` |
| `gallery.html` / `gallery.js` | The browser gallery; `?orientation=landscape&card=grid` shows one card alone |
| `capture.mjs` | Headless Chrome capture over the DevTools protocol (Node 22+, no npm packages) |

## Related

- `tests/test_card_renders.py` replays the same renders in the browser's
  simulator and fails when a card cannot draw what the hub sent.
- `scripts/check_preview_coverage.py` verifies every exposed panel resolves to a
  physical page present in both generated layouts.
