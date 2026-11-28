/**
 * NSPanel HAUI - a draw program's `fill` runs, painted into a canvas.
 *
 * A picture is thousands of adjacent rectangles (`haui/utils/image_program.py`),
 * and a camera stream repaints the whole picture several times a second. As one
 * positioned element per run that is all DOM and all paint: a 6 000-run picture
 * held 6 000 nodes, and the browser spent 71 % of its time in Paint / display-list
 * building on a preview that was drawing a stream - the JS side was 5.6 %.
 *
 * So one run of fills becomes one `<canvas>`, filled with `fillRect` at the
 * display's own pixel grid and scaled by the same transform as the widgets: one
 * node, one texture, and no hairline between adjacent runs because a canvas has
 * no subpixel edges to show (which is what the SVG layer was working around).
 *
 * The canvas is kept across renders and only the fills a render *added* are
 * painted into it. A picture arrives as a program, and the frames after it are
 * deltas appended to the same run (`nextion-display.js`), so repainting the whole
 * run would repaint the whole picture for a handful of changed rectangles - the
 * canvas is the display's own state and a `fill` only ever covers what was there
 * before, so appending is exactly what the panel does.
 *
 * A run that was rewritten rather than extended - a widget repainted over the
 * picture splits its fills, a new program replaced them - is painted again from
 * scratch, because the fills before the rewrite are no longer what the display
 * shows.
 */
import { html } from '../lit-import.js';
import { rgb565ToHex } from '../color-utils.js';

/**
 * Runs below this are drawn as plain boxes: a canvas per two rectangles costs
 * more (one element each, one texture each) than the boxes it would paint. Only
 * a program that interleaves circles or pictures with its fills produces runs
 * this small.
 */
const MIN_CANVAS_FILLS = 8;

/**
 * The layers of one display, in the order a render paints them.
 *
 * @type {WeakMap<object, Array<{canvas: HTMLCanvasElement, painted: number, revision: number, left: number, top: number, width: number, height: number}>>}
 */
const layersByDisplay = new WeakMap();

/**
 * Paint a run of fills into a 2D context, in its own coordinates.
 *
 * Public because it is the whole rasterisation, and a test can hand it a context
 * of its own instead of a browser's.
 *
 * @param {CanvasRenderingContext2D} context
 * @param {Array<{x: number, y: number, w: number, h: number, color: number}>} fills
 * @param {number} left - display x of the context's origin
 * @param {number} top - display y of the context's origin
 */
export function paintFills(context, fills, left, top) {
  for (const fill of fills) {
    context.fillStyle = rgb565ToHex(fill.color);
    context.fillRect(fill.x - left, fill.y - top, fill.w, fill.h);
  }
}

/**
 * The box a run covers, or ``null`` when it has no area.
 *
 * @param {Array<{x: number, y: number, w: number, h: number}>} fills
 * @returns {{left: number, top: number, width: number, height: number}|null}
 */
function boundingBox(fills) {
  let left = Infinity;
  let top = Infinity;
  let right = -Infinity;
  let bottom = -Infinity;
  for (const fill of fills) {
    left = Math.min(left, fill.x);
    top = Math.min(top, fill.y);
    right = Math.max(right, fill.x + fill.w);
    bottom = Math.max(bottom, fill.y + fill.h);
  }
  if (!(right > left && bottom > top)) return null;
  return { left, top, width: right - left, height: bottom - top };
}

/**
 * Whether the canvas still holds the start of ``fills``: paint only what is new.
 *
 * The display keeps a run's fills in the order they were painted and only appends
 * to it while a stream draws (`nextion-display.js`), so the fills a layer painted
 * come back as the first entries of the run and the rest is new. A log that was
 * rewritten - a widget repainted over the picture, a page change - is signalled by
 * the display (`fillsRevision`), and then the canvas starts over because the fills
 * it holds are no longer what the display shows.
 *
 * @param {{painted: number, revision: number}} entry - the layer
 * @param {Array<object>} fills - the run as this render has it
 * @param {number} revision - the display's count of fill-log rewrites
 * @returns {boolean}
 */
function continues(entry, fills, revision) {
  return entry.revision === revision && entry.painted <= fills.length;
}

/**
 * The layer of one run of fills: its canvas, painted up to and including this render.
 *
 * @param {Array<object>} layers - the display's layers, one per run in paint order
 * @param {number} index - the run's place among the render's canvas runs
 * @param {Array<{x: number, y: number, w: number, h: number, color: number}>} fills
 * @param {number} revision - the display's count of fill-log rewrites
 * @returns {HTMLCanvasElement|null} the canvas, or null when the fills have no area
 */
function layer(layers, index, fills, revision) {
  const box = boundingBox(fills);
  if (!box) return null;
  let entry = layers[index];
  if (!entry) {
    entry = {
      canvas: document.createElement('canvas'),
      painted: 0,
      revision,
      left: NaN,
      top: NaN,
      width: 0,
      height: 0,
    };
    entry.canvas.className = 'vp-drawing-layer';
    layers[index] = entry;
  }
  const resized = entry.left !== box.left || entry.top !== box.top
    || entry.width !== box.width || entry.height !== box.height;
  if (resized) {
    Object.assign(entry, box);
    // A canvas' backing store is in display pixels; the scaler's transform makes
    // it fill its box. Setting a size clears the canvas, so it is painted again.
    entry.canvas.width = box.width;
    entry.canvas.height = box.height;
    entry.canvas.style.cssText = `left:${box.left}px;top:${box.top}px;`
      + `width:${box.width}px;height:${box.height}px;`;
    entry.painted = 0;
    entry.revision = revision;
  }
  const context = entry.canvas.getContext('2d');
  if (context) {
    if (!continues(entry, fills, revision)) {
      context.clearRect(0, 0, box.width, box.height);
      entry.painted = 0;
    }
    // Only what the render added: a stream's frame is a handful of rectangles on
    // a picture of thousands, and the canvas already holds the rest of it.
    paintFills(context, fills.slice(entry.painted), box.left, box.top);
    entry.painted = fills.length;
    entry.revision = revision;
  } else if (!entry.warned) {
    // A DOM without a 2D canvas still renders the page; say why the picture is
    // missing instead of leaving the area blank for no stated reason.
    entry.warned = true;
    console.warn(`[virtual panel] no 2D canvas for a ${fills.length}-run picture`);
  }
  return entry.canvas;
}

/**
 * The canvases of a render's fill runs, in paint order.
 *
 * The layers are kept per display in render order, so a stream's frames paint
 * into the canvas the previous frame used instead of a new one each time.
 *
 * @param {object} display - the display the drawings belong to: its layers live
 *   as long as it does, so a stream does not allocate a canvas per frame.
 * @param {Array<Array<{x: number, y: number, w: number, h: number, color: number}>>} runs
 * @returns {Array<HTMLCanvasElement|null>} one entry per run, null when it has no area
 */
export function fillLayers(display, runs) {
  let layers = layersByDisplay.get(display);
  if (!layers) {
    layers = [];
    layersByDisplay.set(display, layers);
  }
  const revision = display.fillsRevision;
  const canvases = runs.map((fills, index) => layer(layers, index, fills, revision));
  // A render with fewer runs no longer shows the layers it had; keep only those
  // so a picture that went away does not hold its canvas.
  layers.length = runs.length;
  return canvases;
}

/**
 * A run of fills too small to be worth a canvas: they go as boxes.
 *
 * @param {Array<{x: number, y: number, w: number, h: number, color: number}>} fills
 * @returns {Array<*>} one template per fill, in paint order
 */
export function fillBoxes(fills) {
  return fills.map(fill => html`<div class="vp-widget" style="left:${fill.x}px;top:${fill.y}px;width:${fill.w}px;height:${fill.h}px;background:${rgb565ToHex(fill.color)};"></div>`);
}

/**
 * Whether a run should become a canvas rather than boxes.
 *
 * @param {number} count - fills in the run
 * @returns {boolean}
 */
export function wantsCanvas(count) {
  return count >= MIN_CANVAS_FILLS;
}
