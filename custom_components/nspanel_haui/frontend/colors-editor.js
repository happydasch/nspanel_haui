/**
 * NSPanel HAUI - Colors override dialog management.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { clone, DEVICE_CONFIG_DEFAULTS } from './constants.js';
import { t } from './localize.js';

const SCHEME_PANEL_COLOR_FIELDS = new Set([
  "text_color", "back_color", "color_pressed", "back_color_pressed", "power_color",
  "keypad_bg_color", "keypad_text_color", "arm_button_color", "arm_button_back_color",
  "disarm_button_color", "disarm_button_back_color", "off_color", "letter_color", "special_color",
]);

function clearSchemePanelOverrides(value) {
  if (Array.isArray(value)) {
    value.forEach(clearSchemePanelOverrides);
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const key of Object.keys(value)) {
    if (SCHEME_PANEL_COLOR_FIELDS.has(key)) delete value[key];
    else clearSchemePanelOverrides(value[key]);
  }
}

export function openColorsDialog(host) {
  host._actionsMenuIndex = null;
  if (!host._selectedDevice) return;
  host._loadDeviceConfig(host._selectedDevice);
  const overrides = host._deviceConfig?.color_overrides || {};
  const storedConfig = host._panels.devices?.[host._selectedDevice]?.config || {};
  host._colorsSchemeId =
    storedConfig.color_scheme_id || storedConfig.color_scheme ||
    (overrides.background === 65535 ? "light" : "dark");
  host._colorsScheme = storedConfig.color_scheme || "dark";
  host._colorsDialog = clone(overrides);
  host._showColorsDialog = true;
  host.requestUpdate();
}

export function closeColorsDialog(host) {
  host._showColorsDialog = false;
  host.requestUpdate();
}

export async function saveColors(host, detail) {
  if (!detail?.schemeId || !host._selectedDevice) return;

  const config = {
    ...(host._deviceConfig || DEVICE_CONFIG_DEFAULTS),
    color_scheme_id: detail.schemeId,
    color_scheme: detail.scheme === "light" ? "light" : "dark",
  };
  const panels = clone(host._devicePanels());
  if (detail.resetOverrides) {
    config.color_overrides = {};
    clearSchemePanelOverrides(panels);
  }
  host._colorsSchemeId = config.color_scheme_id;

  // savePanels shows the success or error toast; keep the dialog open on failure.
  if (await host._savePanels(panels, t("Color scheme applied and panel color overrides cleared"), config)) {
    host._showColorsDialog = false;
  }
  host.requestUpdate();
}