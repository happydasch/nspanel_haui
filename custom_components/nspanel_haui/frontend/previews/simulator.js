/**
 * NSPanel HAUI - shared Nextion simulator primitives.
 *
 * This module contains only generic display simulation and rendering helpers.
 * Panel-specific preview generation lives in `previewer.js`.
 */
import { html } from '../lit-import.js';
import { color, renderDisplay } from '../virtual/nextion-view.js';

export { loadIconMap, loadLayout, pictureUrlFor } from '../virtual/assets.js';

/** Static previews never advance timers. */
export function noopScheduler() {
  return { every: () => 0, cancel() {} };
}

/** Render a simulated display scaled to the card dimensions. */
export function renderSimulatorScreen(display, opts = {}) {
  if (!display || !display.page) {
    return html`<div class="haui-preview-sim haui-preview-sim-empty"></div>`;
  }
  const layout = display.layout;
  const width = layout.visible_width;
  const height = layout.height;
  const scale = opts.scale != null && opts.scale > 0 ? opts.scale : 1;
  // The card behind the scaled screen takes the page's own solid colour (the
  // device theme the hub painted), so no black edge shows around a themed page.
  const page = display.component(0)?.attrs;
  const theme = page?.sta === 1 && page.bco !== undefined ? `background:${color(page.bco)};` : '';
  return html`
    <div class="haui-preview-sim" style="width:${width * scale}px;aspect-ratio:${width}/${height};${theme}">
      <div class="haui-preview-sim-scaler" style="width:${width}px;height:${height}px;transform:scale(${scale});transform-origin:0 0;">
        ${renderDisplay(display, opts)}
      </div>
    </div>`;
}
