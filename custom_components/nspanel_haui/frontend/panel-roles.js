/**
 * NSPanel HAUI - a device's home and idle panel roles.
 *
 * Both roles are the same kind of setting: `home_panel` names one panel,
 * `idle_panel` + `idle_panel_extra` name an ordered list, and a key can outlive
 * its panel - settings copied from a device that had it, a restored backup, or a
 * device that never had the panel. The hub drops the key of a panel it removes
 * (a delete or a move to another device), so a reference surviving its panel came
 * from outside that path. The hub ignores such a reference
 * (see `haui/controller/navigation.py`: Home falls back to the first navigation
 * panel, a missing idle page is dropped from the cycle), so the editor treats
 * both roles alike: a key that names no panel is never a set panel, and it stays
 * visible under its own key so it can be removed.
 *
 * Everything the editor shows or decides about these roles goes through this
 * module, so the editor follows the hub instead of repeating the rule per call
 * site.
 */
import { t } from './localize.js';

/**
 * The panel keys of a comma-separated setting such as `idle_panel_extra`.
 *
 * @param {unknown} value
 * @returns {string[]}
 */
export function panelKeys(value) {
  return String(value ?? '').split(',').map((key) => key.trim()).filter(Boolean);
}

/**
 * The ordered idle-panel sequence the settings hold: the primary key first, then
 * the extra ones. Runtime navigation deduplicates these keys, so the editor does
 * too. Keys stay as stored, so a panel that no longer exists is still listed and
 * can be removed; {@link resolveIdleKeys} answers what the device plays.
 *
 * @param {unknown} idlePanel
 * @param {unknown} idlePanelExtra
 * @returns {string[]}
 */
export function idlePanelKeys(idlePanel, idlePanelExtra) {
  return [...new Set([String(idlePanel ?? '').trim(), ...panelKeys(idlePanelExtra)].filter(Boolean))];
}

/**
 * Split an ordered idle-panel sequence into the two persisted settings.
 *
 * @param {string[]} keys
 * @returns {{ idle_panel: string, idle_panel_extra: string }}
 */
export function idlePanelConfig(keys) {
  const unique = [...new Set(keys.map((key) => key.trim()).filter(Boolean))];
  return { idle_panel: unique[0] || '', idle_panel_extra: unique.slice(1).join(', ') };
}

/**
 * Whether `key` names a panel the device has: one of its own panels, or a system
 * panel (a popup it extends, or a fixed page).
 *
 * @param {string|null|undefined} key
 * @param {any[]} [panels] - the device's panel configs
 * @param {any[]} [systemPanels] - `system_panels` from the hub
 * @returns {boolean}
 */
export function panelExists(key, panels = [], systemPanels = []) {
  if (!key) return false;
  return panels.some((panel) => panel?.key === key) || systemPanels.some((entry) => entry?.key === key);
}

/**
 * The name of a panel reference whose panel is gone. A reference is never
 * silently dropped from a list - it stays visible, under its own marker and its
 * real key, so it can be removed.
 *
 * @param {string|null|undefined} key
 * @returns {string}
 */
export function unknownPanelRef(key) {
  return t('Unknown key "{key}"').replace('{key}', String(key ?? ''));
}

/**
 * @typedef {Object} PanelRole
 * @property {string[]} keys - the configured keys that name a panel, in play order
 * @property {string[]} missing - the configured keys that name no panel
 * @property {string} fallback - the panel the device opens while none is configured
 */

/**
 * Both of the device's panel roles, resolved the way the device resolves them.
 *
 * A role's configured keys split into the ones that name a panel (the device
 * plays those) and the ones that name none; the hub ignores the second kind, so
 * they are not a set panel. Home additionally falls back to the first navigation
 * panel while nothing is configured - a popup override never joins navigation,
 * so it is no fallback.
 *
 * @param {any[]} [panels] - the device's panel configs
 * @param {any} [config] - the device settings
 * @param {any[]} [systemPanels] - `system_panels` from the hub
 * @returns {{ home: PanelRole, idle: PanelRole }}
 */
export function resolvePanelRoles(panels = [], config = {}, systemPanels = []) {
  /** @param {string[]} configured */
  const role = (configured) => {
    /** @type {PanelRole} */
    const resolved = { keys: [], missing: [], fallback: '' };
    for (const key of configured) {
      if (panelExists(key, panels, systemPanels)) resolved.keys.push(key);
      else resolved.missing.push(key);
    }
    return resolved;
  };
  const home = role([String(config.home_panel ?? '')].filter(Boolean));
  if (!home.keys.length) {
    const systemKeys = new Set(systemPanels.map((entry) => entry?.key));
    home.fallback = panels.find(
      (panel) => panel?.show_in_navigation !== false && !systemKeys.has(panel.key),
    )?.key || '';
  }
  return {
    home,
    idle: role(idlePanelKeys(config.idle_panel, config.idle_panel_extra)),
  };
}

/**
 * The panel Home opens, as the device resolves it: the configured panel while the
 * device has it, else the first navigation panel, else none. A popup override is
 * stored among the device's panels but never joins navigation, so it is no
 * fallback either.
 *
 * @param {any[]} [panels] - the device's panel configs
 * @param {any} [config] - the device settings
 * @param {any[]} [systemPanels] - `system_panels` from the hub
 * @returns {string} the panel's key, or '' when the device has no home panel
 */
export function resolveHomeKey(panels = [], config = {}, systemPanels = []) {
  const { home } = resolvePanelRoles(panels, config, systemPanels);
  return home.keys[0] || home.fallback;
}

/**
 * The idle pages the device plays, in order: the configured keys that name a
 * panel, since the hub drops the others.
 *
 * @param {any[]} [panels] - the device's panel configs
 * @param {any} [config] - the device settings
 * @param {any[]} [systemPanels] - `system_panels` from the hub
 * @returns {string[]}
 */
export function resolveIdleKeys(panels = [], config = {}, systemPanels = []) {
  return resolvePanelRoles(panels, config, systemPanels).idle.keys;
}
