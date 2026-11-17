/**
 * NSPanel HAUI - device configuration.
 * Load/open/close helpers for the device configuration dialog state, and the
 * save it reports back.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.  The class methods are thin wrappers:
 *
 *   _loadDeviceConfig(name)   { return DeviceConfig.loadDeviceConfig(this, name); }
 *   _openDeviceConfig()       { return DeviceConfig.openDeviceConfig(this); }
 *   _closeDeviceConfig()      { return DeviceConfig.closeDeviceConfig(this); }
 */
import { clone } from './constants.js';
import { t } from './localize.js';
import * as DeviceEvents from './device-events.js';

/* ── load ─────────────────────────────────────────────────────────────────── */

export function loadDeviceConfig(host, name) {
  host._deviceConfig = host.store.selectors.configFor(name);
}

/* ── open / close ─────────────────────────────────────────────────────────── */

export async function openDeviceConfig(host) {
  const name = host._selectedDevice;
  if (!name) return;
  if (!(await host.store.actions.loadDeviceConfig(name))) return;
  host._editingDeviceConfig = true;
  host._deviceConfigForm = clone(host.store.selectors.configFor(name));
  host.store.actions.pushOverlay({
    kind: 'device-settings',
    anchorKey: 'device-settings',
    subject: name,
    draft: null,
  });
}

export function closeDeviceConfig(host) {
  host._editingDeviceConfig = false;
  host._deviceConfigForm = null;
  host.store.actions.closeOverlay('device-settings', 'device-settings');
}

/* ── save ─────────────────────────────────────────────────────────────────── */

/** The display model changed, so the matching TFT must be installed; the upload restarts the display. */
export function tftInstallParams() {
  return {
    title: t("Install display TFT?"),
    message: t("The display model changed. Install the matching TFT now? The display cannot be used while the TFT updates."),
    confirmText: t("Install TFT"),
    cancelText: t("Not now"),
    confirmVariant: "brand",
  };
}

/**
 * Save the settings sidebar's form. The display cannot report which layout it
 * runs, so a model change asks before installing the matching TFT.
 * @param {any} host
 * @param {any} event
 */
export async function onDeviceConfigSave(host, event) {
  const cfg = event.detail?.config;
  if (!cfg || !host._selectedDevice) return;
  const previousModel = host._deviceConfig?.display_model;

  // saveDeviceConfig shows the success or error toast; keep the dialog open on failure.
  if (await host._saveDeviceConfig(clone(cfg), t("Device configuration saved"))) {
    host._closeDeviceConfig();
    // The upload restarts the display, so ask first instead of installing on save.
    if (cfg.display_model !== previousModel && cfg.update?.enabled !== false) {
      host._tftInstallTarget = host._selectedDevice;
    }
  }
  host.requestUpdate();
}

/** @param {any} host */
export async function confirmTftInstall(host) {
  const name = host._tftInstallTarget;
  host._tftInstallTarget = null;
  if (!name) return;
  await DeviceEvents.installTft(host, { detail: { name } });
}

/** @param {any} host */
export function cancelTftInstall(host) {
  host._tftInstallTarget = null;
  host.requestUpdate();
}
