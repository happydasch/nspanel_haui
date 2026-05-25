/**
 * NSPanel HAUI - Editor - Panel preview renderers.
 *
 * Registry for custom panel previews shown in the grid view card body.
 * Each panel type can register a renderer; if none is registered the
 * default fallback (icon only) is used.
 *
 * This module provides reusable visual primitives (simScreen, simHeader,
 * simTile, simSlider, etc.) and per-panel-type renderers that compose them
 * to give a meaningful visual hint of the panel layout and config.
 */
import { html } from './lit-import.js';

/* ── Registry ──────────────────────────────────────────────────── */

/** @type {Map<string, Function>} */
const panelPreviewRenderers = new Map();

/**
 * Register a custom preview renderer for a panel type.
 * The renderer returns only the visual content (what goes inside
 * `.pg-card-preview-content`). Description text is rendered automatically
 * by the card wrapper for ALL panel types.
 *
 * @param {string} typeKey  - the panel type key (e.g. 'qr', 'climate')
 * @param {Function} renderFn
 *   (host, panel, panelIndex, panelTypeDescriptor) => { content, contentClass?, containerClass? }
 */
export function registerPanelPreview(typeKey, renderFn) {
  panelPreviewRenderers.set(typeKey, renderFn);
}

/**
 * Single entry-point: look up the registered renderer for `panel.type`
 * and call it with consistent args. Falls back to the default icon renderer.
 *
 * @param {object} host      - the Lit element instance
 * @param {object} panel     - the panel config object
 * @param {number} panelIndex - index of the panel in the full panels array
 * @param {object|null} panelType - matched panel type descriptor from host._panelTypes
 * @returns {{ content, contentClass?, containerClass? }}
 */
export function renderPanelPreview(host, panel, panelIndex, panelType) {
  const renderFn = panelPreviewRenderers.get(panel.type) || renderDefaultPreview;
  const result = renderFn(host, panel, panelIndex, panelType);
  const colors = getDeviceColors(host);
  result.deviceStyle = deviceThemeCss(colors);
  result.deviceColors = colors;
  return result;
}

/* ── Utilities ─────────────────────────────────────────────────── */

/**
 * Pick a background class for the screen based on the panel's `background` option.
 * Returns a CSS class string (e.g. 'pg-preview-bg-spring') or empty string.
 */
function backgroundClass(panel) {
  const bg = panel && panel.background;
  if (!bg || bg === 'default') return '';
  return 'pg-preview-bg-' + bg;
}

/**
 * Extract the "items" array from a panel config, defaulting to empty array.
 * Both grid and row panels store items under the `items` key.
 */
function getItems(panel) {
  return (panel && panel.items) || [];
}

/**
 * Get hue from a color_seed number for consistent tile coloring.
 * Simple deterministic hash.
 */
function seedToHue(seed) {
  if (seed == null || seed === 0) return null;
  return ((seed * 137.508) % 360 + 360) % 360;
}

/**
 * Convert a color value to a CSS color string, using the same approach as the
 * panel edit dialog's color swatch (see form-fields.js parseRgbListToHex).
 * Accepts: number (RGB565), [r,g,b] array, "[r,g,b]" string, "#rrggbb" / "rrggbb",
 * numeric string like "63488", or CSS color names.
 *
 * Returns a CSS color string (rgb() or hex), or null if unparseable.
 */
function colorToCss(val) {
  if (val == null || val === '') return null;
  // Number → RGB565
  if (typeof val === 'number') {
    if (val <= 0) return null;
    const r = Math.round(((val & 0xF800) >> 11) * 255 / 31);
    const g = Math.round(((val & 0x07E0) >> 5) * 255 / 63);
    const b = Math.round((val & 0x001F) * 255 / 31);
    return `rgb(${r},${g},${b})`;
  }
  // [r, g, b] array
  if (Array.isArray(val) && val.length === 3) {
    const r = Math.min(255, Math.max(0, parseInt(val[0], 10)));
    const g = Math.min(255, Math.max(0, parseInt(val[1], 10)));
    const b = Math.min(255, Math.max(0, parseInt(val[2], 10)));
    if ([r, g, b].every(Number.isFinite)) {
      return `rgb(${r},${g},${b})`;
    }
    return null;
  }
  const s = String(val).trim();
  // Template string — skip, no preview possible
  if (s.includes('{{')) return null;
  // Already a CSS color like "#rrggbb", "rgb(...)", "hsl(...)"
  if (/^(#|rgb|hsl)/i.test(s)) return s;
  // Hex without # prefix (rrggbb)
  if (/^[0-9a-fA-F]{6}$/.test(s)) return '#' + s;
  // "[r,g,b]" format
  const rgbMatch = s.match(/^\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]\s*$/);
  if (rgbMatch) {
    return `rgb(${rgbMatch[1]},${rgbMatch[2]},${rgbMatch[3]})`;
  }
  // RGB565 integer string (e.g., "12345") — convert to CSS
  if (/^\d{1,5}$/.test(s)) {
    const n = parseInt(s, 10);
    if (n > 0) {
      const r = Math.round(((n & 0xF800) >> 11) * 255 / 31);
      const g = Math.round(((n & 0x07E0) >> 5) * 255 / 63);
      const b = Math.round((n & 0x001F) * 255 / 31);
      return `rgb(${r},${g},${b})`;
    }
  }
  return null;
}

/**
 * Default device color palette (RGB565 ints), matching `haui/mapping/color.py`.
 * Only the keys that affect device-level theming are included — weather, entity,
 * alarm, and climate sub-colors are panel-type specific and not part of the
 * user-visible `color_overrides` schema.
 */
const DEFAULT_COLORS = {
  background: 6339,
  text: 55002,
  text_inactive: 29582,
  header_background: 6339,
  header_text: 65535,
  component_text: 65535,
  component_active: 19773,
  component_accent: 62694,
  component_background: 8452,
};

/**
 * Build a merged device colour palette from defaults + persisted overrides.
 * Every key in the default palette is guaranteed a value.
 *
 * @param {object} host - the Lit element instance (carries _deviceConfig)
 * @returns {object.<string, string>} colour-name -> CSS colour string
 */
function getDeviceColors(host) {
  const overrides = (host && host._deviceConfig && host._deviceConfig.color_overrides) || {};
  const merged = {};
  for (const [k, v] of Object.entries(DEFAULT_COLORS)) {
    merged[k] = colorToCss(overrides[k] !== undefined ? overrides[k] : v);
  }
  return merged;
}

/**
 * Build an inline style string that sets the device-theme CSS custom properties.
 * Applying this on the preview container lets all `var(--primary-text-color, ...)`
 * references resolve to the device's colour scheme automatically.
 *
 * @param {object} deviceColors - output of getDeviceColors()
 * @returns {string} computed inline style
 */
function deviceThemeCss(deviceColors) {
  return [
    '--primary-text-color:' + (deviceColors.text || '#ddd'),
    '--secondary-text-color:' + (deviceColors.text_inactive || '#888'),
    '--primary-color:' + (deviceColors.component_active || '#4fc3f7'),
  ].join(';');
}

/**
 * Build a CSS background-color string for a tile given item config fields.
 * Falls back to null (no custom background).
 */
function tileBgColor(item) {
  if (!item) return null;
  const bc = item.back_color;
  if (bc != null && bc !== '' && bc !== '0') {
    const css = colorToCss(bc);
    if (css) return css;
  }
  const hue = seedToHue(item.color_seed);
  if (hue !== null) return `hsl(${hue}, 55%, 32%)`;
  return null;
}

/**
 * Build a CSS color string for icon/text in a tile given item config fields.
 */
function tileIconColor(item) {
  if (!item) return null;
  // Check grid-specific text_color override first, then fall back to the
  // standard HAUIItem color override (the same field used by get_color()).
  const tc = item.text_color || item.color;
  if (tc != null && tc !== '' && tc !== '0') {
    const css = colorToCss(tc);
    if (css) return css;
  }
  const hue = seedToHue(item.color_seed);
  if (hue !== null) return `hsl(${hue}, 65%, 65%)`;
  return null;
}

/**
 * Extract the entity ID from an item config.
 * Items can be:
 *   - A plain string (the entity_id itself)
 *   - An object with { item: "...", icon, name, ... }
 *   - An object with { entity_id: "...", icon, name, ... }
 * Returns the entity_id string or empty string.
 */
function itemEntityId(item) {
  if (!item) return '';
  if (typeof item === 'string') return item;
  if (typeof item.item === 'string') return item.item;
  if (typeof item.entity_id === 'string') return item.entity_id;
  return '';
}

/**
 * Normalise an item into { icon, name } for display in a tile.
 */
function itemDisplay(item) {
  if (!item) return { icon: 'mdi:help-circle-outline', name: '?' };
  const eid = itemEntityId(item);
  const icon = (item.icon && typeof item.icon === 'string' && item.icon !== '')
    ? item.icon : 'mdi:help-circle-outline';
  const name = (item.name && typeof item.name === 'string' && item.name !== '')
    ? item.name : eid;
  return { icon, name };
}

/* ── Reusable primitives ───────────────────────────────────────── */

/**
 * A simple preview tile — coloured rounded rect with optional icon and label.
 *
 * @param {object} opts
 * @param {string} [opts.icon]  - MDI icon name
 * @param {string} [opts.label] - short text label
 * @param {string} [opts.color] - CSS background-color override
 * @param {string} [opts.iconSize] - mdc-icon-size in px (default 14)
 */
function simTile(opts = {}) {
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
 */
function simItemTile(item, opts = {}) {
  const { icon, name } = itemDisplay(item);
  const bg = tileBgColor(item);
  const ic = tileIconColor(item);
  const shortName = name.length > 7 ? name.slice(0, 6) + '\u2026' : name;
  const cls = 'pg-preview-tile' + (opts.tileClass ? ' ' + opts.tileClass : '');
  return html`
    <div class="${cls}" style="${bg ? `background:${bg};` : ''}">
      <ha-icon icon="${icon}" style="${ic ? `color:${ic};` : ''}"></ha-icon>
      ${name ? html`<span class="pg-preview-tile-label">${shortName}</span>` : ''}
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
function simSlider(opts = {}) {
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
function simSliderVertical(opts = {}) {
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
function simButtonRow(buttons) {
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
function simItemGrid(items, opts = {}) {
  const cols = opts.cols || 2;
  const max = opts.max || 6;
  const tiles = items.slice(0, max);
  return html`
    <div class="pg-preview-grid pg-preview-grid-${cols}cols">
      ${tiles.map(item => simItemTile(item))}
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
function simTimeDisplay() {
  return html`
    <div class="pg-preview-time-display">12:34</div>
    <div class="pg-preview-date-display">Mon, Jun 16</div>
  `;
}

/**
 * Big temperature display mock.
 */
function simTempDisplay(temp) {
  const t = temp != null ? temp : '21';
  return html`
    <div class="pg-preview-temp-display">
      ${t}<span class="pg-preview-temp-unit">&deg;C</span>
    </div>
  `;
}

/**
 * Forecast row: 5 mini day-icons with labels.
 */
function simForecast() {
  const days = [
    { icon: 'mdi:weather-sunny', label: 'Mon' },
    { icon: 'mdi:weather-cloudy', label: 'Tue' },
    { icon: 'mdi:weather-rainy', label: 'Wed' },
    { icon: 'mdi:weather-partly-cloudy', label: 'Thu' },
    { icon: 'mdi:weather-sunny', label: 'Fri' },
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

/* ── Per-type renderers ────────────────────────────────────────── */

/**
 * Default fallback: icon only.
 */
function renderDefaultPreview(_host, _p, _pIdx, pt) {
  return {
    content: html`
      <ha-icon class="pg-card-preview-icon" icon="${pt ? pt.icon : 'mdi:view-dashboard-outline'}"></ha-icon>`,
  };
}

/* ── Grid ──────────────────────────────────────────────────────── */
function renderGridPreview(_host, panel, _pIdx, _pt) {
  const items = getItems(panel);
  if (items.length === 0) {
    return { content: html``, containerClass: backgroundClass(panel) };
  }
  return {
    content: html`
      <div class="pg-preview-grid-fill">
        ${items.slice(0, 6).map(item => simItemTile(item, { tileClass: 'pg-preview-grid-tile fill' }))}
      </div>`,
    containerClass: backgroundClass(panel),
  };
}

/* ── Row ───────────────────────────────────────────────────────── */
function renderRowPreview(_host, panel, _pIdx, _pt) {
  const items = getItems(panel);
  if (items.length === 0) {
    return { content: html``, containerClass: backgroundClass(panel) };
  }
  // Row page: show up to 5 items as flex-based stacked cards.
  // Each row-card uses flex:1 to take exactly 20% of preview height,
  // with icon/label/buttons centered vertically within the row.
  const shown = items.slice(0, 5);
  return {
    content: html`
      <div class="pg-preview-row-stack" style="justify-content:flex-start;">
        ${shown.map(item => {
          const { icon, name } = itemDisplay(item);
          const shortName = name.length > 16 ? name.slice(0, 14) + '\u2026' : name;
          return html`
            <div class="pg-preview-row-card">
              <ha-icon icon="${icon}"></ha-icon>
              <span class="pg-preview-tile-label">${shortName || 'Item'}</span>
              <div class="pg-preview-btn"><ha-icon icon="mdi:arrow-up-bold"></ha-icon></div>
              <div class="pg-preview-btn"><ha-icon icon="mdi:stop"></ha-icon></div>
              <div class="pg-preview-btn"><ha-icon icon="mdi:arrow-down-bold"></ha-icon></div>
            </div>`;
        })}
        ${items.length > 5
          ? html`<div class="pg-preview-btn-row" style="margin-top:2px;">
              ${['\u25CF','\u25CB','\u25CB'].map(d => html`<span style="font-size:11px;color:var(--secondary-text-color,#888);">${d}</span>`)}
            </div>`
          : ''}
      </div>`,
    contentClass: 'pg-preview-content-top',
    containerClass: backgroundClass(panel),
  };
}

/* ── Light ─────────────────────────────────────────────────────── */
function renderLightPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="justify-content:center;">
        <!-- Left area: buttons left-aligned -->
        <div style="flex:1;display:flex;justify-content:flex-start;align-items:center;">
          <div class="pg-preview-sidebar" style="gap:4px;justify-content:center;">
            <div class="pg-preview-btn active"><ha-icon icon="mdi:brightness-6"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:palette"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:thermometer"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:fire"></ha-icon></div>
          </div>
        </div>
        <!-- Center area: slider only, sized to content -->
        <div style="flex:none;display:flex;align-items:center;">
          ${simSliderVertical({ value: 70 })}
        </div>
        <!-- Right area: label centered -->
        <div style="flex:1;display:flex;align-items:center;justify-content:center;">
          <span style="font-size:0.6em;color:var(--secondary-text-color,#888);font-weight:500;">70%</span>
        </div>
      </div>`,
  };
}

/* ── Climate ───────────────────────────────────────────────────── */
function renderClimatePreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex">
        <!-- Left sidebar: fan/preset/swing buttons -->
        <div class="pg-preview-sidebar" style="gap:4px;justify-content:center;">
          <div class="pg-preview-btn"><ha-icon icon="mdi:fan"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:thermostat"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:swap-vertical"></ha-icon></div>
        </div>
        <!-- Center: temp display + up/down pairs -->
        <div class="pg-preview-main-area" style="gap:2px;">
          <div class="pg-preview-temp-display">22<span class="pg-preview-temp-unit">&deg;C</span></div>
          <div class="pg-preview-btn-row" style="gap:3px;">
            ${['mdi:snowflake','mdi:fire','mdi:autorenew','mdi:water'].map(
              icon => html`<div class="pg-preview-btn active"><ha-icon icon="${icon}"></ha-icon></div>`
            )}
          </div>
        </div>
      </div>`,
  };
}

/* ── Media Player ──────────────────────────────────────────────── */
function renderMediaPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col">
        <!-- Media info: icon left, title+interpret right pinned at top -->
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;padding:4px 0;">
          <ha-icon icon="mdi:music-note" style="--mdc-icon-size:34px;color:var(--primary-color,#4fc3f7);flex-shrink:0;padding:2px;"></ha-icon>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:0;">
            <div style="height:7px;width:100%;background:rgba(255,255,255,0.12);border-radius:3px;"></div>
            <div style="height:6px;width:100%;background:rgba(255,255,255,0.07);border-radius:3px;"></div>
          </div>
        </div>
        <!-- Transport buttons + slider centered in available space -->
        <div style="display:flex;flex-direction:column;gap:2px;flex:1;justify-content:center;">
          ${html`<div class="pg-preview-btn-row" style="justify-content:space-evenly">
  <div class="pg-preview-btn" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:shuffle"></ha-icon></div>
  <div class="pg-preview-btn" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:skip-previous"></ha-icon></div>
  <div class="pg-preview-btn active" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:play"></ha-icon></div>
  <div class="pg-preview-btn" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:skip-next"></ha-icon></div>
  <div class="pg-preview-btn" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:repeat"></ha-icon></div>
</div>`}
          ${simSlider({ value: 45 })}
        </div>
        <!-- Source selectors pinned at bottom -->
        <div style="display:flex;gap:8px;flex-shrink:0;">
          <div class="pg-preview-source-row">
            <ha-icon icon="mdi:music-box" style="--mdc-icon-size:14px;color:var(--secondary-text-color,#888);flex-shrink:0;"></ha-icon>
            <div class="pg-preview-skeleton-bar" style="width:100%;"></div>
          </div>
          <div class="pg-preview-source-row">
            <ha-icon icon="mdi:music-box" style="--mdc-icon-size:14px;color:var(--secondary-text-color,#888);flex-shrink:0;"></ha-icon>
            <div class="pg-preview-skeleton-bar" style="width:100%;"></div>
          </div>
          <div class="pg-preview-source-row">
            <ha-icon icon="mdi:music-box" style="--mdc-icon-size:14px;color:var(--secondary-text-color,#888);flex-shrink:0;"></ha-icon>
            <div class="pg-preview-skeleton-bar" style="width:100%;"></div>
          </div>
        </div>
      </div>`,
  };
}

/* ── Cover ─────────────────────────────────────────────────────── */
function renderCoverPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="justify-content:center;">
        <!-- Left area: buttons pushed right toward slider -->
        <div style="flex:1;display:flex;justify-content:flex-end;align-items:center;">
          <div class="pg-preview-sidebar" style="gap:5px;justify-content:center;">
            <div class="pg-preview-btn"><ha-icon icon="mdi:arrow-up-bold"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:stop"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:arrow-down-bold"></ha-icon></div>
          </div>
        </div>
        <!-- Center area: slider only, sized to content -->
        <div style="flex:none;display:flex;align-items:center;">
          ${simSliderVertical({ value: 60 })}
        </div>
        <!-- Right area: label centered -->
        <div style="flex:1;display:flex;align-items:center;justify-content:center;">
          <span style="font-size:0.65em;font-weight:500;color:var(--secondary-text-color,#aaa);">60%</span>
        </div>
      </div>`,
  };
}

/* ── Vacuum ────────────────────────────────────────────────────── */
function renderVacuumPreview(_host, _panel, _pIdx, _pt) {
  const items = getItems(_panel);
  const entityBtns = [];
  for (let i = 0; i < 6; i++) {
    if (i < items.length) {
      const { icon } = itemDisplay(items[i]);
      entityBtns.push(html`
        <div class="pg-preview-btn" style="width:22px;height:100%;flex:1 1 0;min-width:14px;"><ha-icon icon="${icon}"></ha-icon></div>
      `);
    } else {
      entityBtns.push(html`
        <div class="pg-preview-btn" style="width:22px;height:100%;flex:1 1 0;min-width:14px;background:rgba(255,255,255,0.04);"><ha-icon icon="mdi:plus" style="--mdc-icon-size:11px;color:rgba(255,255,255,0.12);"></ha-icon></div>
      `);
    }
  }
  return {
    content: html`
      <div class="pg-preview-full-col" style="align-self:stretch;min-height:0;">
        <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-height:0;">
          <div class="pg-preview-btn-row" style="gap:4px;">
            <div class="pg-preview-btn"><ha-icon icon="mdi:fan"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:play"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:home-map-marker"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:map-marker"></ha-icon></div>
          </div>
          <div style="display:flex;align-items:center;gap:4px;">
            <ha-icon icon="mdi:battery-charging" style="--mdc-icon-size:12px;color:var(--primary-color,#4fc3f7);"></ha-icon>
            <span class="pg-preview-tile-label" style="font-size:0.5em;">85%</span>
          </div>
        </div>
        <div class="pg-preview-btn-row" style="flex-shrink:0;gap:3px;max-width:100%;overflow:hidden;">
          ${entityBtns}
        </div>
      </div>`,
  };
}

/* ── Timer ─────────────────────────────────────────────────────── */
function renderTimerPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:6px;align-items:center;justify-content:center;">
        <div class="pg-preview-temp-display">00:30</div>
        <div class="pg-preview-btn-row">
          <div class="pg-preview-btn"><ha-icon icon="mdi:play"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:pause"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:cancel"></ha-icon></div>
        </div>
      </div>`,
  };
}

/* ── Alarm ─────────────────────────────────────────────────────── */
function renderAlarmPreview(_host, _panel, _pIdx, _pt) {
  // Layout: 3x4 keypad on the left, 4 stacked action buttons on the right,
  // matching the real Nextion page (keypad keys 70px, action btns 180px).
  const fnBtns = ['AWAY','HOME','DISARM','PANIC'];
  const keys = ['1','2','3','4','5','6','7','8','9','CLR','0','DEL'];
  return {
    content: html`
      <div class="pg-preview-full-flex" style="gap:8px;align-items:stretch;">
        <!-- Keypad: 3 columns x 4 rows -->
        <div class="pg-preview-keypad-grid">
          ${keys.map(k => html`
            <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.55em;color:var(--secondary-text-color,#999);">${k}</span></div>
          `)}
        </div>
        <!-- Right: 4 wider stacked action buttons -->
        <div class="pg-preview-action-col">
          ${fnBtns.map(label => html`
            <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label">${label}</span></div>
          `)}
        </div>
      </div>`,
  };
}

/* ── Unlock popup ─────────────────────────────────────────────── */
function renderUnlockPreview(_host, _panel, _pIdx, _pt) {
  // PIN unlock overlay: 3x4 keypad on the left, with UNLOCK indicator
  // + keypad content on the right, matching the real overlay layout.
  const keys = ['1','2','3','4','5','6','7','8','9','CLR','0','DEL'];
  return {
    content: html`
      <div class="pg-preview-full-flex" style="gap:8px;align-items:stretch;">
        <!-- Keypad: 3 columns x 4 rows -->
        <div class="pg-preview-keypad-grid">
          ${keys.map(k => html`
            <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.55em;color:var(--secondary-text-color,#999);">${k}</span></div>
          `)}
        </div>
        <!-- Right: single wider UNLOCK action button + 3 blanks -->
        <div class="pg-preview-action-col">
          <div class="pg-preview-btn active" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label">UNLOCK</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
        </div>
      </div>`,
  };
}

/* ── Clock ─────────────────────────────────────────────────────── */
function renderClockPreview(_host, panel, _pIdx, _pt) {
  const showWeather = panel?.show_weather !== false;
  const showTemp = panel?.show_temp !== false;
  const showNotifs = panel?.show_notifications !== false;
  const bg = backgroundClass(panel);
  const items = (panel && panel.items) || [];

  // Build 6 entity button slots from panel.items
  const entitySlots = [0, 1, 2, 3, 4, 5].map(i => {
    const item = items[i];
    if (item) {
      const { icon, name } = itemDisplay(item);
      const shortName = name.length > 6 ? name.slice(0, 5) + '\u2026' : name;
      const tileBg = tileBgColor(item);
      const tileIc = tileIconColor(item);
      return html`
        <div class="pg-preview-clock-entity-btn" style="${tileBg ? `background:${tileBg};` : ''}">
          <ha-icon icon="${icon}" style="${tileIc ? `color:${tileIc};` : ''}"></ha-icon>
          ${name ? html`<span class="pg-preview-clock-entity-label">${shortName}</span>` : ''}
        </div>
      `;
    }
    return html`
      <div class="pg-preview-clock-entity-btn" style="background:rgba(255,255,255,0.04);">
        <ha-icon icon="mdi:plus" style="--mdc-icon-size:clamp(10px,2.2cqi,15px);color:rgba(255,255,255,0.12);"></ha-icon>
      </div>
    `;
  });

  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:1px;">
        <!-- Top zone: temperature left, notification + weather icon right -->
        <div style="display:flex;flex-shrink:0;align-items:flex-start;width:100%;gap:4px;min-height:0;">
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:1px;">
            ${showTemp ? html`
              <div style="font-size:clamp(11px,3cqi,20px);color:var(--primary-text-color,#ddd);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                <ha-icon icon="mdi:thermometer" style="--mdc-icon-size:clamp(11px,2.5cqi,16px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
                21<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
              </div>
              <div style="font-size:clamp(8px,2cqi,13px);color:var(--secondary-text-color,#888);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">1023 hPa</div>
            ` : ''}
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;align-items:flex-start;">
            ${showNotifs ? html`
              <ha-icon icon="mdi:bell-ring-outline" style="--mdc-icon-size:clamp(14px,3.5cqi,24px);color:var(--accent-color,#ffab40);"></ha-icon>
            ` : ''}
            ${showWeather ? html`
              <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size:clamp(22px,6cqi,40px);color:var(--primary-color,#4fc3f7);"></ha-icon>
            ` : ''}
          </div>
        </div>

        <!-- Center zone: big time + date -->
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;min-height:0;gap:1px;">
          <span class="pg-preview-weather-clock">12:34</span>
          <div style="font-size:clamp(9px,2.2cqi,14px);color:var(--secondary-text-color,#aaa);font-weight:400;">Mon, Jun 16</div>
        </div>

        <!-- Bottom zone: 6 entity buttons -->
        <div class="pg-preview-clock-entity-row">
          ${entitySlots}
        </div>
      </div>`,
    containerClass: bg,
  };
}

/* ── Clock Two (word clock) ────────────────────────────────────── */
function renderClockTwoPreview(_host, panel, _pIdx, _pt) {
  // Word-clock style: scattered letter-like rect placeholders forming a loose grid
  const letters = 'ITLISASAMPMACKWADTENFIFTYFOURHALFBTWOTHR'.split('');
  const rows = [];
  // Use CSS Grid with 1fr columns so the letter grid fills the full preview width
  for (let r = 0; r < 5; r++) {
    const cells = [];
    for (let c = 0; c < 7; c++) {
      const idx = r * 7 + c;
      if (idx < letters.length) {
        cells.push(html`<div style="height:100%;background:rgba(255,255,255,0.10);border-radius:3px;display:flex;align-items:center;justify-content:center;"><span style="font-size:0.55em;color:var(--secondary-text-color,#888);font-weight:500;">${letters[idx]}</span></div>`);
      }
    }
    rows.push(html`<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;height:100%;">${cells}</div>`);
  }
  return {
    content: html`
      <div style="display:grid;grid-template-rows:repeat(5,1fr);gap:3px;width:100%;flex:1;">
        ${rows}
      </div>`,
    containerClass: backgroundClass(panel),
  };
}

/* ── Weather ───────────────────────────────────────────────────── */
function renderWeatherPreview(_host, panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:1px;">
        <!-- Top row: tMainText (inside/outside temp, left) + tDate (right) -->
        <div style="display:flex;gap:4px;flex-shrink:0;align-items:center;min-height:20px;">
          <div style="font-size:clamp(9px,2.4cqi,16px);color:var(--primary-text-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500;flex-shrink:1;min-width:0;">
            <ha-icon icon="mdi:home-thermometer" style="--mdc-icon-size:clamp(9px,2cqi,14px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
            22<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
            &nbsp;
            <ha-icon icon="mdi:thermometer" style="--mdc-icon-size:clamp(9px,2cqi,14px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
            21<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
          </div>
          <div style="font-size:clamp(9px,2.4cqi,16px);color:var(--primary-text-color,#ddd);font-weight:500;flex:1;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;">Monday, 21 May</div>
        </div>
        <!-- Sub-text row: tSubText (pressure, left, below tMainText) -->
        <div style="display:flex;flex-shrink:0;min-height:14px;">
          <div style="font-size:clamp(8px,1.8cqi,12px);color:var(--secondary-text-color,#888);">1023 hPa</div>
        </div>
        <!-- Main body: tMainIcon left + d1/d2 info right, tTime far right -->
        <div class="pg-preview-full-flex" style="gap:4px;flex:1;min-height:0;">
          <!-- Left section: icon + d1/d2 side by side -->
          <div style="display:flex;gap:4px;flex:1;min-width:0;align-items:flex-start;">
            <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size:clamp(38px,11cqi,70px);color:var(--primary-color,#4fc3f7);flex-shrink:0;"></ha-icon>
            <!-- d1/d2 info rows to the right of icon -->
            <div style="display:flex;flex-direction:column;gap:3px;min-width:0;">
              <div class="pg-preview-weather-info-row">
                <ha-icon icon="mdi:water-percent" style="--mdc-icon-size:clamp(12px,2.8cqi,20px);color:var(--secondary-text-color,#aaa);flex-shrink:0;"></ha-icon>
                <span style="font-size:clamp(9px,2cqi,13px);color:var(--secondary-text-color,#999);">65%</span>
              </div>
              <div class="pg-preview-weather-info-row">
                <ha-icon icon="mdi:weather-windy" style="--mdc-icon-size:clamp(12px,2.8cqi,20px);color:var(--secondary-text-color,#aaa);flex-shrink:0;"></ha-icon>
                <span style="font-size:clamp(9px,2cqi,13px);color:var(--secondary-text-color,#999);">15 km/h</span>
              </div>
            </div>
          </div>
          <!-- Right: tTime (giant clock) -->
          <div style="display:flex;align-items:flex-start;justify-content:flex-end;flex:1.6;min-width:0;margin-top:-4px;">
            <span class="pg-preview-weather-clock">12:34</span>
          </div>
        </div>
        <!-- Forecast: 5-day -->
        <div class="pg-preview-forecast">
          ${['Mon','Tue','Wed','Thu','Fri'].map((day, i) => html`
            <div class="pg-preview-forecast-day">
              <span class="pg-preview-forecast-dayname">${day}</span>
              <ha-icon icon="${['mdi:weather-sunny','mdi:weather-cloudy','mdi:weather-rainy','mdi:weather-partly-cloudy','mdi:weather-sunny'][i]}"></ha-icon>
              <span class="pg-preview-forecast-hightemp">${['22','18','15','20','25'][i]}&deg;</span>
              <span class="pg-preview-forecast-lowtemp">${['12','10','8','11','14'][i]}&deg;</span>
            </div>
          `)}
        </div>
      </div>`,
    containerClass: backgroundClass(panel),
  };
}

/**
 * Generate a flat 15x15 QR-like pattern with three proper finder patterns
 * (top-left, top-right, bottom-left) and a dense data area in bottom-right.
 * The finder patterns follow the standard QR 7x7 square-in-square layout.
 */
function generateQRMatrix15() {
  // Standard QR code finder pattern (7x7, 1=dark module, 0=light)
  const finder = [
    [1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1],
    [1,0,1,1,1,0,1],
    [1,0,1,1,1,0,1],
    [1,0,1,1,1,0,1],
    [1,0,0,0,0,0,1],
    [1,1,1,1,1,1,1],
  ];
  // Pseudo-random 7x7 data area (looks like real encoded modules)
  const data = [
    [1,0,1,0,1,0,1],
    [0,1,1,1,0,0,1],
    [1,0,0,1,1,1,0],
    [1,1,0,0,0,1,0],
    [0,1,1,0,1,0,1],
    [1,0,0,1,1,1,0],
    [0,1,1,0,0,1,1],
  ];
  const cells = [];
  for (let r = 0; r < 15; r++) {
    for (let c = 0; c < 15; c++) {
      if (r < 7 && c < 7) cells.push(finder[r][c]);          // TL finder
      else if (r < 7 && c >= 8) cells.push(finder[r][c - 8]); // TR finder
      else if (r >= 8 && c < 7) cells.push(finder[r - 8][c]); // BL finder
      else if (r >= 8 && c >= 8) cells.push(data[r - 8][c - 8]); // data area
      else cells.push(0); // separator rows/columns
    }
  }
  return cells;
}

const QR_MATRIX = generateQRMatrix15();

function renderQRMatrix(size, isBig) {
  const px = size || '4px';
  const gridStyle = isBig
    ? ''  // CSS class pg-preview-qr-matrix--big handles it with 1fr
    : `grid-template-columns:repeat(15,${px});grid-template-rows:repeat(15,${px})`;
  return html`
    <div class="pg-qr-matrix-bg${isBig ? ' pg-qr-matrix-bg--big' : ''}">
      <div class="pg-preview-qr-matrix${isBig ? ' pg-preview-qr-matrix--big' : ''}" style="${gridStyle}">
        ${QR_MATRIX.map(v => html`<div class="pg-preview-qr-cell${v ? ' fill' : ' empty'}"></div>`)}
      </div>
    </div>`;
}


function renderQRPreview(_host, p, _pIdx, _pt) {
  if (p.start_big_qr === true) {
    return {
      content: html`
        <div class="pg-preview-center-col" style="width:100%;flex:1;justify-content:center;">
          <div class="pg-qr-preview-big-wrap">
            ${renderQRMatrix(undefined, true)}
          </div>
        </div>`,
    };
  }
  // Small QR mode — left: QR matrix, right: icon+text info blocks
  // Matches real layout: qrCode at x=15, info blocks starting at x=200
  const showInfo = p.show_info !== false;
  const items = p.items || [];
  let sideContent;
  if (showInfo) {
    // Default: SSID icon + title + text, password icon + title + text
    sideContent = html`
      <div class="pg-preview-qr-info-row">
        <ha-icon icon="mdi:wifi" class="pg-qr-icon"></ha-icon>
        <div class="pg-preview-qr-info-text">
          <div class="pg-preview-text-line narrow" style="width:45%;"></div>
          <div class="pg-preview-text-line wide" style="width:80%;"></div>
        </div>
      </div>
      <div class="pg-preview-qr-info-row">
        <ha-icon icon="mdi:key" class="pg-qr-icon"></ha-icon>
        <div class="pg-preview-qr-info-text">
          <div class="pg-preview-text-line narrow" style="width:50%;"></div>
          <div class="pg-preview-text-line wide" style="width:70%;"></div>
        </div>
      </div>`;
  } else if (items.length) {
    // Items mode — up to 2 custom item blocks
    sideContent = items.slice(0, 2).map(item => html`
      <div class="pg-preview-qr-info-row">
        <ha-icon icon="${item.icon || 'mdi:help-circle-outline'}" class="pg-qr-icon"></ha-icon>
        <div class="pg-preview-qr-info-text">
          <div class="pg-preview-text-line narrow" style="width:45%;"></div>
          <div class="pg-preview-text-line wide" style="width:80%;"></div>
        </div>
      </div>`);
  } else {
    // Fallback placeholder lines
    sideContent = html`
      <div class="pg-card-preview-line" style="width:80px;"></div>
      <div class="pg-card-preview-line" style="width:50px;"></div>`;
  }
  return {
    content: html`
      <div class="pg-preview-qr-matrix-wrap">
        ${renderQRMatrix('clamp(3px, 1.4cqi, 5px)')}
      </div>
      <div class="pg-preview-qr-side">
        ${sideContent}
      </div>`,
    contentClass: 'pg-card-preview-qr-small',
  };
}

/* ── Notify ────────────────────────────────────────────────────── */
function renderNotifyPreview(_host, panel, _pIdx, _pt) {
  // Real layout: large icon area (134×160) left + text area (278×160) right,
  // with two side-by-side action buttons at the bottom.
  return {
    content: html`
      <div class="pg-preview-full-col" style="min-height:0;">
        <!-- Icon + text area (takes most of the space) -->
        <div style="display:flex;flex:1;gap:4px;min-height:0;align-items:stretch;">
          <div style="display:flex;align-items:center;justify-content:center;flex-shrink:0;width:28%;background:rgba(255,255,255,0.04);border-radius:3px;">
            <ha-icon icon="mdi:bell-ring-outline" style="--mdc-icon-size:clamp(14px,3cqi,26px);color:var(--primary-color,#4fc3f7);opacity:0.6;"></ha-icon>
          </div>
          <div style="display:flex;flex-direction:column;justify-content:center;flex:1;gap:3px;min-width:0;padding:2px 0;">
            <div class="pg-preview-text-line wide" style="height:clamp(4px,1cqi,9px);"></div>
            <div class="pg-preview-text-line wide" style="height:clamp(4px,1cqi,9px);"></div>
            <div class="pg-preview-text-line medium" style="height:clamp(4px,1cqi,9px);width:60%;"></div>
          </div>
        </div>
        <!-- Two side-by-side action buttons at the bottom -->
        <div class="pg-preview-btn-row" style="gap:2px;margin-top:2px;">
          <div class="pg-preview-btn" style="width:100%;height:auto;min-height:18px;"><span class="pg-preview-btn-label">DISMISS</span></div>
          <div class="pg-preview-btn" style="width:100%;height:auto;min-height:18px;"><span class="pg-preview-btn-label">ACTION</span></div>
        </div>
      </div>`,
  };
}

/* ── Select ────────────────────────────────────────────────────── */
function renderSelectPreview(_host, panel, _pIdx, _pt) {
  // Real layout: 12 buttons (bSel1-12) in 3×4 grid, each 140×55,
  // or 4 full-width buttons (bSelFull1-4) in "full" mode.
  const isFull = panel && panel.select_mode === 'full';
  const labels = isFull
    ? ['Option A','Option B','Option C','Option D']
    : ['1','2','3','4','5','6','7','8','9','10','11','12'];
  return {
    content: html`
      <div style="display:${isFull ? 'flex' : 'grid'};flex-direction:column;${isFull ? '' : 'grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(4,1fr)'};gap:3px;width:100%;flex:1;min-height:0;">
        ${isFull
          ? labels.map(l => html`
              <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label" style="font-size:0.5em;color:var(--secondary-text-color,#999);">${l}</span></div>
            `)
          : labels.map(l => html`
              <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.5em;color:var(--secondary-text-color,#999);">${l}</span></div>
            `)}
      </div>`,
  };
}

/* ── Settings ──────────────────────────────────────────────────── */
function renderSettingsPreview(_host, _panel, _pIdx, _pt) {
  return {
    contentClass: 'pg-preview-content-top',
    content: html`
      <div class="pg-preview-full-col" style="gap:4px;padding:3px 0;justify-content:flex-start;min-height:0;">
        <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
          <ha-icon icon="mdi:brightness-6" style="--mdc-icon-size:12px;color:var(--secondary-text-color,#999);flex-shrink:0;"></ha-icon>
          <span style="flex:1;min-width:0;font-size:0.55em;color:var(--primary-text-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Brightness</span>
          <span style="font-size:0.55em;color:var(--secondary-text-color,#999);flex-shrink:0;">85%</span>
        </div>
        ${simSlider({ value: 85 })}
        <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
          <ha-icon icon="mdi:brightness-4" style="--mdc-icon-size:12px;color:var(--secondary-text-color,#999);flex-shrink:0;"></ha-icon>
          <span style="flex:1;min-width:0;font-size:0.55em;color:var(--primary-text-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Dimmed</span>
          <span style="font-size:0.55em;color:var(--secondary-text-color,#999);flex-shrink:0;">30%</span>
        </div>
        ${simSlider({ value: 30 })}
      </div>`,
  };
}

/* ── About ─────────────────────────────────────────────────────── */
function renderAboutPreview(_host, _panel, _pIdx, _pt) {
  return {
    containerClass: 'pg-preview-bg-system',
    content: html`
      <div class="pg-preview-full-col" style="gap:3px;padding:6px;">
        <div class="pg-preview-text-line" style="height:clamp(6px,2cqi,12px);width:85%;align-self:center;"></div>
        <div class="pg-preview-text-line" style="height:clamp(6px,2cqi,12px);width:75%;align-self:center;"></div>
        <div style="flex:1;min-height:6px;"></div>
        <div style="display:flex;flex-direction:column;gap:2px;width:60%;align-self:flex-end;">
          <div class="pg-preview-text-line" style="height:clamp(7px,2cqi,13px);width:85%;align-self:flex-end;background:rgba(255,255,255,0.14);"></div>
          <div class="pg-preview-text-line" style="height:clamp(5px,1.5cqi,10px);width:65%;align-self:flex-end;"></div>
          <div style="display:flex;gap:clamp(10px,3cqi,20px);width:100%;margin-top:3px;">
            <div class="pg-preview-text-line" style="flex:1;"></div>
            <div class="pg-preview-text-line" style="width:28%;"></div>
          </div>
          <div style="display:flex;gap:clamp(10px,3cqi,20px);width:100%;">
            <div class="pg-preview-text-line" style="flex:1;"></div>
            <div class="pg-preview-text-line" style="width:28%;"></div>
          </div>
          <div style="display:flex;gap:clamp(10px,3cqi,20px);width:100%;">
            <div class="pg-preview-text-line" style="flex:1;"></div>
            <div class="pg-preview-text-line" style="width:28%;"></div>
          </div>
        </div>
      </div>`,
  };
}

/* ── System ────────────────────────────────────────────────────── */
function renderSystemPreview(_host, _panel, _pIdx, _pt) {
  return {
    containerClass: 'pg-preview-bg-system',
    content: html`
      <div style="display:flex;width:100%;flex:1;align-items:center;justify-content:center;">
        <ha-icon icon="mdi:connection" style="--mdc-icon-size:48px;color:var(--primary-color,#4fc3f7);"></ha-icon>
      </div>`,
  };
}

/* ── Blank ─────────────────────────────────────────────────────── */
function renderBlankPreview(_host, _panel, _pIdx, _pt) {
  return {
    // Blank — minimal empty state, no content rendered
    content: html``,
  };
}

/* ── Register all preview renderers ────────────────────────────── */
registerPanelPreview('grid', renderGridPreview);
registerPanelPreview('row', renderRowPreview);
registerPanelPreview('light', renderLightPreview);
registerPanelPreview('climate', renderClimatePreview);
registerPanelPreview('media', renderMediaPreview);
registerPanelPreview('cover', renderCoverPreview);
registerPanelPreview('vacuum', renderVacuumPreview);
registerPanelPreview('timer', renderTimerPreview);
registerPanelPreview('alarm', renderAlarmPreview);
registerPanelPreview('clock', renderClockPreview);
registerPanelPreview('clocktwo', renderClockTwoPreview);
registerPanelPreview('weather', renderWeatherPreview);
registerPanelPreview('qr', renderQRPreview);
registerPanelPreview('notify', renderNotifyPreview);
registerPanelPreview('notifs', renderNotifyPreview);
registerPanelPreview('select', renderSelectPreview);
registerPanelPreview('system_settings', renderSettingsPreview);
registerPanelPreview('system_about', renderAboutPreview);
registerPanelPreview('system', renderSystemPreview);
registerPanelPreview('blank', renderBlankPreview);
// Popup aliases share renderers with their base types (handled via panel.type)
registerPanelPreview('popup_unlock', renderUnlockPreview);
registerPanelPreview('popup_notify', renderNotifyPreview);
registerPanelPreview('popup_notifs', renderNotifyPreview);
registerPanelPreview('popup_select', renderSelectPreview);
registerPanelPreview('popup_light', renderLightPreview);
registerPanelPreview('popup_media_player', renderMediaPreview);
registerPanelPreview('popup_vacuum', renderVacuumPreview);
registerPanelPreview('popup_climate', renderClimatePreview);
registerPanelPreview('popup_timer', renderTimerPreview);
registerPanelPreview('popup_cover', renderCoverPreview);
