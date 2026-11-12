/**
 * NSPanel HAUI - device actions.
 *
 * Adding, removing and enabling devices, and the TFT and firmware installs the
 * update surface asks for. Each function takes the editor (`host`) first.
 */
import { t } from './localize.js';

/**
 * Get the user-friendly display name for a device, falling back to the device key.
 * @param {any} host
 * @param {string} name  - device key
 * @returns {string}
 */
function _friendlyName(host, name) {
  return host._panels?.devices?.[name]?.friendly_name || name;
}

/** Enable or disable a device. @param {any} host @param {string} name */
export async function toggleDevice(host, name) {
  if (!name) return;
  await host.store.actions.toggleDevice(name);
  host.requestUpdate();
}

/** Remove a device from the hub, with its settings and panels. @param {any} host @param {string} name */
export async function removeDevice(host, name) {
  if (!name) return;
  const friendly = _friendlyName(host, name);
  try {
    await host.api.devices.remove(host.entryId, name);
    // Reload so later saves don't write the removed device back to the store.
    await host.store.actions.loadPanels();
    host._showToast(t('Removed "{name}"').replace('{name}', friendly), "success");
  } catch (err) {
    host._showToast(err.message || t("Failed to remove device"), "error");
  }
  host.requestUpdate();
}

/**
 * Add discovered devices to the hub in one request.
 *
 * @param {any} host
 * @param {Array<{ name?: string, friendly_name?: string, esphome_device_id?: string }>} devices
 * @returns {Promise<boolean>} whether devices were added
 */
export async function addDevices(host, devices) {
  const known = host.store.getState().devices.byName;
  const batch = (devices || []).map((device) => ({
    name: device.name || device.friendly_name,
    esphome_device_id: device.esphome_device_id || "",
    enabled: true,
  })).filter((device) => device.name && !known[device.name]);
  if (!batch.length) return false;
  let added = false;
  try {
    await host.api.devices.add(host.entryId, batch);
    // Reload so later saves include the new devices instead of dropping them.
    await host.store.actions.loadPanels();
    host._showToast(batch.length === 1
      ? t('Added "{name}"').replace('{name}', batch[0].name)
      : t("Added {count} device(s)").replace("{count}", String(batch.length)), "success");
    added = true;
  } catch (err) {
    host._showToast(err.message || (batch.length === 1 ? t("Failed to add device") : t("Failed to add devices")), "error");
  }
  host.requestUpdate();
  return added;
}

/** Install a TFT the update surface chose (release, URL or local file). */
export async function installTft(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    if (e.detail.file) host._showToast(t("Uploading local TFT file…"), "success");
    const result = e.detail.file
      ? await host.api.updates.upload(host.entryId, name, "tft", e.detail.file)
      : await host.api.updates.installTft(host.entryId, name, e.detail.version, e.detail.url);
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

/** Install a firmware the update surface chose (release, URL or local file). */
export async function installFirmware(host, e) {
  const name = e.detail?.name;
  if (!name) return;
  try {
    if (e.detail.file) host._showToast(t("Uploading local firmware file…"), "success");
    const result = e.detail.file
      ? await host.api.updates.upload(host.entryId, name, "firmware", e.detail.file)
      : await host.api.updates.installFirmware(host.entryId, name, e.detail.version, e.detail.url);
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
