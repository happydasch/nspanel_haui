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
/** @typedef {import('./types.js').PanelStore} PanelStore *//** @typedef {import('./types.js').PanelConfig} PanelConfig */

/** @typedef {import('./types.js').PanelTypeDescriptor} PanelTypeDescriptor */
/** @typedef {import('./types.js').PanelTemplate} PanelTemplate */
/** @typedef {import('./types.js').DeviceStatus} DeviceStatus */
/** @typedef {import('./types.js').Notification} Notification */
/** @typedef {import('./types.js').TftReleases} TftReleases */
/** @typedef {import('./types.js').FirmwareReleases} FirmwareReleases */
/** @typedef {import('./types.js').ThemesResponse} ThemesResponse */
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
      // A refused panel save names the fields that break a rule; the editor marks them.
      throw Object.assign(new Error(error.message || failMessage),
        Array.isArray(error.errors) ? { errors: error.errors } : {});
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
       * @param {string} name
       * @param {PanelConfig[]} panels
       * @returns {Promise<Object>}
       */
      async saveDevice(entryId, name, panels) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/panels/${entryId}/${encodeURIComponent(name)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ panels }),
          },
          t('Failed to save panels'),
        );
      },
    },

    devices: {
      /**
       * @param {string} entryId
       * @param {string} name
       */
      settings(entryId, name) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/devices/${entryId}/${encodeURIComponent(name)}`,
          undefined,
          t('Failed to load device settings'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string} name
       * @param {Object} config
       */
      saveSettings(entryId, name, config) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/devices/${entryId}/${encodeURIComponent(name)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config }),
          },
          t('Failed to save device settings'),
        );
      },

      /**
       * @param {string} entryId
       * @param {string[]} deviceOrder
       */
      reorder(entryId, deviceOrder) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/device_order/${entryId}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_order: deviceOrder }),
          },
          t('Failed to save the device order'),
        );
      },

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
       * The hub's update rollout (idle when none ran since Home Assistant started).
       * @param {string} entryId
       * @returns {Promise<Record<string, any>>}
       */
      async rollout(entryId) {
        requireEntry(entryId);
        const result = await request(`/api/nspanel_haui/rollout/${entryId}`, undefined, t('Fetch failed'));
        return result.rollout;
      },

      /**
       * Install the offered updates one device at a time on the hub.
       * @param {string} entryId
       * @returns {Promise<Record<string, any>>} the rollout
       */
      async startRollout(entryId) {
        requireEntry(entryId);
        const result = await request(
          `/api/nspanel_haui/rollout/${entryId}`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) },
          t('Failed to start the update rollout'),
        );
        return result.rollout;
      },

      /**
       * Cancel one queued device of the rollout, or every queued device.
       * @param {string} entryId
       * @param {string} [device]
       * @returns {Promise<Record<string, any>>} the rollout
       */
      async cancelRollout(entryId, device) {
        requireEntry(entryId);
        const path = device ? `${entryId}/${encodeURIComponent(device)}` : entryId;
        const result = await request(
          `/api/nspanel_haui/rollout/${path}`,
          { method: 'DELETE' },
          t('Failed to cancel the update rollout'),
        );
        return result.rollout;
      },

      /**
       * Start, defer or skip a device's scheduled automatic firmware install.
       * @param {string} entryId
       * @param {string} device
       * @param {'install_now'|'defer'|'skip'} action
       * @param {number} [seconds] - for defer: 3600 or 86400
       */
      control(entryId, device, action, seconds) {
        requireEntry(entryId);
        /** @type {Record<string, unknown>} */
        const body = { device, action };
        if (seconds !== undefined) body.seconds = seconds;
        return request(
          `/api/nspanel_haui/update_control/${entryId}`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
          t('Failed to change the scheduled update'),
        );
      },

      /**
       * The hub's automatic update policy.
       * @param {string} entryId
       * @returns {Promise<Record<string, any>>}
       */
      async policy(entryId) {
        requireEntry(entryId);
        const result = await request(
          `/api/nspanel_haui/update_policy/${entryId}`,
          undefined,
          t('Failed to load the update policy'),
        );
        return result.policy;
      },

      /**
       * Save the hub's automatic update policy; every device follows it unless it overrides it.
       * @param {string} entryId
       * @param {Record<string, any>} policy
       * @returns {Promise<Record<string, any>>} the stored policy
       */
      async savePolicy(entryId, policy) {
        requireEntry(entryId);
        const result = await request(
          `/api/nspanel_haui/update_policy/${entryId}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ policy }),
          },
          t('Failed to save the update policy'),
        );
        return result.policy;
      },

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

      /**
       * The starter templates of the Add panel catalog.
       * @param {string} lang
       * @returns {Promise<PanelTemplate[]>}
       */
      panelTemplates(lang) {
        return request(
          `/api/nspanel_haui/panel_templates?language=${encodeURIComponent(lang)}`,
          undefined,
          t('Failed to load panel templates'),
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
       * @returns {Promise<ThemesResponse>}
       */
      themes(entryId) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/themes/${entryId}`,
          undefined,
          t('Unable to load themes.'),
        );
      },

      /**
       * @param {string} entryId
       * @param {{ version: number, themes: Object<string, import('./types.js').Theme> }} body
       */
      saveThemes(entryId, body) {
        requireEntry(entryId);
        return request(
          `/api/nspanel_haui/themes/${entryId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
          t('Unable to save themes. Check for duplicate names or themes in use.'),
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
       * @param {({ panel: Object } | { key: string }) & { kwargs?: Object }} target
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
