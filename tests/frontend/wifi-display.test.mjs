import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import {
  connectionTiles, deviceDiagnostics, diagnosticsModel,
} from '../../custom_components/nspanel_haui/frontend/ui/device-diagnostics.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import {
  fmtRssi,
  rssiBarCount,
  rssiStrengthClass,
} from '../../custom_components/nspanel_haui/frontend/device-info.js';

function collect(value, result = []) {
  if (typeof value === 'string') result.push(value);
  else if (Array.isArray(value)) value.forEach((item) => collect(item, result));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collect(value.strings, result);
    if (Array.isArray(value.values)) collect(value.values, result);
  }
  return result;
}

test('RSSI display helpers map invalid values to unknown instead of offline or NaN', () => {
  for (const value of [null, undefined, '', 'bad-rssi', 'NaN', Number.NaN, Infinity]) {
    assert.equal(rssiStrengthClass(value), 'wifi-unknown');
    assert.equal(rssiBarCount(value), 0);
    assert.equal(fmtRssi(value), 'Unknown');
  }

  assert.equal(rssiStrengthClass(-54), 'wifi-good');
  assert.equal(fmtRssi(-54), '-54 dBm');
});

test('device diagnostics keep partial readings and render malformed RSSI as unknown', () => {
  const status = {
    connected: true,
    connection_state: 'connected',
    current_page: 'home',
    device_info: { name: 'panel', ip: '10.0.0.8', ssid: '', rssi: 'bad-rssi' },
  };

  const simple = collect(deviceDiagnostics({ status })).join(' ');
  assert.equal(simple, '');

  // The Wi-Fi tile of the Connection & device card.
  const tiles = collect(connectionTiles(diagnosticsModel(status))).join(' ');
  assert.match(tiles, /10\.0\.0\.8/);
  assert.match(tiles, /Unknown/);
  assert.doesNotMatch(tiles, /NaN/);

  const markup = collect(deviceDiagnostics({ status, expanded: true })).join(' ');
  assert.match(markup, /Hub details/);
  assert.match(markup, /Idle page/);
  assert.doesNotMatch(markup, /Transport|Device Names|Page Mode/);

  assert.doesNotMatch(markup, /NaN/);
  assert.doesNotMatch(markup, /mdi:wifi-off/);

  status.device_info.display_state = 'dim';
  status.idle_page = { state: 'active', idle_in: null };
  const idleMarkup = collect(deviceDiagnostics({ status, expanded: true })).join(' ');
  assert.match(idleMarkup, /Dimmed/);
  assert.match(idleMarkup, /Shown/);
});

test('the firmware popover hides manual update actions when updates are disabled', () => {
  const FirmwarePopover = customElements.get('nspanel-firmware-popover');
  const dialog = Object.create(FirmwarePopover.prototype);
  Object.assign(dialog, {
    open: true,
    deviceStatus: { device_info: {}, update: { enabled: false } },
    deviceName: 'kitchen',
    _actionBusy: false,
  });

  const markup = collect(dialog.render()).join(' ');
  assert.doesNotMatch(markup, /Install update|Display \(TFT\)|Download firmware/);
});

test('the firmware popover keeps both row install actions without a compatible update offer', () => {
  const FirmwarePopover = customElements.get('nspanel-firmware-popover');
  const dialog = Object.assign(Object.create(FirmwarePopover.prototype), {
    open: true,
    deviceStatus: {
      device_info: {},
      update: { enabled: true, firmware_update_available: false, tft_update_available: false },
    },
    deviceName: 'custom-panel',
    _picker: null,
    _actionBusy: false,
  });

  const labels = collect(dialog.render());
  assert.equal(labels.filter((label) => label === 'Install').length, 2);
  assert.ok(!labels.includes('Install update'));
});

test('the firmware popover keeps both row install actions when an update is offered', () => {
  const FirmwarePopover = customElements.get('nspanel-firmware-popover');
  const dialog = Object.assign(Object.create(FirmwarePopover.prototype), {
    open: true,
    deviceStatus: {
      device_info: {},
      update: {
        enabled: true,
        firmware_update_available: false,
        tft_update_available: true,
        firmware_update_version: '0.4.5',
      },
    },
    deviceName: 'kitchen',
    _picker: null,
    _actionBusy: false,
  });

  const labels = collect(dialog.render());
  assert.equal(labels.filter((label) => label === 'Install').length, 2);
  assert.ok(labels.includes('outlined'));
  assert.ok(!labels.includes('Install update'));
});

test('the display redraw goes through the hub and reports the result', async () => {
  const calls = [];
  const host = Object.create(NSPanelEditor.prototype);
  Object.assign(host, {
    entryId: 'entry1',
    toasts: [],
    _showToast(message, kind) { host.toasts.push([kind, message]); },
    hass: {
      async fetchWithAuth(path, options) {
        calls.push([path, JSON.parse(options.body)]);
        return { ok: true, json: async () => ({ status: 'ok' }) };
      },
    },
  });
  host.api = createApiClient(() => host.hass);

  await host._redrawDisplay('kitchen');

  assert.deepEqual(calls, [['/api/nspanel_haui/refresh_display/entry1', { device: 'kitchen' }]]);
  assert.deepEqual(host.toasts, [['success', 'Display refreshed for "kitchen"']]);
});
