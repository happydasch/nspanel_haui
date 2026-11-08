#!/usr/bin/env python3
"""Export the README images to ``docs/assets/readme/``.

Each image is an HTML page in ``src/`` captured with headless Chrome at twice
its CSS size: the hero and the two step strips (editor, quick start). The hero's
two screens are the hub's own renders of the sample panels in ``SCREENS``, taken
through the card gallery like ``gen_preview_gallery.py --png``, so they show what
the display really draws.

The README links the images by absolute ``raw.githubusercontent.com`` URLs: the
Home Assistant Marketplace shows the README, and mermaid diagrams are not drawn
there.

Usage::

    python -m scripts.readme_images.gen_readme_images
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

import time_machine

from scripts.preview_gallery import gen_preview_gallery as gallery
from scripts.preview_gallery import sample_world

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = ROOT / "docs" / "assets" / "readme"

# name -> CSS size of the page; exported at 2x
IMAGES = {"hero": (1000, 380), "editor": (1000, 236), "quick-start": (1000, 236)}
WHITE = "#ffffff"


def _tile(entity: str, name: str, icon: str, color: str) -> dict[str, str]:
    return {
        "item": entity,
        "name": name,
        "icon": icon,
        "color": WHITE,
        "back_color": color,
        "text_color": WHITE,
    }


# The hero's screens, one panel per orientation: src/hero.html shows
# screens/<orientation>/<key>.png
SCREENS: dict[str, dict[str, Any]] = {
    "landscape": {
        "type": "grid",
        "key": "grid",
        "title": "Living Room",
        "items": [
            _tile("light.lamp", "Light", "mdi:lightbulb", "#e6cf1c"),
            _tile("cover.blind", "Cover", "mdi:blinds-horizontal", "#f2801d"),
            _tile("media_player.tv", "Music", "mdi:music", "#e58fce"),
            _tile("vacuum.robot", "Vacuum", "mdi:robot-vacuum", "#63c31e"),
            _tile("scene.movie", "Scenes", "mdi:play-box-outline", "#2f9be0"),
            _tile("climate.living", "Climate", "mdi:snowflake", "#6b63e6"),
        ],
    },
    "portrait": {
        "type": "clock",
        "key": "clock",
        "title": "Clock",
        "background": "autumn",
        "item": {"item": "weather.home"},
        "items": [],
    },
}


def _render_panel(
    loop: asyncio.AbstractEventLoop, display_model: str, panel: dict[str, Any]
) -> dict[str, Any]:
    import custom_components.nspanel_haui as nspanel_haui
    from custom_components.nspanel_haui.virtual_panel import VirtualPanelHost

    # Both panels: with a single one the header has no previous/next arrows
    store = {
        "devices": {
            "kitchen": {
                "config": {"home_panel": panel["key"], "display_model": display_model},
                "panels": list(SCREENS.values()),
            }
        }
    }
    config = nspanel_haui._build_config_dict(
        {"name": "Hub", "devices": [{"name": "kitchen"}]}, store, device_name="kitchen"
    )
    host = VirtualPanelHost(sample_world.SampleHass(loop), "kitchen", config)

    def run(coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)

    run(host.async_start())
    try:
        return run(host.async_render(panel))
    finally:
        run(host.async_stop())


def render_screens() -> dict[str, dict[str, Any]]:
    """The hub's renders of ``SCREENS``, ``{orientation: {key: render}}``."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        sample_world.install_runtime_stubs(loop)
        with time_machine.travel(gallery.FROZEN_NOW, tick=False):
            return {
                orientation: {
                    panel["key"]: _render_panel(loop, gallery.DEVICES[orientation], panel)
                }
                for orientation, panel in SCREENS.items()
            }
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)


def serve_gallery(renders: dict[str, dict[str, Any]]) -> http.server.ThreadingHTTPServer:
    """Serve the repository like the gallery, with ``renders`` as its renders.json."""
    payload = json.dumps(renders).encode()

    class Handler(gallery._QuietHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] != "/scripts/preview_gallery/out/renders.json":
                super().do_GET()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the README images.")
    parser.add_argument("--chrome", help="Chrome or Chromium executable")
    args = parser.parse_args()
    chrome = gallery.find_chrome(args.chrome)
    # The gallery page draws the screens' icons with this webfont
    gallery.unpack_icons()
    renders = render_screens()

    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp) / "build"
        shutil.copytree(HERE / "src", build)
        fonts = build / "fonts"
        fonts.mkdir()
        for weight in ("Light", "Regular", "Bold"):
            shutil.copy(ROOT / "scripts" / "font_tools" / "Roboto" / f"Roboto-{weight}.ttf", fonts)
        shutil.copy(gallery.OUT / "mdi" / "materialdesignicons-webfont.woff2", fonts)

        server = serve_gallery(renders)
        try:
            url = f"http://127.0.0.1:{server.server_port}/scripts/preview_gallery/gallery.html"
            gallery.write_pngs(renders, chrome, url, build / "screens")
        finally:
            server.shutdown()

        TARGET.mkdir(parents=True, exist_ok=True)
        for name, (width, height) in IMAGES.items():
            path = TARGET / f"{name}.png"
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    f"--user-data-dir={Path(tmp) / 'profile'}",
                    "--force-device-scale-factor=2",
                    "--default-background-color=00000000",
                    "--virtual-time-budget=3000",
                    f"--window-size={width},{height}",
                    f"--screenshot={path}",
                    (build / f"{name}.html").as_uri(),
                ],
                check=True,
                capture_output=True,
            )
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
