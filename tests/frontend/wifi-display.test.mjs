import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

import {
  connectionTiles, deviceDiagnostics, diagnosticsModel,
} from '../../custom_components/nspanel_haui/frontend/ui/device-diagnostics.js';
import {
  fmtRssi,
  rssiBarCount,
  rssiStrengthClass,
} from '../../custom_components/nspanel_haui/frontend/device-info.js';

test('device diagnostics preserve available readings and report malformed RSSI as unknown', () => {
  const status = {
    connected: true,
    connection_state: 'connected',
    current_page: 'home',
    device_info: { name: 'panel', ip: '10.0.0.8', ssid: '', rssi: 'bad-rssi' },
  };

  const simple = render(deviceDiagnostics({ status }));
  assert.equal(simple.textContent.trim(), '');

  const tiles = render(connectionTiles(diagnosticsModel(status)));
  assert.ok(tiles.textContent.includes('10.0.0.8'));
  assert.ok(tiles.textContent.includes('Unknown'));
  assert.doesNotMatch(tiles.textContent, /NaN/);

  const expanded = render(deviceDiagnostics({ status, expanded: true }));
  assert.doesNotMatch(expanded.textContent, /NaN/);
  assert.doesNotMatch(expanded.textContent, /Transport|Device Names|Page Mode/);

  status.device_info.display_state = 'dim';
  status.idle_page = { state: 'active', idle_in: null };
  const withIdleState = render(deviceDiagnostics({ status, expanded: true }));
  assert.ok(withIdleState.textContent.includes('Dimmed'));
  assert.ok(withIdleState.textContent.includes('Shown'));
});

test('RSSI display helpers map invalid values to unknown instead of offline or NaN', () => {
  for (const value of [null, undefined, '', 'bad-rssi', 'NaN', Number.NaN, Infinity]) {
    assert.equal(rssiStrengthClass(value), 'wifi-unknown');
    assert.equal(rssiBarCount(value), 0);
    assert.equal(fmtRssi(value), 'Unknown');
  }

  assert.equal(rssiStrengthClass(-54), 'wifi-good');
  assert.equal(fmtRssi(-54), '-54 dBm');
});
