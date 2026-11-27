import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

import {
  connectionTiles, deviceDiagnostics, diagnosticsModel, diagnosticsReport,
} from '../../custom_components/nspanel_haui/frontend/ui/device-diagnostics.js';
import {
  fmtBaud,
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

test('the Wi-Fi tile value is the reading alone; its signal bars are a hidden glyph of the tile', () => {
  const status = { connected: true, device_info: { rssi: -54 } };
  const tiles = render(connectionTiles(diagnosticsModel(status)));
  const wifi = [...tiles.querySelectorAll('.haui-diag-tile')].find((tile) => tile.textContent.includes('Wi-Fi'));
  assert.equal(wifi.querySelector('.haui-diag-tile-value').textContent.trim(), '-54 dBm');
  assert.ok(wifi.querySelector('.haui-rssi-bars').closest('[aria-hidden="true"]'));
});

test('RSSI display helpers map invalid values to unknown instead of offline or NaN', () => {
  for (const value of [null, undefined, '', 'bad-rssi', 'NaN', Number.NaN, Infinity]) {
    assert.equal(rssiStrengthClass(value), 'haui-wifi-unknown');
    assert.equal(rssiBarCount(value), 0);
    assert.equal(fmtRssi(value), 'Unknown');
  }

  assert.equal(rssiStrengthClass(-54), 'haui-wifi-good');
  assert.equal(fmtRssi(-54), '-54 dBm');
});

/** A tile fact's value, found by its term. */
function factValue(view, name) {
  const term = [...view.querySelectorAll('dt')].find((dt) => dt.textContent.trim() === name);
  return term ? term.nextElementSibling.textContent.trim() : null;
}

test('the Versions tile names the display link speed the panel reported', () => {
  const status = {
    connected: true,
    device_info: { yaml_version: '0.5.7', tft_version: '0.4.6', display_baud: 921600 },
  };
  const view = render(deviceDiagnostics({ status, expanded: true }));
  assert.equal(factValue(view, 'Display link'), '921600 bps');
  assert.ok(diagnosticsReport('kitchen', status).includes('Display link: 921600 bps'));

  // Firmware that does not publish the rate leaves it unknown, never 0 bps.
  const older = { connected: true, device_info: { tft_version: '0.4.5' } };
  assert.equal(factValue(render(deviceDiagnostics({ status: older, expanded: true })), 'Display link'), 'Unknown');
  assert.ok(diagnosticsReport('kitchen', older).includes('Display link: unknown'));
});

test('a malformed display link rate stays unknown', () => {
  for (const value of [null, undefined, '', 'bad-baud', 0, -1, 'NaN', Number.NaN]) {
    assert.equal(fmtBaud(value), 'Unknown');
  }
  assert.equal(fmtBaud(921600), '921600 bps');
  assert.equal(fmtBaud('115200'), '115200 bps');
});
