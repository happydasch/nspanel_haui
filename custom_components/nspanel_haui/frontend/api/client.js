// @ts-check
/**
 * NSPanel HAUI - the editor's typed API client.
 *
 * One namespaced object owns every REST and WebSocket call the editor makes.
 * `getHass` is a callback so the client never holds a stale `hass` after Home
 * Assistant replaces it.
 */

import { getLanguage, t } from '../localize.js';

/** @typedef {import('./types.js').Hass} Hass */
/** @typedef {import('./types.js').PanelStore} PanelStore */
/** @typedef {import('./types.js').PanelTypeDescriptor} PanelTypeDescriptor */
/** @typedef {import('./types.js').DeviceStatus} DeviceStatus */
/** @typedef {import('./types.js').Notification} Notification */
/** @typedef {import('./types.js').TftReleases} TftReleases */
/** @typedef {import('./types.js').FirmwareReleases} FirmwareReleases */
/** @typedef {import('./types.js').ColorSchemesResponse} ColorSchemesResponse */
/** @typedef {import('./types.js').PanelRender} PanelRender */
/** @typedef {import('./types.js').UpdateResult} UpdateResult */

const DEFAULT_REQUEST_TIMEOUT_MS = 20000;

/** @typedef {ReturnType<typeof createApiClient>} ApiClient */

/**
 * @param {() => Hass|null|undefined} getHass
 */
export function createApiClient(getHass) {  /** @returns {Hass} */
  function hass() {
    const value = getHass();
    if (!value) throw new Error(t('No Home Assistant connection'));
    return value;
  }

  /**
   * fetchWithAuth + error unwrapping. Returns the Response on success; throws
   * the server's message (or the given translated fallback) otherwise.
   *
   * @param {string} url
   * @param {RequestInit} [options]
   * @param {string} [failMessage]
   * @param {number} [requestTimeoutMs]
   * @returns {Promise<Response>}
   */
  async function requestRaw(
    url,
    options = {},
    failMessage = t('Request failed'),
    requestTimeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
  ) {
    const controller = new AbortController();
    // Ref'd setTimeout (not AbortSignal.timeout, whose timer is unref'd in some
    // JS engines and never fires in an otherwise idle event loop): a request that
    // never settles must abort and surface instead of hanging silently.  The
    // timer is cleared once the fetch settles so fast requests leave nothing
    // behind.
    const timer = setTimeout(
      () => controller.abort(new DOMException('Request timed out', 'TimeoutError')),
      requestTimeoutMs,
    );
    let response;
    try {
      response = await hass().fetchWithAuth(url, { ...options, signal: controller.signal });
    } catch (err) {
      if (err && (err.name === 'TimeoutError' || err.name === 'AbortError')) {
        throw new Error(
          t('Request timed out; the device may be busy. Check the Home Assistant logs'),
        );
      }
      throw err;
    } finally {
      if (timer) clearTimeout(timer);
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: `HTTP ${response.status}` }));
      throw new Error(error.message || failMessage);
    }
    return response;
  }

  /**
   * @param {string} url
   * @param {RequestInit} [options]
   * @param {string} [failMessage]
   * @returns {Promise<any>}
   */
  async function request(url, options, failMessage) {
    return (await requestRaw(url, options, failMessage)).json();
  }

  /** @param {string} entryId */
  function requireEntry(entryId) {
    if (!entryId) throw new Error(t('No config entry selected'));
  }

  const api = {
    /** The HAUI language code for the current Home Assistant language. */
    language() {
      return getLanguage(hass());
    },

    /** The current Home Assistant websocket connection, if any. */
    connection() {
      return getHass()?.connection ?? null;
    },

    entries: {
      /**
       * The nspanel_haui config entries.
       * @returns {Promise<Array<{ entry_id: string, domain: string }>>}
       */
      async list() {
        const all = await hass().callWS({ type: 'config_entries/get' });
        return (all || []).filter((entry) => entry.domain === 'nspanel_haui');
      },
    },

    panels: {
      /**
       * @param {string} entryId
       * @param {string} lang
       * @returns {Promise<PanelStore>}
       */
      async load(entryId, lang) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/panels/${entryId}?language=${encodeURIComponent(lang)}`,
          undefined,
          t('Failed to load panels'),
        );
      },

      /**
       * @param {string} entryId
       * @param {PanelStore} store
       * @returns {Promise<Object>}
       */
      async save(entryId, store) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/panels/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(store),
          },
          t('Save failed'),
        );
      },
    },

    devices: {
      /** @param {string} entryId */
      scan(entryId) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/devices/${entryId}`,
          undefined,
          t('Failed to scan for devices'),
        );
      },

      /**
       * @param {string} entryId
       * @param {Array<{ name: string, esphome_device_id?: string, enabled?: boolean }>} devices
       */
      add(entryId, devices) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/devices/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ devices }),
          },
          t('Failed to add device'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} name
       */
      remove(entryId, name) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/devices/${entryId}?name=${encodeURIComponent(name)}`,
          { method: 'DELETE' },
          t('Failed to remove device'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       */
      refreshDisplay(entryId, device) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/refresh_display/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device }),
          },
          t('Failed to refresh display'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       */
      resetInteraction(entryId, device) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/reset_interaction/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device }),
          },
          t('Failed to reset interaction timer'),
        );
      },
    },

    status: {
      /**
       * @param {string} entryId
       * @param {string} [device]
       * @returns {Promise<DeviceStatus|{devices: Object<string, DeviceStatus>}>}
       */
      get(entryId, device) {
        requireEntry(entryId);
        const query = device ? `?device=${encodeURIComponent(device)}` : '';
        return request(
          `/api/nspanel_haui/status/${entryId}${query}`,
          undefined,
          t('Fetch failed'),
        );
      },

      /**
       * @param {string} entryId
       * @returns {Promise<Object<string, DeviceStatus>>}
       */
      async getAll(entryId) {
        const result = /** @type {any} */ (await api.status.get(entryId));
        const devices = result?.devices;
        if (!devices || typeof devices !== 'object' || Array.isArray(devices)) {
          throw new Error(t('Invalid device status response'));
        }
        return devices;
      },
    },

    notifications: {
      /**
       * @param {string} entryId
       * @returns {Promise<Notification[]>}
       */
      list(entryId) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/notifications/${entryId}`,
          undefined,
          t('Failed to load notifications'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       * @param {string} id
       */
      dismiss(entryId, device, id) {
        requireEntry(entryId);
        const query = new URLSearchParams({ device, id });
        return request(
          `/api/nspanel_haui/notifications/${entryId}?${query}`,
          { method: 'DELETE' },
          t('Failed to dismiss notification'),
        );
      },

      /**
       * Subscribe to the hub's notification event.
       * @param {(notification: Notification) => void} onNotification
       * @returns {Promise<() => void>}
       */
      subscribe(onNotification) {
        return hass().connection.subscribeEvents(
          (event) => onNotification(event?.data),
          'nspanel_haui.notification',
        );
      },
    },

    updates: {
      /**
       * @param {string} entryId
       * @param {string} device
       * @param {string} [version]
       * @param {string} [url]
       * @returns {Promise<UpdateResult>}
       */
      installTft(entryId, device, version, url) {
        requireEntry(entryId);
        /** @type {Record<string, string>} */
        const body = { device };
        if (version) body.version = version;
        if (url) body.url = url;
        return request(
          `/api/nspanel_haui/update_tft/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
          t('Failed to install the TFT'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       * @param {string} [version]
       * @param {string} [url]
       * @returns {Promise<UpdateResult>}
       */
      installFirmware(entryId, device, version, url) {
        requireEntry(entryId);
        /** @type {Record<string, string>} */
        const body = { device };
        if (version) body.version = version;
        if (url) body.url = url;
        return request(
          `/api/nspanel_haui/update_firmware/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
          t('Failed to install firmware'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       * @param {"tft"|"firmware"} kind
       * @param {File} file
       * @returns {Promise<UpdateResult>}
       */
      async upload(entryId, device, kind, file) {
        requireEntry(entryId);
        const query = new URLSearchParams({ device, filename: file.name });
        const response = await requestRaw(
          `/api/nspanel_haui/update_upload/${entryId}/${kind}?${query}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/octet-stream' },
            body: file,
          },
          t('Failed to upload the update file'),
          300000,
        );
        return response.json();
      },

      /**
       * @param {string} entryId
       * @param {string} device
       * @returns {Promise<TftReleases>}
       */
      tftReleases(entryId, device) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/tft_releases/${entryId}?device=${encodeURIComponent(device)}`,
          undefined,
          t('Failed to load the TFT releases'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       * @returns {Promise<FirmwareReleases>}
       */
      firmwareReleases(entryId, device) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/firmware_releases/${entryId}?device=${encodeURIComponent(device)}`,
          undefined,
          t('Failed to load the firmware releases'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} device
       */
      check(entryId, device) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/check_update/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device }),
          },
          t('Failed to check for updates'),
        );
      },

      /**
       * The prebuilt firmware download of the latest stable release.
       * @returns {Promise<{ url: string|null, version: string|null }>}
       */
      firmwareDownload() {
        return request(
          '/api/nspanel_haui/firmware',
          { method: 'GET' },
          t('Failed to load the firmware link'),
        );
      },
    },

    editor: {
      /**
       * @param {string} lang
       * @returns {Promise<Object<string, string>>}
       */
      translations(lang) {
        return request(
          `/api/nspanel_haui/translations/${encodeURIComponent(lang)}?flat=1`,
          undefined,
          t('Failed to load translations'),
        );
      },

      /**
       * @param {string} lang
       * @returns {Promise<PanelTypeDescriptor[]>}
       */
      panelTypes(lang) {
        return request(
          `/api/nspanel_haui/panel_types?language=${encodeURIComponent(lang)}`,
          undefined,
          t('Failed to load panel types'),
        );
      },

      /** @returns {Promise<Object<string, number>>} */
      colorDefaults() {
        return request(
          '/api/nspanel_haui/color_defaults',
          undefined,
          t('Failed to load color defaults'),
        );
      },

      /**
       * @param {string} entryId
       * @returns {Promise<ColorSchemesResponse>}
       */
      colorSchemes(entryId) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/color_schemes/${entryId}`,
          undefined,
          t('Unable to load color schemes.'),
        );
      },

      /**
       * @param {string} entryId
       * @param {{ version: number, schemes: Object<string, import('./types.js').ColorScheme> }} body
       */
      saveColorSchemes(entryId, body) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/color_schemes/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
          t('Unable to save color schemes. Check for duplicate names or schemes in use.'),
        );
      },

      /**
       * @param {string} [query]
       * @returns {Promise<string[]>}
       */
      icons(query = '') {
        const search = query ? `?q=${encodeURIComponent(query)}` : '';
        return request(
          `/api/nspanel_haui/icons${search}`,
          undefined,
          t('Failed to load icons'),
        );
      },
    },

    preview: {
      /**
       * @param {string} entryId
       * @param {string} device
       * @param {{ panel: Object } | { key: string }} target
       * @returns {Promise<PanelRender>}
       */
      render(entryId, device, target) {
        return hass().connection.sendMessagePromise({
          type: 'nspanel_haui/virtual_panel/render',
          entry_id: entryId,
          device,
          ...target,
        });
      },
    },

    ha: {
      /**
       * Subscribe to HA's `render_template` command.
       * @param {string} template
       * @param {(message: Object) => void} onChange
       * @returns {Promise<() => void>}
       */
      renderTemplate(template, onChange) {
        return hass().connection.subscribeMessage(
          onChange,
          { type: 'render_template', template, report_errors: true },
          { resubscribe: false },
        );
      },
    },

    yaml: {
      /**
       * @param {string} entryId
       * @param {string} device
       * @returns {Promise<string>}
       */
      async export(entryId, device) {
        requireEntry(entryId);
        const response = await requestRaw(
          `/api/nspanel_haui/yaml/${entryId}?device=${encodeURIComponent(device)}`,
          undefined,
          t('Export failed'),
        );
        return response.text();
      },

      /**
       * @param {string} entryId
       * @param {string} device
       * @param {string} text
       * @returns {Promise<{ device: string }>}
       */
      import(entryId, device, text) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/yaml/${entryId}?device=${encodeURIComponent(device)}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-yaml' },
            body: text,
          },
          t('Import failed'),
        );
      },
    },
  };

  return api;
}
