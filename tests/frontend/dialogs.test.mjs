import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';

const DIALOGS = [
  'nspanel-dialog-edit-panel',
  'nspanel-dialog-confirm',
  'nspanel-dialog-device-config',
  'nspanel-dialog-device-info',
  'nspanel-dialog-logs',
  'nspanel-dialog-device-manager',
  'nspanel-dialog-colors',
];

/** A dialog instance without Lit's constructor (which needs a real DOM), recording its events. */
function dialog(tag, props = {}) {
  const dlg = Object.create(customElements.get(tag).prototype);
  const events = [];
  Object.assign(dlg, { requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

test('every editor dialog shares the dialog base class', () => {
  for (const tag of DIALOGS) {
    assert.ok(customElements.get(tag).prototype instanceof HauiDialog, tag);
  }
});

test('closing a dialog emits dialog-closed', () => {
  const { dlg, events } = dialog('nspanel-dialog-logs');
  dlg._dispatchClose();
  assert.deepEqual(events.map((e) => e.type), ['dialog-closed']);
});

function collectTemplateStrings(value, result = []) {
  if (typeof value === 'string') result.push(value);
  else if (Array.isArray(value)) value.forEach((item) => collectTemplateStrings(item, result));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collectTemplateStrings(value.strings, result);
    if (Array.isArray(value.values)) collectTemplateStrings(value.values, result);
  }
  return result;
}

test('the Device Manager offers firmware install only when HA reports an update', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: { kitchen: { config: {}, panels: [] } },
    selectedDevice: 'kitchen',
    _deviceMenuIndex: 0,
    _deviceStatuses: {
      kitchen: {
        device_info: { ip: '192.0.2.1' },
        update: { firmware_update_available: true },
      },
    },
    hass: {},
  });

  const labels = collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' ');
  assert.match(labels, /Install firmware/);

  dlg._deviceStatuses = {
    kitchen: { device_info: { ip: '192.0.2.1' }, update: { firmware_update_available: false } },
  };
  assert.doesNotMatch(
    collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' '),
    /Install firmware/,
  );
  dlg._deviceStatuses = {
    kitchen: {
      device_info: { ip: '192.0.2.1' },
      update: { firmware_update_available: true, firmware_installing: true },
    },
  };
  assert.match(
    collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' '),
    /Installing firmware/,
  );
});
test('the Device Manager keeps TFT install in the More menu when versions are unknown', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: { haui: { config: {}, panels: [] } },
    selectedDevice: 'haui',
    _deviceMenuIndex: 0,
    _deviceStatuses: { haui: { device_info: {} } },
    hass: { states: {} },
  });

  const labels = collectTemplateStrings(dlg._renderDeviceRow('haui')).join(' ');
  assert.match(labels, /Install TFT/);
  assert.match(labels, /Display Unknown/);
  assert.match(labels, /Firmware Unknown/);
});

test('the Device Manager emits add-device with the detail the editor handler reads', () => {
  const { dlg, events } = dialog('nspanel-dialog-device-manager', { devices: {}, _newDeviceName: 'office' });
  dlg._onAddDevice();
  assert.equal(events.length, 1);
  assert.equal(events[0].type, 'add-device');
  assert.deepEqual(events[0].detail, { device: { name: 'office', esphome_device_id: '' } });
});
