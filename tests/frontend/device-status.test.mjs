import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import * as Api from '../../custom_components/nspanel_haui/frontend/api.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { startStatusPolling, stopStatusPolling } from '../../custom_components/nspanel_haui/frontend/device-info.js';
import '../../custom_components/nspanel_haui/frontend/dialogs/device-manager.js';
import { jsonResponse, makeHost } from './fake-host.mjs';
import { previewRenderKey } from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';

const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

function editor() {
  const host = Object.create(NSPanelEditor.prototype);
  Object.assign(host, {
    entryId: 'entry1',
    _loading: true,
    _panels: { devices: {} },
    _selectedDevice: null,
    _deviceStatuses: {},
    _deviceStatus: null,
    _deviceStatusError: null,
    _deviceConfig: null,
    _showToast() {},
  });
  return host;
}

/** Host whose /status responses stay pending until released via `host.pending`. */
function statusHost() {
  const pending = [];
  const host = makeHost(
    { devices: { kitchen: { config: {}, panels: [] }, office: { config: {}, panels: [] } } },
    (method, path) => {
      if (!path.startsWith('/api/nspanel_haui/status/')) throw new Error(`unexpected ${method} ${path}`);
      return new Promise((resolve) => pending.push(resolve));
    },
  );
  host.pending = pending;
  return host;
}

test('preview render keys change when cached device versions arrive', () => {
  const host = {
    entryId: 'entry1',
    _selectedDevice: 'kitchen',
    _deviceConfig: {},
    _deviceStatuses: {},
    _devicePanels: () => [],
  };
  const before = previewRenderKey(host);
  host._deviceStatuses.kitchen = {
    device_info: { yaml_version: '0.4.5', tft_version: '0.4.2' },
  };
  assert.notEqual(previewRenderKey(host), before);
});

test('a status poll that only moves live readings keeps every card render', () => {
  // The editor polls the status every 5 s; a new render key re-renders every card.
  const info = (uptime, rssi) => ({
    name: 'kitchen', yaml_version: '0.4.5', tft_version: '0.4.2', ip: '10.0.0.5', ssid: 'home',
    rssi, connection_uptime: uptime, last_panel_update: `2026-11-07T10:00:0${uptime % 10}Z`,
    last_connection: '2026-11-07T09:00:00Z', idle_page_active: false,
  });
  const host = {
    entryId: 'entry1',
    _selectedDevice: 'kitchen',
    _deviceConfig: {},
    _deviceStatuses: { kitchen: { device_info: info(100, -60) } },
    _devicePanels: () => [],
  };
  const before = previewRenderKey(host);
  host._deviceStatuses = { kitchen: { device_info: info(105, -61) } };
  assert.equal(previewRenderKey(host), before);
  // what the About page shows still re-renders it
  host._deviceStatuses = { kitchen: { device_info: { ...info(105, -61), ip: '10.0.0.6' } } };
  assert.notEqual(previewRenderKey(host), before);
});

test('initial editor load caches every device status before previews can render', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  const ed = editor();
  ed.entryId = 'entry1';
  ed._selectedDevice = null;
  ed._deviceStatuses = {};
  ed._deviceStatus = null;
  ed._deviceStatusError = null;
  const statuses = {
    kitchen: { connected: true, device_info: { yaml_version: '0.4.5', tft_version: '0.4.2' } },
    office: { connected: true, device_info: { yaml_version: '0.4.4', tft_version: '0.4.1' } },
  };
  let releaseStatuses;
  const statusUrls = [];
  ed.hass = {
    language: 'en',
    async fetchWithAuth(url) {
      if (url.startsWith('/api/nspanel_haui/panels/')) {
        return jsonResponse({
          devices: {
            kitchen: { config: {}, panels: [] },
            office: { config: {}, panels: [] },
          },
        });
      }
      if (url.startsWith('/api/nspanel_haui/status/')) {
        statusUrls.push(url);
        if (url.includes('?device=')) return jsonResponse(statuses.kitchen);
        return new Promise((resolve) => { releaseStatuses = resolve; });
      }
      throw new Error(`unexpected ${url}`);
    },
  };

  const loading = ed._load();
  await settle();

  assert.equal(ed._loading, true);
  assert.equal(ed._selectedDevice, 'kitchen');
  assert.deepEqual(statusUrls, ['/api/nspanel_haui/status/entry1']);
  assert.deepEqual(ed._deviceStatuses, {});

  releaseStatuses(jsonResponse({ devices: statuses }));
  await loading;
  await settle();
  stopStatusPolling(ed);

  assert.equal(ed._loading, false);
  assert.deepEqual(Object.keys(ed._deviceStatuses), ['kitchen', 'office']);
  assert.equal(ed._deviceStatus.device_info.yaml_version, '0.4.5');
});

test('switching devices clears the old status and fetches the new one at once', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  const host = statusHost();
  startStatusPolling(host);
  host.pending.shift()(jsonResponse({ connected: true, ip: '10.0.0.1' }));
  await settle();
  assert.equal(host._deviceStatus.ip, '10.0.0.1');

  host._selectedDevice = 'office';
  startStatusPolling(host);

  assert.equal(host._deviceStatus, null);
  assert.equal(host.urls.at(-1), '/api/nspanel_haui/status/entry1?device=office');
  stopStatusPolling(host);
});

test("a status response for the previously selected device is dropped", async () => {
  const host = statusHost();
  const request = Api.loadStatus(host);

  host._selectedDevice = 'office';
  host.pending.shift()(jsonResponse({ connected: true, ip: '10.0.0.1' }));
  await request;

  assert.equal(host._deviceStatus, undefined);
});

/** The Device Manager element without Lit's constructor, which needs a real DOM. */
function deviceManager(hass) {
  const Dialog = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(Dialog.prototype);
  Object.assign(dlg, { open: false, entryId: 'entry1', hass, __statusTimer: null });
  return dlg;
}

test('the Device Manager stops polling when the editor is removed', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  let fetches = 0;
  const dlg = deviceManager({ async fetchWithAuth() { fetches++; return jsonResponse({ devices: {} }); } });
  dlg.open = true;
  dlg.updated(new Map([['open', false]]));

  dlg.disconnectedCallback();
  const initialFetches = fetches;
  t.mock.timers.tick(15000);

  assert.equal(initialFetches, 2); // one status fetch and the automatic device scan
  assert.equal(fetches, initialFetches);
});

import { isOlderVersion } from '../../custom_components/nspanel_haui/frontend/device-info.js';

test('a display TFT is compared with its required version, not firmware version', () => {
  assert.equal(isOlderVersion('0.4.2', '0.4.3'), true);
  assert.equal(isOlderVersion('0.4.3', '0.4.3'), false);
  // Firmware-only releases may advance yaml_version while reusing the same TFT.
  assert.equal(isOlderVersion('0.4.3', '0.4.4'), true);
  assert.equal(isOlderVersion('0.4.1', '0.4'), false);
  assert.equal(isOlderVersion('0.3.10', '0.3.9'), false);
});

import { renderHealthSection } from '../../custom_components/nspanel_haui/frontend/dialogs/device-info.js';

/** Flatten a Lit TemplateResult into its markup and text, for assertions. */
function markup(value) {
  if (value == null || typeof value === 'function') return '';
  if (Array.isArray(value)) return value.map(markup).join('');
  if (value.strings) {
    return value.strings.map((s, i) => s + (i < value.values.length ? markup(value.values[i]) : '')).join('');
  }
  return String(value);
}

test('the health section surfaces versions, uptime, state and disconnect info', () => {
  const out = markup(renderHealthSection(
    { connected: true, integration_version: '0.4.0' },
    { connection_uptime: 125, idle_page_active: false, last_disconnect_reason: null, disconnected_since: null },
  ));
  assert.ok(out.includes('Health'));
  assert.ok(out.includes('0.4.0'));
  assert.ok(out.includes('2m'), out); // 125 s formatted as 2m
  assert.ok(out.includes('Regular page'));

  const off = markup(renderHealthSection(
    { connected: false },
    { idle_page_active: true, last_disconnect_reason: 'heartbeat timeout', disconnected_since: '2026-10-23T12:00:00+00:00' },
  ));
  assert.ok(off.includes('heartbeat timeout'));
  assert.ok(off.includes('Idle page'));
});test("the health section surfaces the TFT update state", () => {
  const out = markup(renderHealthSection(
    { connected: true, update: { state: "installing", version: "0.4.0", started_at: "2026-10-23T12:00:00+00:00", last_error: null } },
    {},
  ));
  assert.ok(out.includes("TFT Update"));
  assert.ok(out.includes("Installing TFT"));
  assert.ok(out.includes("0.4.0"));

  const err = markup(renderHealthSection(
    { connected: true, update: { state: "error", version: "0.4.0", last_error: "No GitHub release" } },
    {},
  ));
  assert.ok(err.includes("TFT update failed"));
  assert.ok(err.includes("No GitHub release"));

  // No update section when nothing is in flight / no history.
  const idle = markup(renderHealthSection({ connected: true }, {}));
  assert.ok(!idle.includes("TFT Update"));
});
