/**
 * NSPanel HAUI - Shared panel utilities.
 *
 * Common helpers for both grid and list views: panel filtering,
 * move-state computation, and badge rendering.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';

/**
 * Collect system panel keys from the host's panels data.
 * @param {object} host - editor component
 * @returns {Set<string>}
 */
export function getSystemPanelKeys(host) {
  return new Set((host._panels?.system_panels || []).map(sp => sp.key).filter(Boolean));
}

/**
 * Split a full panels array into navigation-visible and hidden groups.
 * When systemPanelKeys is provided, panels whose key matches are excluded
 * (override panels are hidden from both lists).
 * @param {Array} panels
 * @param {Set} [systemPanelKeys] - optional set of system panel keys to exclude
 * @returns {{ navPanels: Array, hiddenPanels: Array }}
 */
export function computeFilteredPanels(panels, systemPanelKeys) {
  const userPanels = systemPanelKeys
    ? panels.filter(p => !systemPanelKeys.has(p.key))
    : panels;
  const navPanels = userPanels.filter(p => p.show_in_navigation !== false);
  const hiddenPanels = userPanels.filter(p => p.show_in_navigation === false);
  return { navPanels, hiddenPanels };
}

/**
 * Given a panel and whether it belongs to the nav group, compute its index
 * within its group and whether it can be moved up/down.
 * @param {object} p - the panel config object
 * @param {Array} panels - the full panels array
 * @param {boolean} isNavPanel - whether the panel is in the navigation group
 * @returns {{ pIdx: number, canMoveUp: boolean, canMoveDown: boolean }}
 */
export function getPanelMoveState(p, panels, isNavPanel) {
  const { navPanels, hiddenPanels } = computeFilteredPanels(panels);
  const matchByKey = (x) => p.key && x.key === p.key;
  const pIdx = p.key ? panels.findIndex(matchByKey) : panels.indexOf(p);
  const navIdx = p.key ? navPanels.findIndex(matchByKey) : navPanels.indexOf(p);
  const hiddenIdx = p.key ? hiddenPanels.findIndex(matchByKey) : hiddenPanels.indexOf(p);
  const canMoveUp = isNavPanel ? navIdx > 0 : hiddenIdx > 0;
  const canMoveDown = isNavPanel ? (navIdx >= 0 && navIdx < navPanels.length - 1) : (hiddenIdx >= 0 && hiddenIdx < hiddenPanels.length - 1);
  return { pIdx, canMoveUp, canMoveDown };
}

/**
 * Build badge icons for home/sleep/wakeup panel designations and the
 * system-panel "edited" marker.
 * @param {object} p - panel config
 * @param {object} dc - device config
 * @param {boolean} [hasOverride] - render the edited badge for system panels
 * @returns {Array} array of TemplateResult badge elements
 */
export function renderBadges(p, dc, hasOverride = false) {
  const badges = [];
  if (!p.key) return badges;
  if (p.key === dc.home_panel) badges.push(html`<span class="pl-badge pl-badge-home" title=${t('Home panel')}><ha-icon icon="mdi:home-outline"></ha-icon></span>`);
  if (p.key === dc.sleep_panel) badges.push(html`<span class="pl-badge pl-badge-sleep" title=${t('Sleep panel')}><ha-icon icon="mdi:weather-night"></ha-icon></span>`);
  if (p.key === dc.wakeup_panel) badges.push(html`<span class="pl-badge pl-badge-wakeup" title=${t('Wakeup panel')}><ha-icon icon="mdi:weather-sunny"></ha-icon></span>`);
  if (hasOverride) badges.push(html`<span class="pl-badge pl-badge-edited" title=${t('Edited (overrides system default)')}><ha-icon icon="mdi:pencil"></ha-icon></span>`);
  return badges;
}