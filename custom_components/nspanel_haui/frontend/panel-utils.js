/**
 * NSPanel HAUI - Shared panel-list helpers.
 *
 * Grouping and role markers for the Device panel list. The view modules stay
 * dumb: they render what these helpers and the shell prepared.
 */
import { t } from './localize.js';
import { panelRoleMarker } from './ui/panel-role.js';

/**
 * Collect system panel keys from the host's panels data.
 * @param {object} host - editor component
 * @returns {Set<string>}
 */
export function getSystemPanelKeys(host) {
  return new Set((host._panels?.system_panels || []).map(sp => sp.key).filter(Boolean));
}

/**
 * The name a panel is shown by: its own title, else the label of its type, else
 * its key. The hub names an untitled panel by its type too
 * (`HAUIPanel.get_title`), so the editor never shows a bare key for one.
 *
 * @param {any} panel - a panel config
 * @param {Array} [panelTypes] - the hub's panel type descriptors
 * @returns {string}
 */
export function panelName(panel, panelTypes = []) {
  const typeLabel = (panelTypes || []).find((type) => type.type_key === panel?.type)?.label;
  return panel?.title || typeLabel || panel?.key || '';
}

/**
 * Split a device's panels and the hub's system entries into the groups the
 * Device workspace shows. Popup overrides are stored among the user panels but
 * belong to the Popups group; a popup the device does not replace is offered in
 * the panel catalog instead (`defaults`), and the fixed system panels are not
 * listed at all.
 *
 * @param {Array} [panels] - the device's panel configs
 * @param {Array} [systemPanels] - `system_panels` from the hub
 * @returns {{ navigation: Array, hidden: Array, popups: Array, defaults: Array }}
 */
export function groupPanels(panels = [], systemPanels = []) {
  const systemKeys = new Set(systemPanels.map((entry) => entry.key).filter(Boolean));
  const userPanels = panels.filter((panel) => !systemKeys.has(panel.key));
  const overridden = (entry) => panels.some((panel) => panel.key === entry.key);
  const editable = systemPanels.filter((entry) => entry.editable);
  return {
    navigation: userPanels.filter((panel) => panel.show_in_navigation !== false),
    hidden: userPanels.filter((panel) => panel.show_in_navigation === false),
    popups: editable.filter(overridden),
    defaults: editable.filter((entry) => !overridden(entry)),
  };
}

/**
 * A device that still needs its first panel: it has none, so its display shows
 * only the hub's keyless default clock and no page navigation leads anywhere.
 *
 * @param {{ panels?: unknown[] }|null|undefined} device
 * @returns {boolean}
 */
export function needsSetup(device) {
  return (device?.panels || []).length === 0;
}

/**
 * Home and Idle role markers for a panel thumbnail.
 *
 * The idle panels are one ordered carousel (`idle_panel` first, then
 * `idle_panel_extra`), so the panel the device shows first carries the plain
 * idle marker and every further one a dimmed marker whose label numbers its
 * place in the cycle.
 *
 * @param {string|null|undefined} key
 * @param {{ homePanel?: string, idleKeys?: string[] }} [roleConfig] - the panel
 *   the device opens at home, and its idle carousel in play order
 * @returns {Array} templates for the thumbnail's marker overlay
 */
export function panelRoleMarkers(key, { homePanel = '', idleKeys = [] } = {}) {
  const markers = [];
  if (!key) return markers;
  if (key === homePanel) markers.push(panelRoleMarker({ role: 'home' }));
  const idleOrder = idleKeys.indexOf(key);
  if (idleOrder === 0) markers.push(panelRoleMarker({ role: 'idle' }));
  if (idleOrder > 0) {
    markers.push(panelRoleMarker({
      role: 'idle',
      extra: true,
      label: t('Idle panel {count}').replace('{count}', String(idleOrder + 1)),
    }));
  }
  return markers;
}

