/**
 * NSPanel HAUI - Editor - Panel preview utilities.
 *
 * Shared utility functions for panel preview renderers.
 */
import { t } from '../localize.js';

/**
 * Pick a background class for the screen based on the panel's `background` option.
 * Returns a CSS class string (e.g. 'pg-preview-bg-spring') or empty string.
 */
export function backgroundClass(panel) {
  const bg = panel && panel.background;
  if (!bg || bg === 'default') return '';
  return 'pg-preview-bg-' + bg;
}

/**
 * Extract the "items" array from a panel config, defaulting to empty array.
 * Both grid and row panels store items under the `items` key.
 */
export function getItems(panel) {
  return (panel && panel.items) || [];
}

/**
 * Convert a color value to a CSS color string, using the same approach as the
 * panel edit dialog's color swatch (see form-fields.js parseRgbListToHex).
 * Accepts: number (RGB565), [r,g,b] array, "[r,g,b]" string, "#rrggbb" / "rrggbb",
 * numeric string like "63488", or CSS color names.
 *
 * Returns a CSS color string (rgb() or hex), or null if unparseable.
 */
export function colorToCss(val) {
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
  header_accent: 62694,
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
export function getDeviceColors(host) {
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
export function deviceThemeCss(deviceColors) {
  return [
    '--primary-text-color:' + (deviceColors.text || '#ddd'),
    '--secondary-text-color:' + (deviceColors.text_inactive || '#888'),
    '--primary-color:' + (deviceColors.component_active || '#4fc3f7'),
    '--accent-color:' + (deviceColors.header_accent || '#f69d31'),
  ].join(';');
}

/**
 * Build a CSS background-color string for a tile given item config fields.
 * Falls back to null (no custom background).
 */
export function tileBgColor(item) {
  if (!item) return null;
  const bc = item.back_color;
  if (bc != null && bc !== '' && bc !== '0') {
    const css = colorToCss(bc);
    if (css) return css;
  }
  return null;
}

/**
 * Build a CSS color string for icon/text in a tile given item config fields.
 */
export function tileIconColor(item) {
  if (!item) return null;
  // Check grid-specific text_color override first, then fall back to the
  // standard HAUIItem color override (the same field used by get_color()).
  const tc = item.text_color || item.color;
  if (tc != null && tc !== '' && tc !== '0') {
    const css = colorToCss(tc);
    if (css) return css;
  }
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
export function itemEntityId(item) {
  if (!item) return '';
  if (typeof item === 'string') return item;
  if (typeof item.item === 'string') return item.item;
  if (typeof item.entity_id === 'string') return item.entity_id;
  return '';
}

/**
 * Normalise an item into { icon, name } for display in a tile.
 */
export function itemDisplay(item) {
  if (!item) return { icon: 'mdi:help-circle-outline', name: t('?') };
  const eid = itemEntityId(item);
  const icon = (item.icon && typeof item.icon === 'string' && item.icon !== '')
    ? item.icon : 'mdi:help-circle-outline';
  const name = (item.name && typeof item.name === 'string' && item.name !== '')
    ? item.name : eid;
  return { icon, name };
}
