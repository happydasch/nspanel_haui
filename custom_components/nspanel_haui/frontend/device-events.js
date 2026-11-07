/**
 * NSPanel HAUI - Device manager event handlers.
 *
 * Extracted from haui-editor.js; each function takes the component instance
 * (`host`) as its first parameter.
 */
import { t } from './localize.js';
import * as Api from './api.js';
import { savePanels } from './crud.js';

/**
 * Get the user-friendly display name for a device, falling back to the device key.
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} name  - device key
 * @returns {string}
 */
function _friendlyName(host, name) {
  return host._panels?.devices?.[name]?.friendly_name || name;
}


export async function onDeviceManagerMoveDevice(host, e) {
  const { name, direction } = e.detail || {};
  if (!name || !direction) return;
  const devices = host._panels.devices || {};
  const deviceKeys = Object.keys(devices);
  const idx = deviceKeys.indexOf(name);
  if (idx < 0) return;
  const swapIdx = idx + direction;
  if (swapIdx < 0 || swapIdx >= deviceKeys.length) return;

  const newKeys = [...deviceKeys];
  [newKeys[idx], newKeys[swapIdx]] = [newKeys[swapIdx], newKeys[idx]];

  const newDevices = {};
  for (const key of newKeys) {
    newDevices[key] = devices[key];
  }
  // savePanels posts the store built from _panels, so the new order goes in
  // first and is taken back when the server rejects the save.
  const previous = host._panels;
  host._panels = { ...host._panels, devices: newDevices };
  const friendly = _friendlyName(host, name);
  const message = direction < 0
    ? t('Device "{name}" moved up').replace('{name}', friendly)
    : t('Device "{name}" moved down').replace('{name}', friendly);
  if (!(await host._savePanels(host._devicePanels(), message))) host._panels = previous;
}

export async function onDeviceManagerToggleDevice(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  const dev = (host._panels.devices || {})[name];
  if (!dev) return;
  const config = dev.config || {};
  const newEnabled = !(config.enabled !== false);
  // savePanels commits editor state only once the server accepts the save.
  await savePanels(
    host,
    dev.panels || [],
    `"${_friendlyName(host, name)}" ${newEnabled ? t("enabled") : t("disabled")}`,
    { ...config, enabled: newEnabled },
    name
  );
  host.requestUpdate();
}

export function onDeviceManagerSelect(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  host._selectDevice(name);
}

export function onDeviceManagerSettings(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  host._showDeviceManager = false;
  host._selectedDevice = name;
  host._loadDeviceConfig(name);
  host._openDeviceConfig();
  host.requestUpdate();
}

export async function onDeviceManagerRemove(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    await Api.removeDevice(host, name);
    // Reload so later saves don't write the removed device back to the store.
    await Api.loadPanels(host);
    host._showToast(t('Removed "{name}"').replace('{name}', _friendlyName(host, name)), "success");
  } catch (err) {
    host._showToast(err.message || t("Failed to remove device"), "error");
  }
  host.requestUpdate();
}

export async function onDeviceManagerAdd(host, e) {
  const device = e.detail?.device;
  if (!device) return;
  try {
    await Api.addDevice(host, { devices: [device] });
    // Reload so later saves include the new device instead of dropping it.
    await Api.loadPanels(host);
    host._showToast(t('Added "{name}"').replace('{name}', device.name), "success");
  } catch (err) {
    host._showToast(err.message || t("Failed to add device"), "error");
  }
  host.requestUpdate();
}

export async function onDeviceManagerScan(host, e) {
  const devices = e.detail?.devices;
  if (!devices || !devices.length) return;
  try {
    // Batch-add all discovered devices in a single API call.
    const batch = devices.map((d) => ({
      name: d.name || d.friendly_name,
      esphome_device_id: d.esphome_device_id || "",
      enabled: true,
    })).filter((d) => d.name && !(host._panels?.devices?.[d.name]));
    if (!batch.length) return;
    await Api.addDevice(host, { devices: batch });
    // Reload so later saves include the new devices instead of dropping them.
    await Api.loadPanels(host);
    host._showToast(t("Added {count} device(s)").replace("{count}", batch.length), "success");
  } catch (err) {
    host._showToast(err.message || t("Failed to add devices"), "error");
  }
  host.requestUpdate();
}

export async function onDeviceManagerUpdateTft(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    if (e.detail.file) host._showToast(t("Uploading local TFT file…"), "success");
    const result = e.detail.file
      ? await Api.uploadDeviceUpdate(host, name, "tft", e.detail.file)
      : await Api.updateDeviceTft(host, name, e.detail.version, e.detail.url);
    // Single-device failures are returned as HTTP errors and land in the
    // catch below; the `*` path aggregates failures server-side.  A body with
    // a 200 but an error update state is only possible by contract change on
    // the backend — still surface it instead of a false success toast.
    const update = result.update;
    if (update?.state === "error") {
      const message = update.last_error || t("TFT update failed");
      if (e.detail.file) e.target?._finishLocalUpload?.(message);
      host._showToast(message, "error");
      return;
    }
    const failed = result.failed || [];
    const count = result.devices_updated?.length || 0;
    if (failed.length) {
      const firstError = failed[0]?.error || t("TFT update failed");
      if (e.detail.file) e.target?._finishLocalUpload?.(firstError);
      host._showToast(
        t('TFT update failed for {count} device(s): {error}')
          .replace('{count}', failed.length)
          .replace('{error}', firstError),
        "error",
      );
      return;
    }
    if (e.detail.file) e.target?._finishLocalUpload?.();
    if (name === "*") {
      host._showToast(t('TFT update started for {count} device(s)').replace('{count}', count), "success");
    } else {
      host._showToast(t('TFT update started for "{name}"').replace('{name}', _friendlyName(host, name)), "success");
    }
  } catch (err) {
    if (e.detail.file) {
      e.target?._finishLocalUpload?.(err.message || t("Failed to install the TFT"));
    }
    host._showToast(err.message || t("Failed to install the TFT"), "error");
  }
}

export async function onDeviceManagerUpdateFirmware(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    if (e.detail.file) host._showToast(t("Uploading local firmware file…"), "success");
    const result = e.detail.file
      ? await Api.uploadDeviceUpdate(host, name, "firmware", e.detail.file)
      : await Api.updateDeviceFirmware(host, name, e.detail.version, e.detail.url);
    const update = result.update;
    if (update?.firmware_install_error) {
      if (e.detail.file) e.target?._finishLocalUpload?.(update.firmware_install_error);
      host._showToast(update.firmware_install_error, "error");
      return;
    }
    if (e.detail.file) e.target?._finishLocalUpload?.();
    host._showToast(
      t('Firmware update started for "{name}"').replace('{name}', _friendlyName(host, name)),
      "success",
    );
  } catch (err) {
    if (e.detail.file) {
      e.target?._finishLocalUpload?.(err.message || t("Failed to install firmware"));
    }
    host._showToast(err.message || t("Failed to install firmware"), "error");
  }
}
