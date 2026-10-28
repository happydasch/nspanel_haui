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
  assert.doesNotMatch(markup, /NaN/);
  assert.doesNotMatch(markup, /mdi:wifi-off/);
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
