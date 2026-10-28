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

test('the Device Manager always offers firmware install and shows a running one', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: { kitchen: { config: {}, panels: [] } },
    selectedDevice: 'kitchen',
    _deviceMenuIndex: 0,
    _deviceStatuses: {
      kitchen: { device_info: { ip: '192.0.2.1' }, update: { firmware_update_available: false } },
    },
    hass: {},
  });

  // The picker installs older releases and URLs, so the item no longer
  // depends on an offered update.
  assert.match(collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' '), /Install firmware/);

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

function picker(kind, props = {}) {
  return dialog('nspanel-dialog-device-manager', {
    devices: { haui: { config: {}, panels: [] } },
    _picker: {
      kind,
      device: 'haui',
      releases: ['v0.4.2', 'v0.4.1'],
      releasesError: '',
      choice: '',
      url: '',
      error: '',
      ...props,
    },
  });
}

function releasesHass(urls, releases) {
  return {
    async fetchWithAuth(url) {
      urls.push(url);
      return { ok: true, status: 200, json: async () => ({ releases, required: '0.4.2', error: null }) };
    },
  };
}

test('the TFT picker offers the required version, the releases and a URL', () => {
  const { dlg } = picker('tft');
  const labels = collectTemplateStrings(dlg._renderPicker('haui', '0.4.2', {})).join(' ');
  assert.match(labels, /Version the firmware needs \(0\.4\.2\)/);
  assert.match(labels, /v0\.4\.1/);
  assert.match(labels, /From URL/);
});

test('the TFT picker loads the releases of the device', async () => {
  const urls = [];
  const { dlg } = picker('tft', {});
  Object.assign(dlg, { entryId: 'entry1', hass: releasesHass(urls, ['v0.4.2', 'v0.4.1']) });

  await dlg._openPicker('tft', 'haui');

  assert.deepEqual(urls, ['/api/nspanel_haui/tft_releases/entry1?device=haui']);
  assert.deepEqual(dlg._picker.releases, ['v0.4.2', 'v0.4.1']);
  assert.equal(dlg._picker.choice, '');
});

test('the TFT picker installs the required version by default', () => {
  const { dlg, events } = picker('tft');
  dlg._installFromPicker();
  assert.deepEqual(events.map((e) => [e.type, e.detail]), [['update-tft', { name: 'haui' }]]);
  assert.equal(dlg._picker, null);
});

test('the TFT picker installs an older release', () => {
  const { dlg, events } = picker('tft', { choice: 'v0.4.1' });
  dlg._installFromPicker();
  assert.deepEqual(events[0].detail, { name: 'haui', version: 'v0.4.1' });
});

test('the TFT picker installs from a URL', () => {
  const { dlg, events } = picker('tft', { choice: 'url', url: ' http://ha.local/nspanel_haui.tft ' });
  dlg._installFromPicker();
  assert.deepEqual(events[0].detail, { name: 'haui', url: 'http://ha.local/nspanel_haui.tft' });
});

test('the TFT picker rejects a URL that is not http(s)', () => {
  const { dlg, events } = picker('tft', { choice: 'url', url: 'ftp://ha.local/x.tft' });
  dlg._installFromPicker();
  assert.equal(events.length, 0);
  assert.equal(dlg._picker.error, 'Enter the http(s) URL of a .tft file');
});

test('the firmware picker offers the offered update, the releases and a URL', () => {
  const { dlg } = picker('firmware');
  const labels = collectTemplateStrings(dlg._renderPicker('haui', '0.4.2', {
    firmware_update_available: true, firmware_update_version: '0.4.3',
  })).join(' ');
  assert.match(labels, /Offered update \(0\.4\.3\)/);
  assert.match(labels, /v0\.4\.1/);
  assert.match(labels, /From URL/);
});

test('without an offered update the firmware picker preselects the newest release', async () => {
  const urls = [];
  const { dlg } = picker('firmware');
  Object.assign(dlg, { entryId: 'entry1', hass: releasesHass(urls, ['v0.4.3', 'v0.4.2']) });

  const opening = dlg._openPicker('firmware', 'haui', null);
  assert.equal(dlg._picker.choice, null);
  await opening;

  assert.deepEqual(urls, ['/api/nspanel_haui/firmware_releases/entry1?device=haui']);
  assert.equal(dlg._picker.choice, 'v0.4.3');
  const labels = collectTemplateStrings(dlg._renderPicker('haui', '0.4.2', {})).join(' ');
  assert.doesNotMatch(labels, /Offered update/);
});

test('the firmware picker installs an older release or a URL', () => {
  const release = picker('firmware', { choice: 'v0.4.2' });
  release.dlg._installFromPicker();
  assert.deepEqual(release.events.map((e) => [e.type, e.detail]), [['update-firmware', { name: 'haui', version: 'v0.4.2' }]]);

  const url = picker('firmware', { choice: 'url', url: 'http://ha.local/firmware.ota.bin' });
  url.dlg._installFromPicker();
  assert.deepEqual(url.events[0].detail, { name: 'haui', url: 'http://ha.local/firmware.ota.bin' });
});

test('the firmware picker installs nothing before a release is chosen', () => {
  const { dlg, events } = picker('firmware', { releases: null, choice: null });
  dlg._installFromPicker();
  assert.equal(events.length, 0);
});
