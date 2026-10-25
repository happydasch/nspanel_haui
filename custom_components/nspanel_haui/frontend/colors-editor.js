/**
 * NSPanel HAUI - Colors override dialog management.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { clone, DEVICE_CONFIG_DEFAULTS } from './constants.js';
import { t } from './localize.js';

export function openColorsDialog(host) {
  host._actionsMenuIndex = null;
  if (!host._selectedDevice) return;
  host._loadDeviceConfig(host._selectedDevice);
  const overrides = host._deviceConfig?.color_overrides || {};
  host._colorsDialog = clone(overrides);
  host._showColorsDialog = true;
  host.requestUpdate();
}

export function closeColorsDialog(host) {
  host._showColorsDialog = false;
  host.requestUpdate();
}

export async function saveColors(host, overrides) {
  if (!overrides || !host._selectedDevice) return;

  const config = {
    ...(host._deviceConfig || DEVICE_CONFIG_DEFAULTS),
    color_overrides: overrides,
  };

  // savePanels shows the success or error toast; keep the dialog open on failure.
  if (await host._savePanels(host._devicePanels(), t("Device colors saved"), config)) {
    host._showColorsDialog = false;
  }
  host.requestUpdate();
}