import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/haui-editor.js';
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
    last_connection: '2026-11-07T09:00:00Z', display_state: 'on',
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
  host.store.actions.stopSelectedStatusPolling();

  assert.equal(host._loading, false);
  assert.deepEqual(Object.keys(host._deviceStatuses), ['kitchen', 'office']);
  assert.equal(host._deviceStatus.device_info.yaml_version, '0.4.5');
});

test('switching devices clears the old status and fetches the new one at once', async (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  const host = statusHost();
  host.store.actions.startSelectedStatusPolling();
  host.pending.shift()(jsonResponse({ connected: true, ip: '10.0.0.1' }));
  await settle();
  assert.equal(host._deviceStatus.ip, '10.0.0.1');

  host.store.actions.selectDevice('office');

  assert.equal(host._deviceStatus, null);
  assert.equal(host.urls.at(-1), '/api/nspanel_haui/status/entry1?device=office');
  host.pending.shift()(jsonResponse({ connected: true }));
  await settle();
  host.store.actions.stopSelectedStatusPolling();
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
  host.store.actions.stopSelectedStatusPolling();
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

import {
  connectionTiles, deviceDiagnostics, diagnosticsIcon, diagnosticsModel, diagnosticsReport, watchedEntities,
} from '../../custom_components/nspanel_haui/frontend/ui/device-diagnostics.js';

/** Flatten a Lit TemplateResult into its markup and text, for assertions. */
function markup(value) {
  if (value == null || typeof value === 'function') return '';
  if (Array.isArray(value)) return value.map(markup).join('');
  if (value.strings) {
    return value.strings.map((s, i) => s + (i < value.values.length ? markup(value.values[i]) : '')).join('');
  }
  return String(value);
}

/** An ISO timestamp `minutes` before now, as the hub writes it into a log line. */
const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60_000).toISOString();

const healthy = {
  connected: true,
  haui_version: '0.4.0',
  haui_version_mismatch: false,
  device_info: { connection_uptime: 125, rssi: -55, yaml_version: '0.4.0', tft_version: '0.4.0' },
  logs: ['[2026-11-11T10:00:00+01:00] INFO started'],
};

test('a healthy device keeps uptime out of the collapsed diagnostics body', () => {
  const model = diagnosticsModel(healthy);
  assert.deepEqual(model.issues, []);
  assert.ok(markup(diagnosticsIcon(model)).includes('All good'));
  const simple = markup(deviceDiagnostics({ status: healthy }));
  assert.equal(simple, '');
  const expanded = markup(deviceDiagnostics({ status: healthy, expanded: true }));
  assert.ok(expanded.includes('haui-diag-tiles'));
  assert.ok(expanded.includes('No warnings'));
  assert.ok(!expanded.includes('Redraw display'));
  assert.ok(expanded.includes('Copy report'));
});

test('diagnostics count offline, mismatch, display, signal and log problems as issues', () => {
  const status = {
    connected: false,
    haui_version: '0.4.5',
    haui_version_mismatch: true,
    device_info: {
      yaml_version: '0.4.4', tft_version: '0.4.3', tft_required_version: '0.4.5', rssi: -80,
      last_disconnect_reason: 'heartbeat timeout', disconnected_since: '2026-10-23T12:00:00+00:00',
    },
    logs: [
      `[${minutesAgo(2)}] WARNING slow render`,
      `[${minutesAgo(1)}] ERROR service failed\n  detail of the error`,
      `[${minutesAgo(1)}] INFO WARNING inside a message`,
      // A warning from two days ago is history: it no longer counts as an issue.
      `[${minutesAgo(48 * 60)}] WARNING an old hiccup`,
    ],
  };
  const model = diagnosticsModel(status);
  // Offline hides the signal issue: a stale reading is not a weak one.
  assert.deepEqual(model.issues.map((issue) => issue.key), ['offline', 'mismatch', 'tft', 'logs']);
  assert.equal(model.logProblems, 2);
  const badge = markup(diagnosticsIcon(model));
  assert.ok(badge.includes('4 issues'));
  // Read out, not only a tooltip.
  assert.ok(badge.includes('role="img"'));
  assert.ok(badge.includes('4 issues: Offline, Firmware does not match the hub, Display update pending, 2 log warnings'), badge);

  const simple = markup(deviceDiagnostics({ status }));
  assert.equal(simple, '');

  const expanded = markup(deviceDiagnostics({ status, expanded: true }));
  assert.ok(expanded.includes('haui-diag-tiles'));
  // The connection readings are tiles of the Connection & device card.
  assert.ok(!expanded.includes('heartbeat timeout'));
  const connection = markup(connectionTiles(model));
  assert.match(connection, /Status[\s\S]*Offline/);
  assert.ok(connection.includes('heartbeat timeout'));
  assert.ok(expanded.includes('Mismatch'));
  assert.ok(expanded.includes('Hub details'));
  // Copy report closes the Hub details; the Hub log tile opens the logs.
  assert.match(expanded, /Hub details[\s\S]*Copy report[\s\S]*<\/details>/);
  assert.ok(!expanded.includes('>Logs<'));
});

test('the Diagnostics tiles: Firmware shows its details on hover or tap, Hub log opens the logs', () => {
  const opened = [];
  const status = { ...healthy, device_info: { ...healthy.device_info, ssid: 'HomeNet', ip: '192.0.2.11' } };
  const view = deviceDiagnostics({ status, expanded: true, onLogs: () => opened.push('logs') });
  const text = markup(view);
  assert.ok(!text.includes('haui-diag-tile-detail'));
  assert.equal(text.match(/class="haui-tile-info"/g).length, 2);
  assert.match(text, /<dt>YAML version<\/dt><dd class=[^>]*>0\.4\.0<\/dd>/);
  // The Firmware tile toggles its card on a tap; the Hub log tile opens the logs instead.
  assert.equal(text.match(/aria-expanded="false"/g).length, 1);
  // Uptime and Wi-Fi are tiles of the Connection & device card.
  assert.ok(!text.includes('HomeNet'));
  const connection = markup(connectionTiles(diagnosticsModel(status)));
  assert.equal(connection.match(/aria-expanded="false"/g).length, 2);
  assert.match(connection, /Online for[\s\S]*2m[\s\S]*Wi-Fi[\s\S]*-55 dBm/);
  assert.match(connection, /<dt>SSID<\/dt><dd class=[^>]*>HomeNet<\/dd>/);
  const handlers = [];
  const collect = (value) => {
    if (Array.isArray(value)) value.forEach(collect);
    else if (typeof value === 'function') handlers.push(value);
    else if (value?.values) value.values.forEach(collect);
  };
  collect(view);
  const trigger = { getAttribute: () => 'false', setAttribute() {}, focus() {} };
  const logs = handlers.find((handler) => { handler({ currentTarget: trigger }); return opened.length; });
  assert.ok(logs);
  assert.deepEqual(opened, ['logs']);
});

test('the expanded Diagnostics card has the Show entities checkbox below the tiles', () => {
  const shown = [];
  const view = (showEntities) => deviceDiagnostics({
    status: healthy, expanded: true, showEntities, onShowEntities: (show) => shown.push(show),
  });
  const text = markup(view(false));
  assert.match(text, /haui-diag-tiles[\s\S]*type="checkbox"[\s\S]*Show entities in the preview[\s\S]*Hub details/);
  assert.ok(text.includes('Hover over a widget in the preview'));
  // Collapsed, and without a handler, the card has no checkbox.
  assert.ok(!markup(deviceDiagnostics({ status: healthy, onShowEntities: () => {} })).includes('checkbox'));
  assert.ok(!markup(deviceDiagnostics({ status: healthy, expanded: true })).includes('checkbox'));

  const find = (value) => {
    if (Array.isArray(value)) return value.map(find).find(Boolean);
    if (!value?.strings) return null;
    return value.strings.join('').includes('type="checkbox"') ? value : value.values.map(find).find(Boolean);
  };
  const check = find(view(true));
  assert.ok(check.values.includes(true));
  check.values.find((value) => typeof value === 'function')({ currentTarget: { checked: false } });
  assert.deepEqual(shown, [false]);
});

test('the Firmware tile shows a failed or running display update', () => {
  const failed = { ...healthy, update: { state: 'error', version: '0.4.1', last_error: 'No GitHub release' } };
  assert.deepEqual(diagnosticsModel(failed).issues.map((issue) => issue.key), ['update']);
  assert.ok(markup(deviceDiagnostics({ status: failed, expanded: true })).includes('update failed'));

  const installing = { ...healthy, update: { state: 'installing', version: '0.4.1' } };
  assert.deepEqual(diagnosticsModel(installing).issues, []);
  assert.ok(markup(deviceDiagnostics({ status: installing, expanded: true })).includes('installing'));
});

/** A Home Assistant stand-in: entity states plus its state formatter. */
const fakeHass = {
  states: {
    'weather.home': { state: 'sunny', attributes: { friendly_name: 'Home weather' } },
    'sensor.hall': { state: 'unavailable', attributes: { friendly_name: 'Hall temperature' } },
  },
  formatEntityState: (stateObj) => `formatted ${stateObj.state}`,
};

const listeners = [
  { item_id: 'weather.home', attribute: 'temperature', callback_name: 'callback_weather' },
  { item_id: 'weather.home', attribute: 'pressure', callback_name: 'callback_weather' },
  { item_id: 'sensor.hall', attribute: null, callback_name: 'callback_temp' },
  { item_id: 'light.gone', attribute: null, callback_name: 'callback_light' },
];

test('watched entities group the listeners per entity with their live state', () => {
  const entities = watchedEntities(listeners, fakeHass);
  assert.deepEqual(entities.map(({ entityId, attributes, name, value, problem }) => (
    { entityId, attributes, name, value, problem })), [
    { entityId: 'weather.home', attributes: ['temperature', 'pressure'], name: 'Home weather', value: 'formatted sunny', problem: false },
    { entityId: 'sensor.hall', attributes: [], name: 'Hall temperature', value: 'formatted unavailable', problem: true },
    { entityId: 'light.gone', attributes: [], name: 'light.gone', value: 'Not found', problem: true },
  ]);
});

test('hub details show the display, the idle page and the watched entities', () => {
  const status = {
    ...healthy,
    device_info: { ...healthy.device_info, display_state: 'on' },
    idle_page: { state: 'pending', idle_in: 95 },
    active_listeners: listeners,
    active_listener_count: 4,
    active_timers: [{ callback_name: '_tick', type: 'interval', interval: 1 }],
    active_timer_count: 1,
  };
  const expanded = markup(deviceDiagnostics({ status, hass: fakeHass, expanded: true }));
  assert.ok(expanded.includes('3 watched entities'), expanded);
  assert.ok(expanded.includes('2 unavailable'));
  assert.ok(expanded.includes('In 1m'));
  assert.ok(expanded.includes('Home weather'));
  assert.ok(expanded.includes('weather.home · temperature, pressure'));
  assert.ok(expanded.includes('Listeners 4 · Timers 1'));
  // The raw timer list lives in the report only.
  assert.ok(!expanded.includes('_tick'));
  // A missing entity has nothing to open.
  assert.equal(expanded.match(/<button type="button" class="haui-diag-entity"/g).length, 2);

  for (const [idlePage, label] of [
    [{ state: 'active', idle_in: null }, 'Shown'],
    [{ state: 'suspended', idle_in: null }, 'Paused by an overlay'],
    [{ state: 'held', idle_in: null }, 'Held by the current page'],
    [{ state: 'off', idle_in: null }, 'Off'],
  ]) {
    assert.ok(markup(deviceDiagnostics({ status: { ...status, idle_page: idlePage }, hass: fakeHass, expanded: true }))
      .includes(label), label);
  }
  // Offline, the hub's display and idle readings are stale: only the entities stay.
  const offline = markup(deviceDiagnostics({ status: { ...status, connected: false }, hass: fakeHass, expanded: true }));
  assert.ok(!offline.includes('Idle page'));
  assert.ok(offline.includes('Home weather'));
});

test('drops and late heartbeats of the last 24 hours show in the uptime tile, the hub details and the report', () => {
  const recentDrops = [
    { time: new Date(Date.now() - 3 * 3_600_000).toISOString(), reason: 'device reconnected' },
    { time: new Date(Date.now() - 5 * 3_600_000).toISOString(), reason: 'heartbeat timeout' },
  ];
  const health = {
    drops_24h: 2, recent_drops: recentDrops, late_heartbeats_24h: 4, longest_heartbeat_gap: 9.2, heartbeat_interval: 5,
  };
  const status = { ...healthy, connection_health: health };
  // Two drops are worth showing, not yet an issue.
  assert.deepEqual(diagnosticsModel(status).issues, []);
  // The uptime tile's card: the count with the latest drop, and its reason.
  const tiles = markup(connectionTiles(diagnosticsModel(status)));
  assert.match(tiles, /<dt>Disconnects \(24 h\)<\/dt><dd class=[^>]*>2 · 3 hours ago<\/dd>/);
  assert.match(tiles, /<dt>Last drop<\/dt><dd class=[^>]*>device reconnected<\/dd>/);
  const expanded = markup(deviceDiagnostics({ status, expanded: true }));
  assert.ok(expanded.includes('2 · device reconnected · 3 hours ago'));
  assert.ok(expanded.includes('4 · longest 9s'));

  const unstable = { ...healthy, connection_health: { ...health, drops_24h: 3 } };
  assert.deepEqual(diagnosticsModel(unstable).issues.map((issue) => issue.key), ['unstable']);
  assert.equal(markup(deviceDiagnostics({ status: unstable })), '');

  const quiet = { ...healthy, connection_health: { drops_24h: 0, recent_drops: [], late_heartbeats_24h: 0, longest_heartbeat_gap: null } };
  const quietMarkup = markup(deviceDiagnostics({ status: quiet, expanded: true }));
  // The hub details' two rows, and the uptime tile's card.
  assert.equal(quietMarkup.match(/>None</g).length, 2);
  const quietTiles = markup(connectionTiles(diagnosticsModel(quiet)));
  assert.equal(quietTiles.match(/>None</g).length, 1);
  assert.ok(!quietTiles.includes('Last drop'));

  const report = diagnosticsReport('kitchen', status, new Date('2026-11-11T09:00:00Z'));
  assert.ok(report.includes(`Disconnects (24 h): 2\n  ${recentDrops[0].time} device reconnected`));
  assert.ok(report.includes('Late heartbeats (24 h): 4, longest 9.2s'));
});

test('the diagnostics report carries versions and logs but not the SSID or IP', () => {
  const status = {
    ...healthy,
    device_info: { ...healthy.device_info, ssid: 'HomeNet', ip: '192.0.2.11' },
    active_listeners: [
      { item_id: 'weather.home', attribute: 'temperature', callback_name: 'callback_weather' },
      { item_id: 'weather.home', attribute: 'pressure', callback_name: 'callback_weather' },
      { item_id: 'sensor.kasia_temperature', attribute: null, callback_name: 'callback_inside_temp' },
    ],
    active_listener_count: 3,
    active_timers: [{ callback_name: '_check_inactivity', type: 'interval', interval: 1 }],
    active_timer_count: 1,
    idle_page: { state: 'pending', idle_in: 42 },
    logs: [
      '[2026-11-11T10:00:00+01:00] INFO started',
      '[2026-11-11T10:00:05+01:00] INFO Syncing switch.kasia_lamp ON (hub config use_relay_left=True) from 192.0.2.11',
    ],
  };
  const report = diagnosticsReport('kitchen', status, new Date('2026-11-11T09:00:00Z'));
  assert.ok(report.includes('INFO Syncing switch.<entity> ON (hub config use_relay_left=True) from <ip>'), report);
  assert.ok(report.includes('Device: kitchen'));
  assert.ok(report.includes('Generated: 2026-11-11T09:00:00.000Z'));
  assert.ok(report.includes('Integration: 0.4.0'));
  assert.ok(report.includes('Wi-Fi signal: -55 dBm'));
  assert.ok(report.includes('Idle page: pending (in 42s)'));
  assert.ok(report.includes('Listeners (3):\n  weather [temperature] -> callback_weather'));
  assert.ok(report.includes('  sensor [state] -> callback_inside_temp'));
  assert.ok(report.includes('Timers (1):\n  _check_inactivity (interval 1s)'));
  // Entity ids carry room and people names: the public report keeps only the domain.
  assert.ok(!report.includes('weather.home'));
  assert.ok(!report.includes('kasia'));
  assert.ok(report.includes('INFO started'));
  assert.ok(!report.includes('HomeNet'));
  assert.ok(!report.includes('192.0.2.11'));
});
