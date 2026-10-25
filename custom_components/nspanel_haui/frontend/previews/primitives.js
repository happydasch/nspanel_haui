/**
 * NSPanel HAUI - Panel preview primitives.
 *
 * Reusable visual primitives for building panel preview renderers.
 */
import { html } from '../lit-import.js';
import { itemDisplay, tileBgColor, tileIconColor } from './utils.js';

/**
 * A tile built from a panel item config (entity with optional icon/name/color).
 * @param {object} item - item config with entity_id, icon, name, back_color, text_color, etc.
 * @param {object} [opts]
 * @param {string} [opts.tileClass] - extra CSS class for the tile (e.g. 'pg-preview-grid-tile')
 * @param {object} [host] - optional Lit host element for HA state lookups
 */
export function simItemTile(item, opts = {}, host) {
  const { icon, name } = itemDisplay(item, host);
  const bg = tileBgColor(item);
  const ic = tileIconColor(item);
  const shortName = name.length > 7 ? name.slice(0, 6) + '\u2026' : name;
  const cls = 'pg-preview-tile' + (opts.tileClass ? ' ' + opts.tileClass : '');
  return html`
    <div class="${cls}" style="${bg ? `background:${bg};` : ''}">
      <div class="pg-preview-tile-icon-wrap">
        <ha-icon icon="${icon}" style="${ic ? `color:${ic};` : ''}"></ha-icon>
      </div>
      ${name ? html`<span class="pg-preview-tile-label" style="${ic ? `color:${ic};` : ''}">${shortName}</span>` : ''}
    </div>
  `;
}

/**
 * Horizontal slider track with filled portion.
 *
 * @param {object} opts
 * @param {number} [opts.value] - 0..100 how much is filled
 * @param {number} [opts.max]   - max value (default 100)
 */
export function simSlider(opts = {}) {
  const value = opts.value != null ? opts.value : 65;
  const max = opts.max || 100;
  const pct = Math.min(100, Math.round((value / max) * 100));
  return html`
    <div class="pg-preview-slider-track">
      <div class="pg-preview-slider-fill" style="width:${pct}%;"></div>
      <div class="pg-preview-slider-thumb" style="left:${pct}%;"></div>
    </div>
  `;
}

/**
 * Vertical slider track with filled portion from bottom.
 *
 * @param {object} opts
 * @param {number} [opts.value] - 0..100
 */
export function simSliderVertical(opts = {}) {
  const value = opts.value != null ? opts.value : 65;
  const pct = Math.min(100, Math.max(0, value));
  return html`
    <div class="pg-preview-slider-vertical">
      <div class="pg-preview-slider-fill" style="height:${pct}%;"></div>
    </div>
  `;
}
