/**
 * NSPanel HAUI - Editor - Localization helper.
 *
 * Fetches UI text translations from the backend and provides a simple
 * lookup function that falls back to the English key when no translation
 * is available for the user's HA language.
 *
 * Usage:
 *   import { fetchTranslations, t, getLanguage } from './localize.js';
 *   await fetchTranslations(hass, 'de');
 *   t('Cancel');  // → "Abbrechen" or "Cancel" if not found
 */

/** @type {Object<string, string> | null} */
let _translations = null;
/** @type {string | null} */
let _currentLang = null;

/**
 * Fetch translations for the given language from the backend.
 * Caches aggressively so a given language is fetched only once per session.
 * On failure (network error, missing endpoint) falls back to empty map.
 *
 * @param {import("lit").LitElement} hass - the hass object from the Lit element
 * @param {string} lang - language code ('en', 'de', 'nl', 'pl')
 * @returns {Promise<Object<string, string>>} flat { key: translation } map
 */
export async function fetchTranslations(hass, lang) {
  if (_currentLang === lang && _translations) return _translations;
  try {
    const resp = await hass.fetchWithAuth(
      `/api/nspanel_haui/translations/${encodeURIComponent(lang)}?flat=1`
    );
    _translations = await resp.json();
    _currentLang = lang;
  } catch {
    // Fallback: return empty so keys display as-is (English)
    _translations = {};
    _currentLang = lang;
  }
  return _translations;
}

/**
 * Translate a key using the cached translation map.
 * Returns the translated string if available, otherwise the key itself.
 *
 * @param {string} key - English text to translate
 * @returns {string}
 */
export function t(key) {
  return _translations?.[key] || key;
}

/**
 * Extract the HAUI-supported language code from the hass object.
 * Handles full locale strings like "de-DE", "de_DE" → "de".
 * Defaults to "en" when the language is not one of our supported locales.
 *
 * @param {import("lit").LitElement} [hass]
 * @returns {string}
 */
export function getLanguage(hass) {
  if (!hass?.language) return 'en';
  const lang = hass.language.split('-')[0].split('_')[0].toLowerCase();
  return ['en', 'de', 'nl', 'pl'].includes(lang) ? lang : 'en';
}
