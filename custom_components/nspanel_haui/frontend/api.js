import { getLanguage, t } from './localize.js';
/**
 * NSPanel HAUI - data loading helpers.
 * Extracted from panel-editor.js _loadEntries, _load, _loadPanelTypes methods.
 *
 * Simplified to single-hub: loadEntries picks the first nspanel_haui entry
 * and auto-loads panels. No multi-entry discovery or device scanning.
 */

export async function loadEntries(host) {
  if (!host.hass) return;
  try {
    const all = await host.hass.callWS({ type: "config_entries/get" });
    const entries = (all || []).filter((e) => e.domain === "nspanel_haui");
    if (entries.length && !host.entryId) {
      host.entryId = entries[0].entry_id;
      await host._load();
    } else if (!entries.length) {
      host._loading = false;
    }
  } catch (e) {
    console.error("Failed to load config entries:", e);
    host._loading = false;
  }
}

export async function loadPanels(host) {
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
    if (resp.ok) {
      host._panels = await resp.json();
      const devices = Object.keys(host._panels.devices || {});
      // Preserve the currently selected device if it still exists
      if (host._selectedDevice && devices.includes(host._selectedDevice)) {
        // Keep current selection
      } else {
        host._selectedDevice = devices.length ? devices[0] : null;
      }
      if (host._selectedDevice) host._loadDeviceConfig(host._selectedDevice);
    }
  } catch (e) {
    console.error("Failed to load panels:", e);
  }
  host._loading = false;
}

export async function loadPanelTypes(host) {
  if (!host.hass) return;
  try {
    const lang = getLanguage(host.hass);
    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/panel_types?language=${encodeURIComponent(lang)}`
    );
    if (resp.ok) {
      host._panelTypes = await resp.json();
    }
  } catch (e) {
    console.error("Failed to load panel types:", e);
  }
}
export async function loadStatus(host) {
  if (!host.entryId || !host.hass) {
    host._deviceStatus = null;
    host._deviceStatusError = t("No device selected");
    return;
  }
  try {
    // Request status for the currently-selected device so the backend
    // returns a flat response (no {devices: {...}} wrapper).
    const deviceKey = host._selectedDevice || "";
    const qs = deviceKey ? `?device=${encodeURIComponent(deviceKey)}` : "";
    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/status/${host.entryId}${qs}`
    );
    if (resp.ok) {
      let data = await resp.json();
      // When no device is selected the backend returns
      // {devices: {name: status, ...}}. Unwrap the first device.
      if (data.devices && typeof data.devices === "object") {
        const names = Object.keys(data.devices);
        data = names.length ? data.devices[names[0]] : {};
      }
      host._deviceStatus = data;
      host._deviceStatusError = null;
    } else {
      host._deviceStatus = null;
      host._deviceStatusError = `HTTP ${resp.status}`;
    }
  } catch (e) {
    host._deviceStatus = null;
    host._deviceStatusError = e.message || t("Fetch failed");
  }
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
    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/yaml/${host.entryId}?device=${encodeURIComponent(deviceKey)}`
    );
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
      throw new Error(err.message || t("Export failed"));
    }
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

  const resp = await host.hass.fetchWithAuth(
    `/api/nspanel_haui/yaml/${host.entryId}?device=${encodeURIComponent(deviceKey)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-yaml" },
      body: yamlText,
    }
  );

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || t("Import failed"));
  }

  const result = await resp.json();
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

/* ── device management ─────────────────────────────────────────────────── */

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
  const resp = await host.hass.fetchWithAuth(
    `/api/nspanel_haui/devices/${host.entryId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(device),
    }
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || t("Failed to add device"));
  }
  return resp.json();
}

/**
 * Remove a device from the config entry.
 *
 * DELETE /api/nspanel_haui/devices/{entryId}?name={name}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} name - device name to remove
 * @param {boolean} [keepConfig=false] - keep panel config in store
 * @returns {Promise<{ status: string, kept_config: boolean }>}
 */
export async function removeDevice(host, name, keepConfig = false) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  const resp = await host.hass.fetchWithAuth(
    `/api/nspanel_haui/devices/${host.entryId}?name=${encodeURIComponent(name)}`,
    {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keep_config: keepConfig }),
    }
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || t("Failed to remove device"));
  }
  return resp.json();
}

/**
 * Trigger display refresh on one or all devices.
 *
 * POST /api/nspanel_haui/update_display/{entryId}
 *
 * @param {import('./haui-editor.js').NSPanelEditor} host
 * @param {string} deviceName - device name, or "*" for all devices
 * @returns {Promise<{ status: string, devices_updated: string[] }>}
 */
export async function updateDeviceDisplay(host, deviceName) {
  if (!host.entryId || !host.hass) {
    throw new Error(t("No config entry selected"));
  }
  const resp = await host.hass.fetchWithAuth(
    `/api/nspanel_haui/update_display/${host.entryId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device: deviceName }),
    }
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || t("Failed to update display"));
  }
  return resp.json();
}

