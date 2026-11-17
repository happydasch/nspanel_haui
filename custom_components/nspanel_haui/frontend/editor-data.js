/**
 * NSPanel HAUI - the editor's bootstrap data.
 *
 * The integration entries the editor can show, the color theme library and the
 * translations. The hub's own data (devices, panels, status, panel types) is
 * loaded by the store; these three belong to the editor element, which mirrors
 * them into its render state.
 */
import { fetchStateNames, fetchTranslations, t } from './localize.js';

/**
 * Look up the integration entries and open the first hub. Runs once the editor
 * has a Home Assistant connection.
 * @param {any} host - the editor element
 */
export async function loadEntries(host) {
  if (!host.hass) return;
  try {
    const entries = await host.api.entries.list();
    host._entriesError = null;
    if (entries.length && !host.entryId) {
      const entryId = entries[0].entry_id;
      host.__notificationsFor = entryId;
      await host._load(entryId);
      // Not awaited: Fleet shows what it finds when the scan returns.
      host._scanDevices();
    } else if (!entries.length) {
      host._store.actions.setLoading(false);
    }
  } catch (error) {
    console.error('Failed to load NSPanel HAUI integration list:', error);
    host._entriesError = error.message || t('Failed to load the integration list');
    host._store.actions.setLoading(false);
  }
}

/**
 * Load the built-in and custom themes of one hub entry, once.
 * @param {any} host - the editor element
 * @param {string|null} [entryId]
 * @param {boolean} [force] - load again although this entry's library is loaded
 */
export async function loadThemeLibrary(host, entryId = host.entryId, force = false) {
  if (!entryId || (!force && host.__themeLibraryEntry === entryId)
      || host.__themeLibraryLoadingEntry === entryId) return;
  host.__themeLibraryLoadingEntry = entryId;
  host._themesLoading = true;
  host._themesError = '';
  if (host.__themeLibraryEntry !== entryId) {
    host._builtinThemes = {};
    host._customThemes = {};
  }
  host.requestUpdate();
  try {
    const data = await host.api.editor.themes(entryId);
    if (host.entryId !== entryId) return;
    host._builtinThemes = data.builtins || {};
    host._customThemes = data.themes || {};
    host.__themeLibraryEntry = entryId;
  } catch (_error) {
    if (host.entryId === entryId) {
      host._themesError = t('Unable to load color themes.');
      host.__themeLibraryEntry = entryId;
    }
  } finally {
    if (host.__themeLibraryLoadingEntry === entryId) {
      host.__themeLibraryLoadingEntry = null;
      host._themesLoading = false;
      host.requestUpdate();
    }
  }
}

/**
 * Load the UI translations and the localized panel types for `lang`.
 * @param {any} host - the editor element
 * @param {string} lang
 */
export async function loadLanguage(host, lang) {
  // Translations first: panel types carry translated labels, and a failed
  // load is reported through t(), which is only translated once this resolves.
  await fetchTranslations(host.api, lang);
  await Promise.all([host._loadPanelTypes(), fetchStateNames(host.api, lang)]);
  // t() reads a module-level map, so Lit does not know the text changed.
  host.requestUpdate();
}
