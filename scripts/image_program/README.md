# Image preview

`gen_image_preview.py` renders what `nspanel_haui.show_image` would paint,
without a panel, so a rectangle and a `quality` budget can be judged before an
action is called.

An image on the panel is not a picture: the hub reduces it to a bounded program
of Nextion `fill` rectangles (`custom_components/nspanel_haui/haui/utils/image_program.py`)
and the firmware streams that through the pacer. The run count is therefore the
latency (`runs * COMMAND_SPACING_MS`), and the cell size the rasteriser settles
on is the detail — it is never finer than one display pixel, and for a large
rectangle the panel's 30 000-character program limit decides how close to that
it gets. This script runs the real rasteriser over a local file and draws every
`fill` onto a canvas the size of the display, beside the ideal fit.

```bash
source .venv/bin/activate
python -m scripts.image_program.gen_image_preview nextion/images/logo_ha.png \
  --x 20 --y 60 --w 160 --h 160 --progressive
```

```
coarse   59 runs    1298 chars  ~118 ms on the panel
full    265 runs    5830 chars  ~530 ms on the panel  drawn in 1 px blocks
rasterised in 31 ms here, rect at (20, 60) 160x160
wrote .dev/image-preview.png — tiles: ideal fit | coarse | full
```

| Option | Default | Meaning |
|--------|---------|---------|
| `image` | — | Path or `http(s)` URL of the image |
| `--x`, `--y` | `20`, `20` | Top left of the rectangle, in display pixels |
| `--w`, `--h` | `160`, `160` | Size of the rectangle, in display pixels |
| `--budget` | `300` | The service's `quality` option, 60 up to the 1153 a program can carry |
| `--progressive` | off | Render the coarse pass first, the way the action does |
| `--portrait` | off | 320x480 instead of 480x320 |
| `--background` | `4226` | Page background as RGB565 (`4226` is the default theme's) |
| `--scale` | `2` | Zoom of the saved tiles, so a 1 px cell is visible |
| `--out` | `.dev/image-preview.png` | Where to write the sheet (git-ignored) |

It prints a warning when the final pass needs cells over
`MAX_RECOMMENDED_CELL_PX` — the mosaic the service logs about — and when a
program would exceed the firmware's `draw_program_max`. Shrink the rectangle, or
pick a `--budget` the program length can hold.

The printed delays are estimates from the run count; the real figure is in the
panel's ESPHome log (`draw_runs: N runs, M rejected, ok=1, <ms>`).
