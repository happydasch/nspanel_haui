import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import * as Events from '../../custom_components/nspanel_haui/frontend/device-events.js';
import { makeHost } from './fake-host.mjs';

const kitchen = { config: {}, panels: [] };

test('a TFT install whose request times out shows the friendly timeout message', async () => {
  // The API layer aborts requests that never settle and rejects with a
  // TimeoutError; the handler must surface that instead of a silent no-op.
  const host = makeHost({ devices: { kitchen } }, () =>
    Promise.reject(Object.assign(new Error('timed out'), { name: 'TimeoutError' })),
  );

  await Events.onDeviceManagerUpdateTft(host, { detail: { name: 'kitchen' } });

  assert.deepEqual(host.toasts.at(-1), [
    'error',
    'Request timed out; the device may be busy. Check the Home Assistant logs',
  ]);
});

test('a display refresh whose request times out shows the friendly timeout message', async () => {
  const host = makeHost({ devices: { kitchen } }, () =>
    Promise.reject(Object.assign(new Error('timed out'), { name: 'TimeoutError' })),
  );

  await Events.onDeviceManagerUpdateDisplay(host, { detail: { name: 'kitchen' } });

  assert.deepEqual(host.toasts.at(-1), [
    'error',
    'Request timed out; the device may be busy. Check the Home Assistant logs',
  ]);
});
