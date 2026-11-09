import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { renderDeviceInfoStrip } from '../../custom_components/nspanel_haui/frontend/toolbar.js';
import {
  fmtRssi,
  rssiBarCount,
  rssiIcon,
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
    assert.equal(rssiIcon(value), 'mdi:wifi');
    assert.equal(rssiBarCount(value), 0);
    assert.equal(fmtRssi(value), 'Unknown');
  }

  assert.equal(rssiIcon(-54), 'mdi:wifi-strength-3');
  assert.equal(rssiStrengthClass(-54), 'wifi-good');
  assert.equal(fmtRssi(-54), '-54 dBm');
});

test('Device Manager renders each network value from the backend status', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dialog = Object.create(DeviceManager.prototype);
  Object.assign(dialog, {
    devices: { panel: { config: {}, panels: [] } },
    selectedDevice: 'panel',
    _deviceMenuIndex: -1,
    _deviceStatuses: {
      panel: { device_info: { ip: '', ssid: 'HomeNet', rssi: -54 } },
    },
    hass: { states: { 'sensor.panel_ip': { state: '192.0.2.99' } } },
  });

  const markup = collect(dialog._renderDeviceRow('panel')).join(' ');
  assert.match(markup, /HomeNet/);
  assert.match(markup, /mdi:wifi-strength-3/);
  assert.doesNotMatch(markup, /192\.0\.2\.99/);
  assert.doesNotMatch(markup, /Offline/);
});

test('Device Info keeps partial readings and renders malformed RSSI as unknown', () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dialog = Object.create(DeviceInfo.prototype);
  Object.assign(dialog, {
    deviceStatus: {
      connected: true,
      connection_state: 'connected',
      current_page: 'home',
      device_info: { name: 'panel', ip: '10.0.0.8', ssid: '', rssi: 'bad-rssi' },
    },
  });

  const markup = collect(dialog.render()).join(' ');
  assert.match(markup, /10\.0\.0\.8/);
  assert.match(markup, /Unknown/);
  assert.match(markup, /Page Mode/);
  assert.match(markup, /Regular page/);

  assert.doesNotMatch(markup, /NaN/);
  assert.doesNotMatch(markup, /mdi:wifi-off/);

  dialog.deviceStatus.device_info.idle_page_active = true;
  const idleMarkup = collect(dialog.render()).join(' ');
  assert.match(idleMarkup, /Idle page/);
  assert.doesNotMatch(idleMarkup, /Regular page/);
});

test('Device Info hides manual update actions when updates are disabled', () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dialog = Object.create(DeviceInfo.prototype);
  Object.assign(dialog, {
    deviceStatus: { device_info: {}, update: { enabled: false } },
    deviceName: 'kitchen',
    _actionBusy: false,
  });

  const markup = collect(dialog.render()).join(' ');
  assert.doesNotMatch(markup, /Install update|Display \(TFT\)|Download firmware/);
});

test('Device Info keeps manual install choices available without a compatible update offer', () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dialog = Object.create(DeviceInfo.prototype);
  Object.assign(dialog, {
    deviceStatus: {
      device_info: {},
      update: {
        enabled: true,
        firmware_update_available: false,
        tft_update_available: false,
        firmware_update_version: null,
      },
    },
    deviceName: 'custom-panel',
    _picker: null,
    _actionBusy: false,
  });

  const labels = collect(dialog.render());
  assert.ok(labels.includes('Install update'));
  assert.ok(labels.includes('Download firmware'));

  dialog._openPicker('select', 'custom-panel');
  const choices = collect(dialog._renderPicker('custom-panel', null, dialog.deviceStatus.update));
  assert.ok(choices.includes('Display (TFT)'));
  assert.ok(choices.includes('Firmware'));
});

test('Device Info offers both manual install types even if only TFT has a compatible update', () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dialog = Object.create(DeviceInfo.prototype);
  Object.assign(dialog, {
    deviceStatus: {
      device_info: {},
      update: {
        enabled: true,
        firmware_update_available: false,
        tft_update_available: true,
      },
    },
    deviceName: 'custom-panel',
    _picker: null,
    _actionBusy: false,
  });

  assert.ok(collect(dialog.render()).includes('Install update'));
  dialog._openPicker('select', 'custom-panel');
  const choices = collect(dialog._renderPicker('custom-panel', null, dialog.deviceStatus.update));
  assert.ok(choices.includes('Display (TFT)'));
  assert.ok(choices.includes('Firmware'));
});

test('Device Info exposes refresh, update type selection, and firmware download actions', async () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dialog = Object.create(DeviceInfo.prototype);
  const calls = [];
  Object.assign(dialog, {
    deviceStatus: {
      device_info: {},
      update: {
        enabled: true,
        firmware_update_available: true,
        tft_update_available: true,
        firmware_update_version: '0.4.5',
      },
    },
    deviceName: 'kitchen',
    entryId: 'entry1',
    _picker: null,
    _actionBusy: false,
    _toast: null,
    hass: {
      language: 'en',
      locale: { language: 'en' },
      async fetchWithAuth(path, options = {}) {
        calls.push([path, options]);
        return {
          ok: true,
          json: async () => path === '/api/nspanel_haui/firmware'
            ? { url: 'https://example.test/nspanel_haui.bin', version: '0.4.5' }
            : { status: 'ok', update: { state: 'installing' } },
        };
      },
    },
  });

  await dialog._loadFirmwareDownloadInfo();
  const markup = collect(dialog.render()).join(' ');
  assert.match(markup, /Redraw display/);
  assert.doesNotMatch(markup, /Refresh display/);
  assert.match(markup, /Install update/);
  assert.match(markup, /Download firmware/);
  assert.match(markup, /Firmware download version/);
  assert.ok(markup.includes('0.4.5'));

  dialog._openPicker('select', 'kitchen');
  const optionMarkup = collect(
    dialog._renderPicker('kitchen', null, dialog.deviceStatus.update),
  ).join(' ');
  assert.ok(optionMarkup.includes('Display (TFT)'));
  assert.match(optionMarkup, /Firmware/);
  assert.doesNotMatch(optionMarkup, /Install update/);

  const originalSetTimeout = globalThis.setTimeout;
  const originalOpen = window.open;
  const opened = [];
  window.open = (...args) => opened.push(args);
  globalThis.setTimeout = () => 0;
  try {
    await dialog._refreshDisplay();
    await dialog._downloadFirmware();
    assert.deepEqual(dialog._toast, {
      message: 'Downloading firmware 0.4.5',
      type: 'success',
    });
  } finally {
    globalThis.setTimeout = originalSetTimeout;
    window.open = originalOpen;
  }

  assert.deepEqual(opened, [['https://example.test/nspanel_haui.bin', '_blank']]);
  assert.deepEqual(calls.map(([path, options]) => [path, options.body ? JSON.parse(options.body) : undefined]), [
    ['/api/nspanel_haui/firmware', undefined],
    ['/api/nspanel_haui/refresh_display/entry1', { device: 'kitchen' }],
  ]);
  assert.deepEqual(dialog._toast, {
    message: 'Downloading firmware 0.4.5',
    type: 'success',
  });
});

test('toolbar reads its IP from the backend status without entity-id lookup', () => {
  const markup = collect(renderDeviceInfoStrip({
    _deviceStatus: {
      connected: true,
      connection_state: 'connected',
      current_page: 'home',
      device_info: { ip: '', ssid: 'HomeNet', rssi: -54 },
    },
    _selectedDevice: 'panel',
    _deviceStatusError: null,
    _actionsMenuIndex: null,
    narrow: false,
    hass: { states: { 'sensor.panel_ip': { state: '192.0.2.99' } } },
  })).join(' ');

  assert.doesNotMatch(markup, /192\.0\.2\.99/);
});
