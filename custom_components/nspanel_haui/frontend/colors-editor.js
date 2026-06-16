/**
 * NSPanel HAUI - Editor - Colors override dialog management.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { clone, DEVICE_CONFIG_DEFAULTS } from './constants.js';

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

  host._deviceConfig = {
    ...(host._deviceConfig || DEVICE_CONFIG_DEFAULTS),
    color_overrides: overrides,
  };

  try {
    await host._savePanels(host._devicePanels(), "Device colors saved");
    host._showToast("Device colors saved", "success");
  } catch (e) {
    host._showToast(e.message || "Failed to save colors", "error");
  } finally {
    host._showColorsDialog = false;
    host.requestUpdate();
  }
}