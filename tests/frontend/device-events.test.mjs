import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { loadDeviceConfig } from '../../custom_components/nspanel_haui/frontend/device-config.js';
import * as Events from '../../custom_components/nspanel_haui/frontend/device-events.js';
import { jsonResponse, makeHost } from './fake-host.mjs';

/** Host whose backend store is `serverStore`; device add/remove calls succeed. */
const bodies = [];
function hostWithStore(panels, serverStore) {
  return makeHost(panels, (method, path, opts) => {
    if (method === 'GET' && path.startsWith('/api/nspanel_haui/panels/')) {
      return jsonResponse(structuredClone(serverStore));
    }
    if (path.startsWith('/api/nspanel_haui/devices/')) {
      bodies.push(opts.body);
      return jsonResponse({ status: 'ok', devices_added: [] });
    }
    if (method === 'POST' && path.startsWith('/api/nspanel_haui/panels/')) {
      return jsonResponse({ status: 'ok' });
    }
    throw new Error(`unexpected ${method} ${path}`);
  }, { loadDeviceConfig });
}

const kitchen = { config: {}, panels: [] };
const office = { config: {}, panels: [] };

test('a device with an empty stored config defaults to enabled', () => {
  const host = hostWithStore({ devices: { kitchen } }, {});
  loadDeviceConfig(host, 'kitchen');
  assert.equal(host._deviceConfig.enabled, true);
});

test('adding a device refreshes the editor from the server store', async () => {
  const host = hostWithStore({ devices: { kitchen } }, { devices: { kitchen, office } });

  await Events.onDeviceManagerAdd(host, { detail: { device: { name: 'office' } } });

  assert.deepEqual(Object.keys(host._panels.devices), ['kitchen', 'office']);
});

test('adding a device sends the batch form', async () => {
  bodies.length = 0;
  const host = hostWithStore({ devices: { kitchen } }, { devices: { kitchen, office } });

  await Events.onDeviceManagerAdd(host, { detail: { device: { name: 'office' } } });

  assert.deepEqual(JSON.parse(bodies[0]), { devices: [{ name: 'office' }] });
});

test('scanning devices refreshes the editor from the server store', async () => {
  const host = hostWithStore({ devices: { kitchen } }, { devices: { kitchen, office } });

  await Events.onDeviceManagerScan(host, { detail: { devices: [{ name: 'office' }] } });

  assert.deepEqual(Object.keys(host._panels.devices), ['kitchen', 'office']);
});

test('removing a device refreshes the editor from the server store', async () => {
  const host = hostWithStore({ devices: { kitchen, office } }, { devices: { kitchen } });

  await Events.onDeviceManagerRemove(host, { detail: { name: 'office' } });

  assert.deepEqual(Object.keys(host._panels.devices), ['kitchen']);
});

test('toggling the selected device updates the config later saves send', async () => {
  const panels = { devices: { kitchen: { config: { enabled: true }, panels: [] } } };
  const host = hostWithStore(panels, panels);
  loadDeviceConfig(host, 'kitchen');

  await Events.onDeviceManagerToggleDevice(host, { detail: { name: 'kitchen' } });

  assert.equal(host._panels.devices.kitchen.config.enabled, false);
  assert.equal(host._deviceConfig.enabled, false);
});

test('a failed toggle save leaves the editor state unchanged and shows the error', async () => {
  const panels = { devices: { kitchen: { config: { enabled: true }, panels: [] } } };
  const host = makeHost(panels, () => jsonResponse({ message: 'nope' }, 500), { loadDeviceConfig });
  loadDeviceConfig(host, 'kitchen');

  await Events.onDeviceManagerToggleDevice(host, { detail: { name: 'kitchen' } });

  assert.equal(host._panels.devices.kitchen.config.enabled, true);
  assert.equal(host._deviceConfig.enabled, true);
  assert.deepEqual(host.toasts.at(-1), ['error', 'nope']);
  assert.equal(host._saving, false);
});

test('toggling a device that is not selected leaves the selected config alone', async () => {
  const panels = {
    devices: {
      kitchen: { config: { enabled: true }, panels: [] },
      office: { config: { enabled: true }, panels: [] },
    },
  };
  const host = hostWithStore(panels, panels);
  loadDeviceConfig(host, 'kitchen');

  await Events.onDeviceManagerToggleDevice(host, { detail: { name: 'office' } });

  assert.equal(host._panels.devices.office.config.enabled, false);
  assert.equal(host._deviceConfig.enabled, true);
});test('installing the TFT posts to the update endpoint and shows a success toast', async () => {
  const paths = [];
  const host = makeHost({ devices: { kitchen } }, (method, path, opts) => {
    paths.push([method, path, JSON.parse(opts.body)]);
    return jsonResponse({ status: 'ok', devices_updated: ['kitchen'] });
  });

  await Events.onDeviceManagerUpdateTft(host, { detail: { name: 'kitchen' } });

  assert.deepEqual(paths, [['POST', '/api/nspanel_haui/update_tft/entry1', { device: 'kitchen' }]]);
  assert.deepEqual(host.toasts.at(-1), ['success', 'TFT update started for "kitchen"']);
});

test('a failed TFT install shows the backend error', async () => {
  const host = makeHost({ devices: { kitchen } }, () => jsonResponse({ message: 'nope' }, 500));

  await Events.onDeviceManagerUpdateTft(host, { detail: { name: 'kitchen' } });

  assert.deepEqual(host.toasts.at(-1), ['error', 'nope']);
});test('a TFT install that fails for all devices reports the failed count and reason', async () => {
  const host = makeHost({ devices: { kitchen } }, () =>
    jsonResponse({
      status: 'ok',
      devices_updated: [],
      failed: [{ name: 'kitchen', error: 'device disconnected' }],
    }),
  );

  await Events.onDeviceManagerUpdateTft(host, { detail: { name: '*' } });

  assert.deepEqual(host.toasts.at(-1), [
    'error',
    'TFT update failed for 1 device(s): device disconnected',
  ]);
});

test('a failed TFT install rejects with its HTTP error message', async () => {
  const host = makeHost({ devices: { kitchen } }, () =>
    jsonResponse({ message: 'device disconnected' }, 502),
  );

  await Events.onDeviceManagerUpdateTft(host, { detail: { name: 'kitchen' } });

  assert.deepEqual(host.toasts.at(-1), ['error', 'device disconnected']);
});