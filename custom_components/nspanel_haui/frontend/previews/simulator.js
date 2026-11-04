/**
 * NSPanel HAUI - shared Nextion simulator primitives.
 *
 * This module contains only generic display simulation and rendering helpers.
 * Panel-specific preview generation lives in `previewer.js`.
 */
import { html } from '../lit-import.js';
import { renderDisplay } from '../virtual/nextion-view.js';

const MODULE_URL = import.meta.url;
const LAYOUT_CACHE = new Map();
let ICON_MAP_PROMISE = null;

function loadJson(url, loader) {
  if (loader) return Promise.resolve(loader(url));
  return fetch(url).then((response) => {
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  });
}

/** Memoised virtual-panel layout loader. */
export function loadLayout(orientation, loader) {
  let promise = LAYOUT_CACHE.get(orientation);
  if (!promise) {
    promise = loadJson(new URL(`../virtual/layout_${orientation}.json`, MODULE_URL), loader)
      .catch((error) => {
        LAYOUT_CACHE.delete(orientation);
        throw error;
      });
    LAYOUT_CACHE.set(orientation, promise);
  }
  return promise;
}

/** Memoised icon-map loader used by the virtual display renderer. */
export function loadIconMap(loader) {
  if (!ICON_MAP_PROMISE) {
    ICON_MAP_PROMISE = loadJson(new URL('../virtual/icon_map.json', MODULE_URL), loader)
      .catch((error) => {
        ICON_MAP_PROMISE = null;
        throw error;
      });
  }
  return ICON_MAP_PROMISE;
}

/** URL of a virtual-panel picture asset. */
export function pictureUrlFor(orientation, id) {
  return new URL(`../virtual/pictures/${orientation}/${id}.webp`, MODULE_URL).href;
}

/** Static previews never advance timers. */
export function noopScheduler() {
  return { every: () => 0, cancel() {} };
}

/** Render a simulated display scaled to the card dimensions. */
export function renderSimulatorScreen(display, opts = {}) {
  if (!display || !display.page) {
    return html`<div class="pg-sim pg-sim-empty"></div>`;
  }
  const layout = display.layout;
  const width = layout.visible_width;
  const height = layout.height;
  const scale = opts.scale != null && opts.scale > 0 ? opts.scale : 1;
  return html`
    <div class="pg-sim" style="aspect-ratio:${width}/${height};">
      <div class="pg-sim-scaler" style="width:${width}px;height:${height}px;transform:scale(${scale});transform-origin:0 0;">
        ${renderDisplay(display, opts)}
      </div>
    </div>`;
}
