// @ts-check
/**
 * NSPanel HAUI - the colours a quick start preset derives from the device theme.
 *
 * A generated panel should look like the panel it lands on, and colour is the
 * one thing a preset can carry that makes a first render look intentional. The
 * hub resolves a panel's colours against the theme it renders in
 * (`haui/mapping/color.py`), but a saved config carries literal values: a
 * template in a generated item would be evaluated with no theme variables at
 * hand (`hub/adapter.py`). So the palette is materialised when a preset is
 * resolved, from the theme the device itself draws in.
 */
import { mixHex, parseRgbListToHex, rgb565ToHex } from './color-utils.js';

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

/** How far an on tile is lifted off the page background. */
const TILE_TINT = 0.16;

/**
 * The colours of a grid tile, keyed by the item state the tile shows: a tint of
 * the page background while the item is on, so an off tile keeps the theme's
 * own background. An unknown palette sets nothing, and the device theme's
 * defaults stay in charge.
 *
 * @param {Record<string, any>|null} palette
 * @returns {{ back_color?: Record<string, string>, power_color?: string }}
 */
export function tileColors(palette) {
  const background = paletteHex(palette, 'background');
  const on = paletteHex(palette, 'entity_on');
  if (!background || !on) return {};
  const tint = mixHex(background, on, TILE_TINT);
  return { back_color: { on: tint, playing: tint }, power_color: on };
}
