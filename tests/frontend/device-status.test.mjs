import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { startStatusPolling, stopStatusPolling } from '../../custom_components/nspanel_haui/frontend/device-info.js';
import '../../custom_components/nspanel_haui/frontend/dialogs/device-manager.js';
import { jsonResponse, makeHost } from './fake-host.mjs';
import { previewRenderKey } from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';

const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

function previewContext(overrides = {}) {
  return {
    entryId: 'entry1',
    device: 'kitchen',
    deviceConfig: {},
    panels: [],
    deviceInfo: null,
    api: { preview: { render: async () => null } },
    ...overrides,
  };
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
  const context = previewContext();
  const before = previewRenderKey(context);
  context.deviceInfo = { yaml_version: '0.4.5', tft_version: '0.4.2' };
  assert.notEqual(previewRenderKey(context), before);
});

test('a status poll that only moves live readings keeps every card render', () => {
  // The editor polls the status every 5 s; a new render key re-renders every card.
  const info = (uptime, rssi) => ({
    name: 'kitchen', yaml_version: '0.4.5', tft_version: '0.4.2', ip: '10.0.0.5', ssid: 'home',
    rssi, connection_uptime: uptime, last_panel_update: `2026-11-07T10:00:0${uptime % 10}Z`,
    last_connection: '2026-11-07T09:00:00Z', idle_page_active: false,
  });
  const context = previewContext({ deviceInfo: info(100, -60) });
  const before = previewRenderKey(context);
  context.deviceInfo = info(105, -61);
  assert.equal(previewRenderKey(context), before);
  // what the About page shows still re-renders it
  context.deviceInfo = { ...info(105, -61), ip: '10.0.0.6' };
  assert.notEqual(previewRenderKey(context), before);
});

test('initial editor load caches every device status before previews can render', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  const statuses = {
    kitchen: { connected: true, device_info: { yaml_version: '0.4.5', tft_version: '0.4.2' } },
    office: { connected: true, device_info: { yaml_version: '0.4.4', tft_version: '0.4.1' } },
  };
  let releaseStatuses;
  const statusUrls = [];
  const host = makeHost(
    { devices: { kitchen: { config: {}, panels: [] }, office: { config: {}, panels: [] } } },
    (method, path) => {
      if (path === '/api/nspanel_haui/panels/entry1') {
        return jsonResponse({
          devices: {
            kitchen: { config: {}, panels: [] },
            office: { config: {}, panels: [] },
          },
        });
      }
      if (path === '/api/nspanel_haui/status/entry1') {
        statusUrls.push(host.urls.at(-1));
        return new Promise((resolve) => { releaseStatuses = resolve; });
      }
      if (path === '/api/nspanel_haui/panel_types') return jsonResponse([]);
      if (path === '/api/nspanel_haui/notifications/entry1') return jsonResponse([]);
      throw new Error(`unexpected ${method} ${path}`);
    },
  );

  const loading = host.store.actions.loadHub('entry1');
  await settle();

  assert.equal(host._loading, true);
  assert.equal(host._selectedDevice, 'kitchen');
  assert.deepEqual(statusUrls, ['/api/nspanel_haui/status/entry1']);
  assert.deepEqual(host._deviceStatuses, {});

  releaseStatuses(jsonResponse({ devices: statuses }));
  await loading;
  await settle();
  stopStatusPolling(host);

  assert.equal(host._loading, false);
  assert.deepEqual(Object.keys(host._deviceStatuses), ['kitchen', 'office']);
  assert.equal(host._deviceStatus.device_info.yaml_version, '0.4.5');
});

test('switching devices clears the old status and fetches the new one at once', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  const host = statusHost();
  startStatusPolling(host);
  host.pending.shift()(jsonResponse({ connected: true, ip: '10.0.0.1' }));
  await settle();
  assert.equal(host._deviceStatus.ip, '10.0.0.1');

  host.store.actions.selectDevice('office');

  assert.equal(host._deviceStatus, null);
  assert.equal(host.urls.at(-1), '/api/nspanel_haui/status/entry1?device=office');
  host.pending.shift()(jsonResponse({ connected: true }));
  await settle();
  stopStatusPolling(host);
});

test('a status response for the previously selected device is dropped', async () => {
  const host = statusHost();
  const request = host.store.actions.pollSelectedStatus();

  host.store.actions.selectDevice('office');
  host.pending.shift()(jsonResponse({ connected: true, ip: '10.0.0.1' }));
  await request;

  assert.equal(host._deviceStatus, null);
  host.pending.shift()(jsonResponse({ connected: true }));
  await settle();
  stopStatusPolling(host);
});

/** The Device Manager element without Lit's constructor, which needs a real DOM. */
function deviceManager(host) {
  const Dialog = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(Dialog.prototype);
  Object.assign(dlg, {
    open: false,
    entryId: 'entry1',
    hass: host.hass,
    api: host.api,
    onStatusPollingStart: () => host.store.actions.startAllStatusPolling(),
    onStatusPollingStop: () => host.store.actions.stopAllStatusPolling(),
  });
  return dlg;
}

test('the Device Manager stops polling when the editor is removed', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  let fetches = 0;
  const host = makeHost({ devices: { kitchen: { config: {}, panels: [] } } }, (method, path) => {
    fetches++;
    if (path === '/api/nspanel_haui/devices/entry1') return jsonResponse({ devices: [] });
    if (path === '/api/nspanel_haui/status/entry1') return jsonResponse({ devices: {} });
    throw new Error(`unexpected ${method} ${path}`);
  });
  const dlg = deviceManager(host);
  dlg.open = true;
  dlg.updated(new Map([['open', false]]));
  await settle();

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
  assert.equal(isOlderVersion('0.4.5.dev29', '0.4.5.dev30'), true);
  assert.equal(isOlderVersion('0.4.5.dev30', '0.4.5.dev29'), false);
  assert.equal(isOlderVersion('0.4.5.dev30', '0.4.5'), true);
  assert.equal(isOlderVersion('0.4.5.rc1', '0.4.5'), true);
  assert.equal(isOlderVersion('0.4.5', '0.4.5.dev30'), false);
  assert.equal(isOlderVersion('', '0.4.5'), false);
  assert.equal(isOlderVersion('not-a-version', '0.4.5'), false);
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
    { connected: true, haui_version: '0.4.0', haui_version_mismatch: false },
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

  const mismatch = markup(renderHealthSection(
    { connected: true, haui_version: '0.4.5', haui_version_mismatch: true },
    { yaml_version: '0.4.4' },
  ));
  assert.ok(mismatch.includes('Firmware and HAUI versions do not match'));
});

test("the health section surfaces the TFT update state", () => {
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
