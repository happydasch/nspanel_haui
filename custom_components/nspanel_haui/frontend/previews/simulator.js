/**
 * NSPanel HAUI - shared Nextion simulator primitives.
 *
 * This module contains only generic display simulation and rendering helpers.
 * Panel-specific preview generation lives in `previewer.js`.
 */
import { html } from '../lit-import.js';
import { renderDisplay } from '../virtual/nextion-view.js';

export { loadIconMap, loadLayout, pictureUrlFor } from '../virtual/assets.js';

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
