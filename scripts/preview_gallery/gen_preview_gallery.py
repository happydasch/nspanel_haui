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

Usage::

    python scripts/preview_gallery/gen_preview_gallery.py           # render only
    python scripts/preview_gallery/gen_preview_gallery.py --serve   # and open the gallery
    python scripts/preview_gallery/gen_preview_gallery.py --png     # and write PNGs
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
sys.path.insert(0, str(ROOT / "custom_components"))
sys.path.insert(0, str(ROOT / "scripts"))

import _ha_stubs  # noqa: E402,F401  (installs the Home Assistant import stubs)
import sample_world  # noqa: E402

DEVICES = {"landscape": "eu", "portrait": "us"}
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
    raise SystemExit("--png needs Chrome or Chromium; none found, pass --chrome PATH")


def write_pngs(renders: dict[str, dict[str, Any]], chrome: str, url: str) -> None:
    """Screenshot each card alone at the display's resolution (``capture.mjs``)."""
    node = shutil.which("node")
    if node is None:
        raise SystemExit("--png needs Node 22+ (capture.mjs drives Chrome over DevTools)")
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
                "path": str(OUT / "png" / orientation / f"{card}.png"),
            }
            for card in cards
        )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(jobs, handle)
    try:
        subprocess.run([node, str(HERE / "capture.mjs"), chrome, handle.name], check=True)
    finally:
        Path(handle.name).unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--serve", action="store_true", help="serve the gallery until Ctrl+C")
    parser.add_argument("--png", action="store_true", help="write one PNG per card")
    parser.add_argument("--chrome", help="Chrome or Chromium executable for --png")
    parser.add_argument("--port", type=int, default=8765, help="gallery port (default 8765)")
    args = parser.parse_args(argv)

    renders = render()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "renders.json").write_text(json.dumps(renders, ensure_ascii=False), encoding="utf-8")
    unpack_icons()
    cards = sum(len(orientation) for orientation in renders.values())
    print(f"rendered {cards} cards -> {(OUT / 'renders.json').relative_to(ROOT)}")
    if not (args.serve or args.png):
        print("--serve opens the gallery, --png writes one PNG per card")
        return 0

    server = serve(args.port)
    url = f"http://127.0.0.1:{server.server_port}/scripts/preview_gallery/gallery.html"
    try:
        if args.png:
            write_pngs(renders, find_chrome(args.chrome), url)
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
