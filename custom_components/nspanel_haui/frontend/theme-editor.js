/**
 * NSPanel HAUI - Theme sidebar management.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { DEVICE_CONFIG_DEFAULTS } from './constants.js';
import { t } from './localize.js';

/**
 * The theme editor of the device's selected theme. `themeId` is the choice the
 * Connection & device card's Edit theme row names; without it the stored choice
 * is used.
 */
export function openThemeSidebar(host, themeId = null) {
  if (!host._selectedDevice) return;
  host._loadDeviceConfig(host._selectedDevice);
  const storedConfig = host._panels.devices?.[host._selectedDevice]?.config || {};
  host._themeId = themeId || storedConfig.theme_id || "dark";
  host.store.actions.pushOverlay({ kind: 'theme', anchorKey: 'theme', subject: host._selectedDevice, draft: null });
  host.requestUpdate();
}

export function closeThemeSidebar(host) {
  host.store.actions.closeOverlay('theme', 'theme');
  host.requestUpdate();
}

export async function saveTheme(host, detail) {
  if (!detail?.themeId || !host._selectedDevice) return;

  const config = {
    ...(host._deviceConfig || DEVICE_CONFIG_DEFAULTS),
    theme_id: detail.themeId,
  };
  host._themeId = config.theme_id;

  // Save settings first: the theme selection must not be coupled to panel state.
  if (!(await host._saveDeviceConfig(config, t("Theme applied")))) {
    host.requestUpdate();
    return;
  }
  if (detail.resetPanelColors) {
    await host._savePanels(host._devicePanels(), '');
  }
  closeThemeSidebar(host);
}