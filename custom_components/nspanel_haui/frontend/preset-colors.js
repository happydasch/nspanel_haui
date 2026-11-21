// @ts-check
/**
 * NSPanel HAUI - the colours a quick start preset derives from the device theme.
 *
 * A page option can take a colour from the theme, but a saved config carries
 * literal values: a template in a generated item would be evaluated with no
 * theme variables at hand (`hub/adapter.py`). A preset that needs one therefore
 * materialises it when it is resolved, from the theme the device itself draws in
 * (`presets.js`). Colours the hub resolves on every render - a grid tile's on
 * background and its power button - are left unset, so they follow a theme
 * change instead of pinning the theme the preset was created in.
 */
import { parseRgbListToHex, rgb565ToHex } from './color-utils.js';

/**
 * The colour map of the theme a device draws in: its own theme first (a custom
 * one before the built-in of that id), then the device default (dark).
 *
 * @param {Record<string, any>|null|undefined} customThemes
 * @param {Record<string, any>|null|undefined} builtinThemes
 * @param {string|null|undefined} themeId
 * @returns {Record<string, any>|null}
 */
export function themePalette(customThemes, builtinThemes, themeId) {
  const wanted = themeId || '';
  const theme = (wanted && (customThemes?.[wanted] || builtinThemes?.[wanted]))
    || builtinThemes?.dark
    || null;
  const colors = theme?.colors;
  return colors && typeof colors === 'object' ? colors : null;
}

/**
 * One palette entry as a #rrggbb colour, or '' when the theme does not set it.
 *
 * @param {Record<string, any>|null} palette
 * @param {string} key
 */
export function paletteHex(palette, key) {
  const value = palette?.[key];
  if (typeof value === 'number') return rgb565ToHex(value);
  return value ? parseRgbListToHex(value) : '';
}
