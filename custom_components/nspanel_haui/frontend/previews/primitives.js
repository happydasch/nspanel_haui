/**
 * NSPanel HAUI - Panel preview primitives.
 *
 * Reusable visual primitives for building panel preview renderers.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { itemDisplay, tileBgColor, tileIconColor } from './utils.js';

/**
 * A simple preview tile — coloured rounded rect with optional icon and label.
 *
 * @param {object} opts
 * @param {string} [opts.icon]  - MDI icon name
 * @param {string} [opts.label] - short text label
 * @param {string} [opts.color] - CSS background-color override
 * @param {string} [opts.iconSize] - mdc-icon-size in px (default 14)
 */
export function simTile(opts = {}) {
  return html`
    <div class="pg-preview-tile" style="${opts.color ? `background:${opts.color};` : ''}">
      ${opts.icon ? html`<ha-icon icon="${opts.icon}"></ha-icon>` : ''}
      ${opts.label ? html`<span class="pg-preview-tile-label">${opts.label}</span>` : ''}
    </div>
  `;
}

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

/**
 * A row of simulated buttons, each with a small icon.
 *
 * @param {Array<{icon:string, active?:boolean}>} buttons
 */
export function simButtonRow(buttons) {
  return html`
    <div class="pg-preview-btn-row">
      ${buttons.map(b => html`
        <div class="pg-preview-btn${b.active ? ' active' : ''}">
          <ha-icon icon="${b.icon}"></ha-icon>
        </div>
      `)}
    </div>
  `;
}

/**
 * A grid of item tiles (2 columns by default).
 *
 * @param {Array} items - panel item config objects
 * @param {object} [opts]
 * @param {number} [opts.cols] - number of columns (default 2)
 * @param {number} [opts.max]  - max tiles to show (default 6)
 */
export function simItemGrid(items, opts = {}, host) {
  const cols = opts.cols || 2;
  const max = opts.max || 6;
  const tiles = items.slice(0, max);
  return html`
    <div class="pg-preview-grid pg-preview-grid-${cols}cols">
      ${tiles.map(item => simItemTile(item, {}, host))}
      ${tiles.length < max
        ? Array.from({ length: max - tiles.length }, (_, i) =>
            simTile({ icon: 'mdi:plus', label: '' })
          )
        : ''}
    </div>
  `;
}

/**
 * Big time display (mock "12:34").
 */
export function simTimeDisplay() {
  return html`
    <div class="pg-preview-time-display">12:34</div>
    <div class="pg-preview-date-display">Mon, Jun 16</div>
  `;
}

/**
 * Big temperature display mock.
 */
export function simTempDisplay(temp) {
  const t2 = temp != null ? temp : '21';
  return html`
    <div class="pg-preview-temp-display">
      ${t2}<span class="pg-preview-temp-unit">&deg;C</span>
    </div>
  `;
}

/**
 * Forecast row: 5 mini day-icons with labels.
 */
export function simForecast() {
  const days = [
    { icon: 'mdi:weather-sunny', label: t('Mon') },
    { icon: 'mdi:weather-cloudy', label: t('Tue') },
    { icon: 'mdi:weather-rainy', label: t('Wed') },
    { icon: 'mdi:weather-partly-cloudy', label: t('Thu') },
    { icon: 'mdi:weather-sunny', label: t('Fri') },
  ];
  return html`
    <div class="pg-preview-forecast">
      ${days.map(d => html`
        <div class="pg-preview-forecast-day">
          <ha-icon icon="${d.icon}"></ha-icon>
          <span class="pg-preview-tile-label">${d.label}</span>
        </div>
      `)}
    </div>
  `;
}
