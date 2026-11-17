/**
 * NSPanel HAUI - color theme library helpers.
 *
 * Pure helpers for the Theme sidebar: built-in theme labels, unique names and
 * ids for new custom themes, and the JSON file format behind Export / Import.
 */
import { t } from './localize.js';

export const THEME_FILE_VERSION = 1;

/**
 * The icon palette a theme uses: its own page background decides between the
 * dark and the light one. Mirrors `Theme.background_variant()` in Python
 * (`custom_components/nspanel_haui/haui/mapping/color.py`).
 * @param {Record<string, number> | undefined} colors
 * @returns {'dark'|'light'}
 */
export function themeIconVariant(colors) {
  const background = colors?.background;
  if (typeof background !== 'number') return 'dark';
  const red = Math.floor(((background >> 11) & 0x1f) * 255 / 31);
  const green = Math.floor(((background >> 5) & 0x3f) * 255 / 63);
  const blue = Math.floor((background & 0x1f) * 255 / 31);
  const brightness = Math.floor((2126 * red + 7152 * green + 722 * blue) / 10000);
  return brightness >= 128 ? 'light' : 'dark';
}

/**
 * The translated name of a built-in theme. Looked up at render: t() returns
 * its key until the translations have loaded, which is after this module.
 * @param {string} id
 */
export function builtinThemeLabel(id) {
  return {
    dark: t("Dark Color"),
    light: t("Light Color"),
    white: t("White"),
    black: t("Black"),
    midnight: t("Midnight"),
    ocean: t("Ocean"),
    forest: t("Forest"),
    sunset: t("Sunset"),
    violet: t("Violet"),
    sky: t("Sky"),
  }[id];
}

/**
 * Build select options for the device default, built-in themes and saved custom themes.
 * @param {Record<string, {name: string}>} library
 * @param {{includeDeviceTheme?: boolean}} [options]
 * @returns {{value: string, label: string}[]}
 */
export function themeOptions(library, { includeDeviceTheme = false } = {}) {
  const options = includeDeviceTheme
    ? [{ value: '', label: t('Device theme (default)') }]
    : [];
  for (const [id, theme] of Object.entries(library)) {
    options.push({ value: id, label: builtinThemeLabel(id) || theme.name });
  }
  return options;
}

/**
 * A custom theme name derived from `base` that no existing theme uses.
 * @param {Record<string, { name: string }>} themes
 * @param {string} base
 */
export function uniqueThemeName(themes, base) {
  const names = new Set(Object.values(themes).map((theme) => theme.name.toLowerCase()));
  let name = `${base} (custom)`;
  for (let suffix = 2; names.has(name.toLowerCase()); suffix += 1) {
    name = `${base} (custom ${suffix})`;
  }
  return name;
}

/**
 * A custom theme id derived from `base` that no existing theme uses.
 * @param {Record<string, unknown>} themes
 * @param {string} base
 */
export function uniqueThemeId(themes, base) {
  let id = `${base}-custom`;
  for (let suffix = 2; themes[id]; suffix += 1) {
    id = `${base}-custom-${suffix}`;
  }
  return id;
}

/**
 * The id a new custom theme gets from its name.
 * @param {string} name
 */
export function themeIdFromName(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

/**
 * The JSON body of an exported theme file.
 * @param {Record<string, unknown>} themes
 */
export function themeFile(themes) {
  return { version: THEME_FILE_VERSION, themes };
}

/**
 * Parse an imported theme file; throws on anything that is not one.
 * @param {string} text
 * @returns {Record<string, any>}
 */
export function parseThemeFile(text) {
  const data = JSON.parse(text);
  if (data?.version !== THEME_FILE_VERSION || !data.themes || typeof data.themes !== "object") {
    throw new Error("invalid theme file");
  }
  return data.themes;
}

/**
 * Download `themes` as a theme file.
 * @param {Record<string, unknown>} themes
 * @param {string} filename
 */
export function downloadThemes(themes, filename) {
  const blob = new Blob([JSON.stringify(themeFile(themes), null, 2)], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
