/**
 * NSPanel HAUI - the editor's per-browser preferences.
 *
 * The side stack's expanded card, the selected panel's preview fold, the
 * Add panel catalog's preview size and Fleet's latest-events window are one
 * localStorage flag each; the shell reads them on start and the surfaces that
 * change them write them back, so a reload opens the editor the way it was left.
 */
import { readStorage, writeStorage } from './dom-helpers.js';

// Whether the Connection card lists its facts and the Diagnostics card shows its
// tiles; per-browser preferences.
const DETAILS_EXPANDED_KEY = 'haui_deviceDetailsExpanded';
const DIAGNOSTICS_EXPANDED_KEY = 'haui_diagnosticsExpanded';
// Whether the selected panel's card shows its render large; remembered per browser.
const PANEL_PREVIEW_FOLDED_KEY = 'haui_panelPreviewFolded';
// Which preview size the Add panel catalog last used ('1' compact), so it opens the way it was left.
const CATALOG_COMPACT_KEY = 'haui_panelCatalogCompact';
// The moment Fleet's latest events were reset to (ms); empty for the default 24 hours.
const FLEET_EVENTS_SINCE_KEY = 'haui_fleetEventsSince';

/** The preferences the shell starts from, before normalizing the side cards. */
export function readEditorPreferences() {
  return {
    catalogCompact: readStorage(CATALOG_COMPACT_KEY, '0') === '1',
    panelPreviewCollapsed: readStorage(PANEL_PREVIEW_FOLDED_KEY, '0') === '1',
    detailsExpanded: readStorage(DETAILS_EXPANDED_KEY, '1') === '1',
    diagnosticsExpanded: readStorage(DIAGNOSTICS_EXPANDED_KEY, '0') === '1',
  };
}

/**
 * Store the side stack's expanded card. Only one of the two sides is open at a
 * time, so both are written together.
 *
 * @param {{ detailsExpanded: boolean, diagnosticsExpanded: boolean }} sideCards
 */
export function writeSideCards({ detailsExpanded, diagnosticsExpanded }) {
  writeStorage(DETAILS_EXPANDED_KEY, detailsExpanded ? '1' : '0');
  writeStorage(DIAGNOSTICS_EXPANDED_KEY, diagnosticsExpanded ? '1' : '0');
}

/** @param {boolean} collapsed */
export function writePanelPreviewFolded(collapsed) {
  writeStorage(PANEL_PREVIEW_FOLDED_KEY, collapsed ? '1' : '0');
}

/** @param {boolean} compact */
export function writeCatalogCompact(compact) {
  writeStorage(CATALOG_COMPACT_KEY, compact ? '1' : '0');
}

/**
 * The moment Fleet's latest-events window starts at, or null for the default 24 hours.
 *
 * @returns {number|null}
 */
export function readFleetEventsSince() {
  const stored = Number(readStorage(FLEET_EVENTS_SINCE_KEY, ''));
  return Number.isFinite(stored) && stored > 0 ? stored : null;
}

/**
 * Remember Fleet's latest-events window per browser; null restores the 24 hours.
 *
 * @param {number|null} since
 */
export function writeFleetEventsSince(since) {
  writeStorage(FLEET_EVENTS_SINCE_KEY, since === null ? '' : String(since));
}
