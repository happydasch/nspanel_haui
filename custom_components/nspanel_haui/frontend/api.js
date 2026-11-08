import { getLanguage, t } from './localize.js';
/**
 * NSPanel HAUI - REST API client for the editor.
 *
 * Single hub: loadEntries picks the first nspanel_haui entry and loads its
 * panels. The rest wraps the hub's REST views (status, YAML, devices, display
 * refresh, TFT/firmware installs, update checks).
 */

export async function loadEntries(host) {
  if (!host.hass) return;
  try {
    const all = await host.hass.callWS({ type: "config_entries/get" });
    const entries = (all || []).filter((e) => e.domain === "nspanel_haui");
    host._entriesError = null;
    if (entries.length && !host.entryId) {
      host.entryId = entries[0].entry_id;
      await host._load();
    } else if (!entries.length) {
      host._loading = false;
    }
  } catch (e) {
    console.error("Failed to load config entries:", e);
    // Not "no integration configured": the list itself could not be read.
    // The editor renders _entriesError as a card, so no toast here.
    host._entriesError = e.message || t("Failed to load the integration list");
    host._loading = false;
  }
}

export async function loadPanels(host, { keepLoading = false } = {}) {
  if (!host.entryId || !host.hass) {
    host._loading = false;
    return;
  }
  host._loading = true;
  try {
    const lang = getLanguage(host.hass);
    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/panels/${host.entryId}?language=${encodeURIComponent(lang)}`
    );
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    host._panels = await resp.json();
    const devices = Object.keys(host._panels.devices || {});
    // Preserve the currently selected device if it still exists
    if (host._selectedDevice && devices.includes(host._selectedDevice)) {
      // Keep current selection
    } else {
      host._selectedDevice = devices.length ? devices[0] : null;
    }
    host._deviceStatuses = Object.fromEntries(
      Object.entries(host._deviceStatuses || {}).filter(([name]) => devices.includes(name))
    );
    if (host._selectedDevice) host._loadDeviceConfig(host._selectedDevice);
    if (
      !keepLoading &&
      devices.some((name) => !Object.hasOwn(host._deviceStatuses, name))
    ) {
      await loadDeviceStatuses(host);
    }
  } catch (e) {
    console.error("Failed to load panels:", e);
    host._showToast(t("Failed to load panels"), "error");
  }
  if (!keepLoading) host._loading = false;
}

/** Load and cache the status snapshot for every configured device. */
export async function loadDeviceStatuses(host) {
  if (!host.entryId || !host.hass) return null;
  try {
    const resp = await host.hass.fetchWithAuth(`/api/nspanel_haui/status/${host.entryId}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    const statuses = result?.devices;
    if (!statuses || typeof statuses !== "object" || Array.isArray(statuses)) {
      throw new Error("Invalid device status response");
    }
    host._deviceStatuses = { ...(host._deviceStatuses || {}), ...statuses };
    const selected = host._deviceStatuses[host._selectedDevice];
    if (selected) {
      host._deviceStatus = selected;
      host._deviceStatusError = null;
    }
    return host._deviceStatuses;
  } catch (e) {
    console.error("Failed to load device statuses:", e);
    host._deviceStatusError = e.message || t("Fetch failed");
    return null;
  }
}

export async function loadPanelTypes(host) {
  if (!host.hass) return;
  try {
    const lang = getLanguage(host.hass);
    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/panel_types?language=${encodeURIComponent(lang)}`
    );
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    host._panelTypes = await resp.json();
  } catch (e) {
    console.error("Failed to load panel types:", e);
    host._showToast(t("Failed to load panel types"), "error");
  }
}
export async function loadStatus(host) {
  if (!host.entryId || !host.hass) {
    host._deviceStatus = null;
    host._deviceStatusError = t("No device selected");
    return;
  }
  // Request status for the currently-selected device so the backend
  // returns a flat response (no {devices: {...}} wrapper).
  const deviceKey = host._selectedDevice || "";
  let status = null;
  let error = null;
  try {
    const qs = deviceKey ? `?device=${encodeURIComponent(deviceKey)}` : "";
    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/status/${host.entryId}${qs}`
    );
    if (resp.ok) {
      status = await resp.json();
      // The unfiltered response contains every device; cache it and use the
      // selected device's entry when one was requested.
      if (status.devices && typeof status.devices === "object") {
        const statuses = status.devices;
        host._deviceStatuses = { ...(host._deviceStatuses || {}), ...statuses };
        const names = Object.keys(statuses);
        status = deviceKey
          ? statuses[deviceKey] || null
          : names.length ? statuses[names[0]] : {};
      }
    } else {
      error = `HTTP ${resp.status}`;
    }
  } catch (e) {
    error = e.message || t("Fetch failed");
  }
  // The user may have switched devices while this request was in flight.
  if ((host._selectedDevice || "") !== deviceKey) return;
  if (deviceKey && status) {
    host._deviceStatuses = { ...(host._deviceStatuses || {}), [deviceKey]: status };
  }
  host._deviceStatus = status;
  host._deviceStatusError = error;
}

/**
 * Export the selected device's config as a YAML blob and download it.
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceKey  - the internal device name
 */
export async function exportDeviceYaml(host, deviceKey) {
  if (!host.entryId || !deviceKey) return;
  try {
    const resp = await requestRaw(
      host,
      `/api/nspanel_haui/yaml/${host.entryId}?device=${encodeURIComponent(deviceKey)}`,
      undefined,
      t("Export failed")
    );
    const yamlText = await resp.text();
    downloadBlob(yamlText, `${deviceKey}.yaml`, "application/x-yaml");
  } catch (e) {
    console.error("Export failed:", e);
    throw e;
  }
}

/**
 * Import a YAML file for the selected device.
 *
 * Opens a file picker, reads the contents, POSTs to the YAML endpoint,
 * then refreshes the panel store.
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceKey  - the internal device name
 * @returns {Promise<string>}  - the toast message on success
 */
export async function importDeviceYaml(host, deviceKey) {
  if (!host.entryId || !deviceKey) return;
  const file = await pickYamlFile();
  if (!file) return;
  const yamlText = await file.text();

  const result = await request(
    host,
    `/api/nspanel_haui/yaml/${host.entryId}?device=${encodeURIComponent(deviceKey)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-yaml" },
      body: yamlText,
    },
    t("Import failed")
  );
  // Reload panels to reflect imported data
  await loadPanels(host);
  return t('Imported YAML for "{name}"').replace('{name}', result.device);
}

/* ── helpers ─────────────────────────────────────────────────────────────── */

/**
 * Create a downloadable file in the browser.
 */
function downloadBlob(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Open a file picker restricted to YAML files and return the selected File.
 * @returns {Promise<File|null>}
 */
function pickYamlFile() {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".yaml,.yml";
    input.onchange = () => {
      const file = input.files && input.files[0];
      resolve(file || null);
    };
    input.click();
  });
}

/**
 * fetchWithAuth + error unwrapping. Returns the Response on success; throws
 * the server's message (or the given translated fallback) otherwise.
 */
const DEFAULT_REQUEST_TIMEOUT_MS = 20000;

async function requestRaw(host, url, options, failMessage, requestTimeoutMs) {
  const controller = new AbortController();
  const timeoutMs = requestTimeoutMs ?? host._apiTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS;
  // Ref'd setTimeout (not AbortSignal.timeout, whose timer is unref'd in some
  // JS engines and never fires in an otherwise idle event loop): a request that
  // never settles must abort and surface instead of hanging silently.  The
  // timer is cleared once the fetch settles so fast requests leave nothing
  // behind.
  const timer = options?.signal
    ? null
    : setTimeout(
        () => controller.abort(new DOMException("Request timed out", "TimeoutError")),
        timeoutMs,
      );
  const signal = options?.signal || controller.signal;
  let resp;
  try {
    resp = await host.hass.fetchWithAuth(url, { ...options, signal });
  } catch (err) {
    if (err && (err.name === "TimeoutError" || err.name === "AbortError")) {
      throw new Error(
        t("Request timed out; the device may be busy. Check the Home Assistant logs")
      );
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || failMessage);
  }
  return resp;
}

async function request(host, url, options, failMessage) {
  return (await requestRaw(host, url, options, failMessage)).json();
}

/* ── device management ─────────────────────────────────────────────────── */

/**
 * Scan for discoverable ESPHome HAUI devices.
 *
 * GET /api/nspanel_haui/devices/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @returns {Promise<{ devices: Array<{ name: string, friendly_name: string, esphome_device_id: string }> }>}
 */
export async function scanDevices(host) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(host, `/api/nspanel_haui/devices/${host.entryId}`, undefined, t("Failed to scan for devices"));
}

/**
 * Add a new device to the config entry.
 *
 * POST /api/nspanel_haui/devices/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {{ name: string, esphome_device_id?: string }} device
 * @returns {Promise<{ status: string }>}
 */
export async function addDevice(host, device) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(host, `/api/nspanel_haui/devices/${host.entryId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(device),
    }, t("Failed to add device"));
}

/**
 * Remove a device from the hub, together with its settings and panels.
 *
 * DELETE /api/nspanel_haui/devices/{entryId}?name={name}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} name - device name to remove
 * @returns {Promise<{ status: string }>}
 */
export async function removeDevice(host, name) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(host, `/api/nspanel_haui/devices/${host.entryId}?name=${encodeURIComponent(name)}`,
    { method: "DELETE" }, t("Failed to remove device"));
}


/**
 * Trigger a display refresh for one device.
 *
 * POST /api/nspanel_haui/refresh_display/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceName - device name
 * @returns {Promise<{ status: string, devices_updated: string[] }>}
 */
export async function refreshDeviceDisplay(host, deviceName) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(host, `/api/nspanel_haui/refresh_display/${host.entryId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device: deviceName }),
    }, t("Failed to refresh display"));
}

/**
 * Reset the firmware's interaction timer for one device.
 *
 * POST /api/nspanel_haui/reset_interaction/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceName - device name
 */
export async function resetDeviceInteractionTimer(host, deviceName) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(host, `/api/nspanel_haui/reset_interaction/${host.entryId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device: deviceName }),
    }, t("Failed to reset interaction timer"));
}

/**
 * Resolve the prebuilt firmware (.bin) download link of the latest stable release.
 *
 * GET /api/nspanel_haui/firmware
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @returns {Promise<{ url: string|null, version: string|null }>}
 */
export async function getFirmwareDownload(host) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(host, `/api/nspanel_haui/firmware`, {
    method: "GET",
  }, t("Failed to load the firmware link"));
}

/**
 * Trigger a TFT install on one or all devices.
 *
 * POST /api/nspanel_haui/update_tft/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceName - device name, or "*" for all devices
 * @param {string} [version] - release version (default: the firmware's required TFT version)
 * @param {string} [url] - URL of a .tft file instead of a release (single device only)
 * @returns {Promise<{ status: string, devices_updated: string[] }>}
 */
export async function updateDeviceTft(host, deviceName, version, url) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  const body = { device: deviceName };
  if (version) body.version = version;
  if (url) body.url = url;
  return request(host, `/api/nspanel_haui/update_tft/${host.entryId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }, t("Failed to install the TFT"));
}

/**
 * List the GitHub releases a device's TFT can be installed from.
 *
 * GET /api/nspanel_haui/tft_releases/{entryId}?device={deviceName}
 *
 * @param {{ entryId: string, hass: Object }} host
 * @param {string} deviceName
 * @returns {Promise<{ releases: string[], required: string|null, error: string|null }>}
 */
export async function getTftReleases(host, deviceName) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(
    host,
    `/api/nspanel_haui/tft_releases/${host.entryId}?device=${encodeURIComponent(deviceName)}`,
    undefined,
    t("Failed to load the TFT releases"),
  );
}

/**
 * Install firmware on one or all devices.
 *
 * POST /api/nspanel_haui/update_firmware/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceName - device name, or "*" for all devices
 * @param {string} [version] - release to install (default: the update HA offers)
 * @param {string} [url] - URL of a firmware OTA image instead (single device only)
 * @returns {Promise<{ status: string, devices_updated: string[], update?: Object }>}
 */
export async function updateDeviceFirmware(host, deviceName, version, url) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  const body = { device: deviceName };
  if (version) body.version = version;
  if (url) body.url = url;
  return request(host, `/api/nspanel_haui/update_firmware/${host.entryId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, t("Failed to install firmware"));
}

/**
 * Upload a local TFT or OTA image and start its install on one device.
 *
 * POST /api/nspanel_haui/update_upload/{entryId}/{kind}?device=...&filename=...
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceName
 * @param {"tft"|"firmware"} kind
 * @param {File} file
 * @returns {Promise<{ status: string, devices_updated: string[], update?: Object }>}
 */
export async function uploadDeviceUpdate(host, deviceName, kind, file) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  const query = new URLSearchParams({ device: deviceName, filename: file.name });
  const response = await requestRaw(
    host,
    `/api/nspanel_haui/update_upload/${host.entryId}/${kind}?${query}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: file,
    },
    t("Failed to upload the update file"),
    300000,
  );
  return response.json();
}

/**
 * List the GitHub releases whose firmware a device can install over the air.
 *
 * GET /api/nspanel_haui/firmware_releases/{entryId}?device={deviceName}
 *
 * @param {{ entryId: string, hass: Object }} host
 * @param {string} deviceName
 * @returns {Promise<{ releases: string[], error: string|null }>}
 */
export async function getFirmwareReleases(host, deviceName) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  return request(
    host,
    `/api/nspanel_haui/firmware_releases/${host.entryId}?device=${encodeURIComponent(deviceName)}`,
    undefined,
    t("Failed to load the firmware releases"),
  );
}
