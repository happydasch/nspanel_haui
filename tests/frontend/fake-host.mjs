// Fake editor host and backend for testing the editor's state handling.

export function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

/**
 * Build a host whose `hass.fetchWithAuth` answers from `respond(method, path, opts)`.
 * Every request is recorded in `host.calls` as "METHOD /path" and its full URL in `host.urls`.
 */
export function makeHost(panels, respond, { loadDeviceConfig } = {}) {
  const calls = [];
  const urls = [];
  return {
    entryId: 'entry1',
    _panels: panels,
    _selectedDevice: Object.keys(panels.devices)[0],
    _deviceConfig: null,
    _panelTypes: [],
    _itemListData: {},
    _saving: false,
    toasts: [],
    calls,
    urls,
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
    _showToast(msg, kind) { this.toasts.push([kind, msg]); },
    _loadDeviceConfig(name) { loadDeviceConfig?.(this, name); },
    _devicePanels() { return this._panels.devices[this._selectedDevice]?.panels || []; },
    requestUpdate() {},
  };
}
