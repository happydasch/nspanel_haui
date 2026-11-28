# Image preview

`gen_image_preview.py` renders what `nspanel_haui.show_image` would paint,
without a panel, so a rectangle and a `quality` budget can be judged before an
action is called.

An image on the panel is not a picture: the hub reduces it to a bounded program
of Nextion `fill` rectangles (`custom_components/nspanel_haui/haui/utils/image_program.py`)
and the firmware streams that to the display. A pass is one `fill` in the
picture's own most common colour — its canvas, so a flat field and the margins of
a fitted image cost nothing — followed by the blocks that differ from it. The run
count is therefore the latency — at most `runs * COMMAND_SPACING_MS`, the pace the
hub plans for, while a draw is streamed at the display's own acknowledgement rate
— and the cell size the rasteriser settles on is the detail: it is never finer
than one display pixel, and for a large rectangle the run budget decides how close
to that it gets, because a pass is sent in slices and length is never what stops
it. This script runs the real rasteriser over a local file and replays the runs it
returns onto a canvas the size of the display, beside the ideal fit — both in the
colours the panel can show (RGB565), because a tile drawn from `fill` colours and
a reference drawn from the source's 8-bit ones would disagree about a correct
picture.

```bash
source .venv/bin/activate
python -m scripts.image_program.gen_image_preview nextion/images/logo_ha.png \
  --x 20 --y 60 --w 160 --h 160 --progressive
```

```
coarse   57 runs     830 chars  ~114 ms planned, 1 slice(s)
full    152 runs    2204 chars  ~304 ms planned, 1 slice(s)  drawn in 4 px blocks
rasterised in 16 ms here, rect at (20, 60) 160x160
wrote .dev/image-preview.png — tiles: ideal fit | coarse | full
```

| Option | Default | Meaning |
|--------|---------|---------|
| `image` | — | Path or `http(s)` URL of the image |
| `--x`, `--y` | `20`, `20` | Top left of the rectangle, in display pixels |
| `--w`, `--h` | `160`, `160` | Size of the rectangle, in display pixels |
| `--budget` | `300` | The service's `quality` option, 60 up to 12000 |
| `--progressive` | off | Render the coarse pass first, the way the action does |
| `--portrait` | off | 320x480 instead of 480x320 |
| `--scale` | `2` | Zoom of the saved tiles, so a 1 px cell is visible |
| `--out` | `.dev/image-preview.png` | Where to write the sheet (git-ignored) |

It prints how many slices the pass is sent in — the panel stages one at a time,
and a slice is `draw_wire.DRAW_SLICE_CHARS` (8 000) packed characters — and warns
when the final pass needs cells over `MAX_RECOMMENDED_CELL_PX`, the mosaic the
service logs about. Shrink the rectangle, or raise `--budget`.

The printed delays are estimates from the run count (`runs × COMMAND_SPACING_MS`,
the pace the hub plans for); what the panel really took is in the hub's log
(`Draw program finished: N runs, ok=True, M ms, R runs/s`) and in the panel's own
ESPHome log (`draw_runs: N runs, M rejected, ok=1, <ms>`).
