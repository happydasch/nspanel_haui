import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import * as Api from '../../custom_components/nspanel_haui/frontend/api.js';
import { startStatusPolling, stopStatusPolling } from '../../custom_components/nspanel_haui/frontend/device-info.js';
import '../../custom_components/nspanel_haui/frontend/dialogs/device-manager.js';
import { jsonResponse, makeHost } from './fake-host.mjs';

const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

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
  t.mock.timers.tick(15000);

  assert.equal(fetches, 1);
});

import { isOlderVersion } from '../../custom_components/nspanel_haui/frontend/device-info.js';

test('a display TFT older than the firmware version counts as an update pending', () => {
  assert.equal(isOlderVersion('0.3.3', '0.4.0'), true);
  assert.equal(isOlderVersion('0.4.0', '0.4.0'), false);
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
  assert.ok(out.includes('Active'));

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
