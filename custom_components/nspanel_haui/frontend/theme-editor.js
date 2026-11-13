/**
 * NSPanel HAUI - Theme sidebar management.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { clone, DEVICE_CONFIG_DEFAULTS } from './constants.js';
import { t } from './localize.js';

const THEME_PANEL_COLOR_FIELDS = new Set([
  "text_color", "back_color", "color_pressed", "back_color_pressed", "power_color",
  "keypad_bg_color", "keypad_text_color", "arm_button_color", "arm_button_back_color",
  "disarm_button_color", "disarm_button_back_color", "off_color", "letter_color", "special_color",
]);

function clearPanelColorOverrides(value) {
  if (Array.isArray(value)) {
    value.forEach(clearPanelColorOverrides);
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const key of Object.keys(value)) {
    if (THEME_PANEL_COLOR_FIELDS.has(key)) delete value[key];
    else clearPanelColorOverrides(value[key]);
  }
}

export function openThemeSidebar(host) {
  if (!host._selectedDevice) return;
  host._loadDeviceConfig(host._selectedDevice);
  const storedConfig = host._panels.devices?.[host._selectedDevice]?.config || {};
  host._themeId = storedConfig.theme_id || "dark";
  host._themeVariant = storedConfig.theme_variant || "dark";
  // Open the theme editor from the Panels view's Theme card.
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
    theme_variant: detail.themeVariant === "light" ? "light" : "dark",
  };
  const panels = clone(host._devicePanels());
  if (detail.resetPanelColors) {
    clearPanelColorOverrides(panels);
  }
  host._themeId = config.theme_id;

  // savePanels shows the success or error toast; keep the sidebar open on failure.
  const message = detail.resetPanelColors
    ? t("Theme applied and panel color overrides reset")
    : t("Theme applied");
  if (await host._savePanels(panels, message, config)) {
    closeThemeSidebar(host);
  } else {
    host.requestUpdate();
  }
}