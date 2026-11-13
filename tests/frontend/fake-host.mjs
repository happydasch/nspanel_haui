// Fake editor host and backend for testing the editor's state handling.
//
// The host is a real store-backed facade: the same store the shell uses owns
// the state, and the `_` fields below mirror it so existing assertions on the
// editor's properties keep their meaning.

import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { createStore, devicesFromStore } from '../../custom_components/nspanel_haui/frontend/store/store.js';
import * as Crud from '../../custom_components/nspanel_haui/frontend/crud.js';

export function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

/** In-memory storage for tests that do not inject their own. */
function testStorage() {
  const memory = new Map();
  return {
    read: (key, fallback) => memory.get(key) ?? fallback,
    write: (key, value) => memory.set(key, String(value)),
  };
}

/**
 * Build a host whose `hass.fetchWithAuth` answers from `respond(method, path, opts)`.
 * Every request is recorded in `host.calls` as "METHOD /path" and its full URL in `host.urls`.
 */
export function makeHost(panels, respond, { loadDeviceConfig, storage } = {}) {
  const calls = [];
  const urls = [];
  const toasts = [];
  const api = createApiClient(() => host.hass);
  const store = createStore({
    client: api,
    storage: storage || testStorage(),
    onToast: (message, type) => toasts.push([type, message]),
  });

  const host = {
    entryId: 'entry1',
    _panels: panels,
    _selectedDevice: Object.keys(panels.devices)[0],
    _deviceConfig: null,
    _deviceStatuses: {},
    _deviceStatus: null,
    _deviceStatusError: null,
    _panelTypes: [],
    _itemListData: {},
    _saving: false,
    _notifications: [],
    _toast: null,
    toasts,
    calls,
    urls,
    api,
    store,
    hass: {
      language: 'en',
      locale: { language: 'en' },
      async fetchWithAuth(url, opts = {}) {
        const method = opts.method || 'GET';
        const path = url.split('?')[0];
        calls.push(`${method} ${path}`);
        urls.push(url);
        return respond(method, path, opts);
      },
    },
    _showToast(msg, kind) { store.actions.showToast(msg, kind); },
    _loadDeviceConfig(name) {
      if (loadDeviceConfig) loadDeviceConfig(this, name);
      else this._deviceConfig = store.selectors.configFor(name);
    },
    _devicePanels() { return store.selectors.devicePanels(); },
    _savePanels(nextPanels, message, deviceName) {
      return Crud.savePanels(this, nextPanels, message, deviceName);
    },
    _saveDeviceConfig(config, message, deviceName) {
      return Crud.saveDeviceConfig(this, config, message, deviceName);
    },
    _selectDevice(name) { store.actions.selectDevice(name); },
    requestUpdate() {},
  };

  store.setState((current) => ({
    ...current,
    hub: {
      ...current.hub,
      entryId: 'entry1',
      loading: false,
      systemPanels: panels.system_panels || [],
      themes: panels.themes || {},
    },
    devices: devicesFromStore(panels, current.devices),
  }));

  let lastConfig = null;
  const sync = () => {
    const state = store.getState();
    host._panels = {
      device_order: [...state.devices.order],
      themes: state.hub.themes,
      system_panels: state.hub.systemPanels,
      devices: Object.fromEntries(state.devices.order.map((name) => {
        const device = state.devices.byName[name];
        return [name, {
          friendly_name: device.friendlyName,
          config: device.config,
          panels: device.panels,
        }];
      })),
    };
    host._selectedDevice = state.devices.selected;
    const config = state.devices.selected
      ? store.selectors.configFor(state.devices.selected)
      : null;
    if (config !== lastConfig) {
      host._deviceConfig = config;
      lastConfig = config;
    }
    host._deviceStatuses = store.selectors.statuses();
    host._deviceStatus = store.selectors.selectedStatus();
    host._deviceStatusError = state.hub.statusError;
    host._panelTypes = state.hub.panelTypes;
    host._notifications = state.notifications;
    host._saving = state.hub.saving;
    host._toast = state.ui.toast;
    host._loading = state.hub.loading;
  };
  store.subscribe(sync);
  sync();

  return host;
}
