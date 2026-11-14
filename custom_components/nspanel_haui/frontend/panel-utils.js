/**
 * NSPanel HAUI - Shared panel-list helpers.
 *
 * Grouping and role markers for the Device panel list. The view modules stay
 * dumb: they render what these helpers and the shell prepared.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import { icon } from './ui/icon.js';

/**
 * Collect system panel keys from the host's panels data.
 * @param {object} host - editor component
 * @returns {Set<string>}
 */
export function getSystemPanelKeys(host) {
  return new Set((host._panels?.system_panels || []).map(sp => sp.key).filter(Boolean));
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
 * Home and Idle role markers for a panel thumbnail.
 *
 * @param {string|null|undefined} key
 * @param {object} [deviceConfig]
 * @returns {Array} templates for the thumbnail's marker overlay
 */
export function panelRoleMarkers(key, deviceConfig = {}) {
  const roles = [];
  if (!key || !deviceConfig) return roles;
  if (key === deviceConfig.home_panel) {
    roles.push(html`<span class="haui-panel-role haui-panel-role-home" role="img" aria-label=${t('Home panel')}>${icon('home')}</span>`);
  }
  if (key === deviceConfig.idle_panel) {
    roles.push(html`<span class="haui-panel-role haui-panel-role-idle" role="img" aria-label=${t('Idle panel')}>${icon('sleep')}</span>`);
  }
  return roles;
}

