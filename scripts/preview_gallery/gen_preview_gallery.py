#!/usr/bin/env python3
"""Render every panel card with sample data and show it in a browser gallery.

The hub renders a panel of every type and every system panel with the sample
world in ``sample_world.py`` — the same render the editor's cards use — for a
landscape (``eu``) and a portrait (``us``) device. ``gallery.html`` replays the
renders in the editor's own card element. Output goes to the git-ignored
``scripts/preview_gallery/out/``:

- ``renders.json``: ``{orientation: {card: {page, before, commands}}}``
- ``mdi/``: the Material Design Icons webfont the gallery draws icons with
- ``png/<orientation>/<card>.png``: with ``--png``, one screenshot per card at
  the display's resolution, taken with headless Chrome or Chromium driven by
  ``capture.mjs`` (Node 22+)

``--docs`` writes the same screenshots to ``docs/assets/screens/`` instead and
the screen overview ``docs/screens.html`` that shows them; the ``Screens``
workflow runs it and commits the result. Every render runs at a fixed time, so
the clock screens do not change from one run to the next.

Usage::

    python scripts/preview_gallery/gen_preview_gallery.py           # render only
    python scripts/preview_gallery/gen_preview_gallery.py --serve   # and open the gallery
    python scripts/preview_gallery/gen_preview_gallery.py --png     # and write PNGs
    python scripts/preview_gallery/gen_preview_gallery.py --docs    # and write the docs overview
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import functools
import html
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
import zoneinfo
from pathlib import Path
from typing import Any

import time_machine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
DOCS = ROOT / "docs"
SCREENS = DOCS / "assets" / "screens"
sys.path.insert(0, str(ROOT / "custom_components"))
sys.path.insert(0, str(ROOT / "scripts"))

import _ha_stubs  # noqa: E402,F401  (installs the Home Assistant import stubs)
import sample_world  # noqa: E402

DEVICES = {"landscape": "eu", "portrait": "us"}
# The sample Home Assistant runs in UTC; travelling to a UTC time also sets the
# process's local zone, so naive ``datetime.now()`` agrees on every machine.
FROZEN_NOW = datetime.datetime(2026, 6, 12, 10, 9, tzinfo=zoneinfo.ZoneInfo("UTC"))
MDI_ZIP = ROOT / "scripts" / "gen_fonts" / "MaterialDesign-Webfont.zip"
MDI_FILES = {
    "MaterialDesign-Webfont/css/materialdesignicons.css": "materialdesignicons.css",
    "MaterialDesign-Webfont/fonts/materialdesignicons-webfont.woff2": (
        "materialdesignicons-webfont.woff2"
    ),
}
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
MAC_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def render() -> dict[str, dict[str, Any]]:
    """Every card for each orientation, rendered by the hub."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        sample_world.install_runtime_stubs(loop)
        # time-machine leaves the monotonic clock alone, so the event loop's
        # and the debouncers' timers still run.
        with time_machine.travel(FROZEN_NOW, tick=False):
            return {
                orientation: sample_world.render_every_card(loop, display_model)
                for orientation, display_model in DEVICES.items()
            }
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)


def unpack_icons() -> None:
    """Outside Home Assistant the gallery draws `<ha-icon>` with the MDI webfont."""
    target = OUT / "mdi"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(MDI_ZIP) as archive:
        for member, name in MDI_FILES.items():
            (target / name).write_bytes(archive.read(member))


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def serve(port: int) -> http.server.ThreadingHTTPServer:
    """Serve the repository root on localhost: the gallery imports the editor's modules."""
    handler = functools.partial(_QuietHandler, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def find_chrome(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in CHROME_NAMES:
        path = shutil.which(name)
        if path:
            return path
    if MAC_CHROME.exists():
        return str(MAC_CHROME)
    raise SystemExit("--png and --docs need Chrome or Chromium; none found, pass --chrome PATH")


def write_pngs(renders: dict[str, dict[str, Any]], chrome: str, url: str, target: Path) -> None:
    """Screenshot each card alone at the display's resolution (``capture.mjs``).

    Args:
        renders: The hub's renders, ``{orientation: {card: render}}``.
        chrome: Chrome or Chromium executable.
        url: The gallery page served on localhost.
        target: Directory that receives ``<orientation>/<card>.png``.
    """
    node = shutil.which("node")
    if node is None:
        raise SystemExit("--png and --docs need Node 22+ (capture.mjs drives Chrome over DevTools)")
    jobs = []
    for orientation, cards in renders.items():
        layout_path = (
            ROOT
            / "custom_components/nspanel_haui/frontend/virtual"
            / f"layout_{orientation}.json"
        )
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        jobs.extend(
            {
                "url": f"{url}?orientation={orientation}&card={card}",
                "width": layout["visible_width"],
                "height": layout["height"],
                "path": str(target / orientation / f"{card}.png"),
            }
            for card in cards
        )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(jobs, handle)
    try:
        subprocess.run([node, str(HERE / "capture.mjs"), chrome, handle.name], check=True)
    finally:
        Path(handle.name).unlink()


SCREENS_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NSPanel HAUI Screens</title>
  <!-- Generated by scripts/preview_gallery/gen_preview_gallery.py --docs; do not edit. -->
  <style>
    body {{
      margin: 0;
      padding: 0 16px 32px;
      background: #1c1c1c;
      color: #e1e1e1;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    header {{ padding: 20px 0 8px; }}
    h1 {{ margin: 0 0 6px; font-size: 26px; font-weight: normal; }}
    h2 {{ margin: 32px 0 0; font-size: 22px; font-weight: normal; }}
    h3 {{ margin: 20px 0 10px; font-size: 16px; font-weight: normal; color: #9e9e9e; }}
    p {{ margin: 0; max-width: 72ch; color: #9e9e9e; font-size: 14px; line-height: 1.5; }}
    a {{ color: #64b5f6; }}
    nav {{ margin-top: 12px; display: flex; gap: 16px; font-size: 14px; }}
    .grid {{
      display: grid;
      gap: 20px;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    }}
    .grid.portrait {{ grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }}
    figure {{ margin: 0; }}
    img {{ display: block; width: 100%; height: auto; border-radius: 6px; background: #000; }}
    figcaption {{ margin-top: 6px; font-size: 14px; }}
    code {{ color: #9e9e9e; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>NSPanel HAUI Screens</h1>
    <p>Every panel, popup and system screen as the integration draws it with sample data,
      in the landscape (EU) and the portrait (US) layout. The images are regenerated
      automatically from the integration's own renders.</p>
    <nav>
      <a href="#landscape">Landscape</a>
      <a href="#portrait">Portrait</a>
      <a href="./">Documentation</a>
    </nav>
  </header>
{sections}
</body>
</html>
"""
GROUPS = {"panels": "Panels", "popups": "Popups", "system": "System"}


def card_group(card: str) -> str:
    if card.startswith("popup_"):
        return "popups"
    if card.startswith("sys_"):
        return "system"
    return "panels"


def write_screens_page(renders: dict[str, dict[str, Any]], path: Path) -> None:
    """Write the overview page that shows every card's PNG, grouped per orientation."""
    from nspanel_haui.haui.mapping.panel import (
        get_system_panel_entries,
        get_user_panel_type_descriptors,
    )

    labels = {d["type_key"]: d["label"] for d in get_user_panel_type_descriptors()}
    labels |= {entry["key"]: entry["label"] for entry in get_system_panel_entries()}
    sections = []
    for orientation, cards in renders.items():
        layout_path = (
            ROOT
            / "custom_components/nspanel_haui/frontend/virtual"
            / f"layout_{orientation}.json"
        )
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        width, height = layout["visible_width"], layout["height"]
        parts = [f'  <section id="{orientation}">', f"    <h2>{orientation.capitalize()}</h2>"]
        for group, title in GROUPS.items():
            parts.append(f"    <h3>{title}</h3>")
            parts.append(f'    <div class="grid {orientation}">')
            for card in cards:
                if card_group(card) != group:
                    continue
                label = html.escape(labels[card])
                parts.append(
                    f'      <figure id="{orientation}-{card}">'
                    f'<img src="assets/screens/{orientation}/{card}.png" alt="{label}"'
                    f' width="{width}" height="{height}" loading="lazy">'
                    f"<figcaption>{label} <code>{card}</code></figcaption></figure>"
                )
            parts.append("    </div>")
        parts.append("  </section>")
        sections.append("\n".join(parts))
    path.write_text(SCREENS_PAGE.format(sections="\n".join(sections)), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--serve", action="store_true", help="serve the gallery until Ctrl+C")
    parser.add_argument("--png", action="store_true", help="write one PNG per card")
    parser.add_argument(
        "--docs",
        action="store_true",
        help="write the PNGs to docs/assets/screens/ and the overview docs/screens.html",
    )
    parser.add_argument("--chrome", help="Chrome or Chromium executable for --png")
    parser.add_argument("--port", type=int, default=8765, help="gallery port (default 8765)")
    args = parser.parse_args(argv)

    renders = render()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "renders.json").write_text(json.dumps(renders, ensure_ascii=False), encoding="utf-8")
    unpack_icons()
    cards = sum(len(orientation) for orientation in renders.values())
    print(f"rendered {cards} cards -> {(OUT / 'renders.json').relative_to(ROOT)}")
    if not (args.serve or args.png or args.docs):
        print("--serve opens the gallery, --png writes one PNG per card, --docs the docs overview")
        return 0

    server = serve(args.port)
    url = f"http://127.0.0.1:{server.server_port}/scripts/preview_gallery/gallery.html"
    try:
        if args.png:
            write_pngs(renders, find_chrome(args.chrome), url, OUT / "png")
        if args.docs:
            # Start empty, so a card that no longer exists leaves no stale PNG.
            shutil.rmtree(SCREENS, ignore_errors=True)
            write_pngs(renders, find_chrome(args.chrome), url, SCREENS)
            write_screens_page(renders, DOCS / "screens.html")
            print(f"screens -> {SCREENS.relative_to(ROOT)}, docs/screens.html")
        if args.serve:
            print(f"gallery: {url}  (Ctrl+C to stop)")
            threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
