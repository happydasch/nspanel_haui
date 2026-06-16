/**
 * NSPanel HAUI - Editor - Shared color utility functions.
 *
 * Canonical implementation of color conversion between hex, RGB565, and CSS formats.
 * Extracted from form-fields.js, dialogs/colors.js, and previews/utils.js to eliminate
 * three near-duplicate implementations of the same conversion logic.
 */

/**
 * Convert a hex #rrggbb string to an RGB565 integer (0–65535).
 * Uses Math.round scaling for accuracy across the full input range.
 */
export function hexToRgb565(hex) {
  const raw = hex.replace("#", "");
  const rr = parseInt(raw.slice(0, 2), 16);
  const gg = parseInt(raw.slice(2, 4), 16);
  const bb = parseInt(raw.slice(4, 6), 16);
  if (![rr, gg, bb].every(Number.isFinite)) return 0;
  const r = Math.round((rr * 31) / 255);
  const g = Math.round((gg * 63) / 255);
  const b = Math.round((bb * 31) / 255);
  return (r << 11) | (g << 5) | b;
}

/**
 * Convert an RGB565 integer (0–65535) to a #rrggbb hex string.
 */
export function rgb565ToHex(num) {
  const n = num | 0;
  const r5 = (n >> 11) & 0x1F;
  const g6 = (n >> 5) & 0x3F;
  const b5 = n & 0x1F;
  const r = Math.round((r5 * 255) / 31);
  const g = Math.round((g6 * 255) / 63);
  const b = Math.round((b5 * 255) / 31);
  return "#"
    + r.toString(16).padStart(2, '0')
    + g.toString(16).padStart(2, '0')
    + b.toString(16).padStart(2, '0');
}

/** Convert hex #rrggbb to "[r, g, b]" string (for template display). */
export function hexToRgbList(hex) {
  const m = hex.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (!m) return "";
  return `[${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)}]`;
}

/** Convert hex #rrggbb to [r, g, b] number array. */
export function hexToRgbArray(hex) {
  const m = hex.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (!m) return null;
  return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
}

/**
 * Parse any color value to hex #rrggbb, or "" if unparseable.
 * Accepts: number (RGB565), [r,g,b] array, "[r, g, b]" string, "#rrggbb" / "rrggbb".
 */
export function parseRgbListToHex(val) {
  if (val === null || val === undefined || val === "") return "";
  if (typeof val === "number") return rgb565ToHex(val);
  if (Array.isArray(val) && val.length === 3) {
    const r = Math.min(255, Math.max(0, parseInt(val[0], 10)));
    const g = Math.min(255, Math.max(0, parseInt(val[1], 10)));
    const b = Math.min(255, Math.max(0, parseInt(val[2], 10)));
    if ([r, g, b].every(Number.isFinite)) {
      return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }
    return "";
  }
  const s = String(val).trim();
  if (s.includes("{{")) return "";
  // RGB565 integer string → hex
  if (/^\d{1,5}$/.test(s)) return rgb565ToHex(parseInt(s, 10));
  // "[r, g, b]" format
  const rgbMatch = s.match(/\[\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\]/);
  if (rgbMatch) {
    const r = Math.min(255, Math.max(0, parseInt(rgbMatch[1])));
    const g = Math.min(255, Math.max(0, parseInt(rgbMatch[2])));
    const b = Math.min(255, Math.max(0, parseInt(rgbMatch[3])));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }
  const hexMatch = s.match(/^#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (hexMatch) {
    return `#${hexMatch[1].toLowerCase()}${hexMatch[2].toLowerCase()}${hexMatch[3].toLowerCase()}`;
  }
  return "";
}

/**
 * Convert a hex #rrggbb to a new color value matching the type of the previous value.
 * Handles: number (RGB565), array [r,g,b], "[r, g, b]" string, "#rrggbb" string.
 * Falls back to RGB565 number.
 */
export function hexToColorMatching(hex, prevVal) {
  if (Array.isArray(prevVal)) return hexToRgbArray(hex);
  if (typeof prevVal === "number") return hexToRgb565(hex);
  if (typeof prevVal === "string") {
    const t = prevVal.trim();
    if (t.startsWith("[")) return hexToRgbList(hex);
    if (t.startsWith("#")) return hex;
  }
  return hexToRgb565(hex);
}

/**
 * Common NSPanel color presets for quick selection (hex values).
 */
export const COLOR_PRESETS = [
  "#FFFFFF", "#F5F5F5", "#E0E0E0", "#9E9E9E", "#616161", "#212121",
  "#F44336", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5", "#2196F3",
  "#03A9F4", "#00BCD4", "#009688", "#4CAF50", "#8BC34A", "#CDDC39",
  "#FFEB3B", "#FFC107", "#FF9800", "#FF5722", "#795548", "#607D8B",
];

/**
 * Unified color-to-CSS parser. Accepts multiple input formats and returns
 * a CSS color string (hex, rgb(), or null).
 *
 * Input formats:
 *  - Number (RGB565 integer)
 *  - [r,g,b] array
 *  - "[r,g,b]" string
 *  - "#rrggbb" or "rrggbb"
 *  - CSS color name or rgb()/hsl() string
 *  - Numeric string like "63488"
 *
 * Returns a CSS color string or null if unparseable.
 */
export function colorToCss(val) {
  if (val == null || val === '') return null;
  if (typeof val === 'number') {
    if (val <= 0) return null;
    const r = Math.round(((val & 0xF800) >> 11) * 255 / 31);
    const g = Math.round(((val & 0x07E0) >> 5) * 255 / 63);
    const b = Math.round((val & 0x001F) * 255 / 31);
    return `rgb(${r},${g},${b})`;
  }
  if (Array.isArray(val) && val.length === 3) {
    const r = Math.min(255, Math.max(0, parseInt(val[0], 10)));
    const g = Math.min(255, Math.max(0, parseInt(val[1], 10)));
    const b = Math.min(255, Math.max(0, parseInt(val[2], 10)));
    if ([r, g, b].every(Number.isFinite)) return `rgb(${r},${g},${b})`;
    return null;
  }
  const s = String(val).trim();
  if (s.includes('{{')) return null;
  if (/^(#|rgb|hsl)/i.test(s)) return s;
  if (/^[0-9a-fA-F]{6}$/.test(s)) return '#' + s;
  const rgbMatch = s.match(/^\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]\s*$/);
  if (rgbMatch) return `rgb(${rgbMatch[1]},${rgbMatch[2]},${rgbMatch[3]})`;
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