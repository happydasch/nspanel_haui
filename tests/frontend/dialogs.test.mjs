import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';

import { getColorScheme } from '../../custom_components/nspanel_haui/frontend/dialogs/colors.js';
import { hexToRgb565 } from '../../custom_components/nspanel_haui/frontend/color-utils.js';

const DIALOGS = [
  'nspanel-dialog-edit-panel',
  'nspanel-dialog-confirm',
  'nspanel-dialog-device-config',
  'nspanel-dialog-device-info',
  'nspanel-dialog-logs',
  'nspanel-dialog-device-manager',
  'nspanel-dialog-colors',
  'nspanel-dialog-live-preview',
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

test('color schemes build complete palettes from defaults', () => {
  const defaults = {
    header_background: 10,
    header_text: 20,
    background: 30,
    text: 40,
    component_background: 50,
    component_pressed: 60,
    component_active: 70,
  };

  assert.deepEqual(getColorScheme('dark', defaults), defaults);

  const light = getColorScheme('light', defaults);
  assert.equal(light.background, hexToRgb565('#ffffff'));
  assert.equal(light.text, hexToRgb565('#101010'));
  assert.equal(light.component_active, defaults.component_active);

  const black = getColorScheme('black', defaults);
  assert.equal(black.background, hexToRgb565('#000000'));
  assert.equal(black.component_background, hexToRgb565('#111111'));
  assert.equal(black.component_active, defaults.component_active);
  assert.throws(() => getColorScheme('unknown', defaults), /Unknown color scheme/);
});

test('color dialog applies a preset and marks edited palettes as custom', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  const defaults = { header_background: 1, background: 2, component_background: 3 };
  Object.assign(dlg, {
    open: true,
    overrides: {},
    hass: { fetchWithAuth: async () => ({ json: async () => defaults }) },
    _colors: {},
    _loading: false,
    requestUpdate() {},
  });

  dlg.willUpdate(new Map([['open', false]]));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(dlg._selectedScheme(), 'dark');

  dlg._applyScheme('black');
  assert.equal(dlg._selectedScheme(), 'black');
  dlg._onColorChange('background', { target: { value: '#123456' } });
  assert.equal(dlg._selectedScheme(), 'custom');
});

test('closing a dialog emits dialog-closed', () => {
  const { dlg, events } = dialog('nspanel-dialog-logs');
  dlg._dispatchClose();
  assert.deepEqual(events.map((e) => e.type), ['dialog-closed']);
});

test('Device Info places update actions beside the firmware version and redraw in Health', () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dlg = Object.create(DeviceInfo.prototype);
  Object.assign(dlg, {
    open: true,
    deviceName: 'kitchen',
    deviceStatus: {
      connected: true,
      connection_state: 'connected',
      current_page: 'home',
      device_info: {
        name: 'Kitchen',
        yaml_version: '0.4.2',
        tft_version: '1.2.3',
      },
      esphome: {
        transport: 'native_api',
        device_names: ['nspanel-kitchen'],
      },
      update: { enabled: true, firmware_update_version: '0.4.3' },
      active_listeners: [],
      active_timers: [],
    },
    _firmwareDownloadVersion: '0.4.5',
    _firmwareDownloadLoading: false,
    _actionBusy: false,
  });

  const rendered = dlg.render();
  const statusCard = rendered.values.find((value) =>
    value?.strings?.join(' ').includes('di-status-card'),
  );
  const deviceSection = rendered.values.find((value) =>
    value?.strings?.join(' ').includes('mdi:information-outline'),
  );
  const healthSection = rendered.values.find((value) =>
    value?.strings?.join(' ').includes('mdi:heart-pulse'),
  );
  assert.ok(statusCard);
  assert.ok(deviceSection);
  assert.ok(healthSection);
  const statusLabels = collectTemplateStrings(statusCard).join(' ');
  const deviceLabels = collectTemplateStrings(deviceSection).join(' ');
  assert.doesNotMatch(statusLabels, /Install update|Download firmware|Redraw display/);
  assert.match(deviceLabels, /Firmware Update Version/);
  assert.match(deviceLabels, /Firmware download version/);
  assert.match(deviceLabels, /0\.4\.5/);
  assert.match(deviceLabels, /0\.4\.3/);
  assert.match(deviceLabels, /Install update/);
  assert.match(deviceLabels, /Download firmware/);
  assert.match(deviceLabels, /Transport/);
  assert.match(deviceLabels, /native_api/);
  assert.match(deviceLabels, /Device Names/);
  assert.match(deviceLabels, /nspanel-kitchen/);
  assert.doesNotMatch(collectTemplateStrings(rendered).join(' '), /ESPHome/);
  assert.doesNotMatch(deviceLabels, /Redraw display/);
  assert.match(collectTemplateStrings(healthSection).join(' '), /Redraw display/);
  assert.doesNotMatch(collectTemplateStrings(healthSection).join(' '), /slot="secondaryAction"/);
  assert.doesNotMatch(collectTemplateStrings(rendered).join(' '), /slot="secondaryAction"/);
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

test('the Device Manager footer no longer offers a bulk display refresh', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: {},
    selectedDevice: null,
    entryId: null,
    open: true,
    _scannedDevices: [],
    _scanning: false,
    _scanError: '',
    _deviceStatuses: {},
    _toast: null,
    _removeTarget: null,
  });

  const labels = collectTemplateStrings(dlg.render()).join(' ');
  assert.doesNotMatch(labels, /Refresh all displays|Download firmware|Scan/);
});

test('opening Device Manager automatically scans for HAUI devices', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  let scans = 0;
  Object.assign(dlg, {
    open: true,
    _startStatusPolling() {},
    _stopStatusPolling() {},
    _onScan() { scans += 1; },
  });

  dlg.updated(new Map([['open', false]]));
  assert.equal(scans, 1);

  dlg.open = false;
  dlg.updated(new Map([['open', true]]));
  assert.equal(scans, 1);
});

test('the Device Manager shows update status but has no manual install action', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: { kitchen: { config: {}, panels: [] } },
    selectedDevice: 'kitchen',
    _deviceMenuIndex: 0,
    _deviceStatuses: {
      kitchen: {
        device_info: { ip: '192.0.2.1' },
        update: { firmware_update_available: true, firmware_installing: true },
      },
    },
    hass: {},
  });

  const labels = collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' ');
  assert.match(labels, /Installing firmware/);
  assert.doesNotMatch(labels, /Install update|From URL|From local file/);
});

test('Device Info always offers the full install picker, even without an update offer', () => {
  const { dlg } = dialog('nspanel-dialog-device-info', {
    deviceName: 'haui',
    deviceStatus: { device_info: {}, update: { enabled: true } },
    _picker: null,
  });

  assert.match(collectTemplateStrings(dlg.render()).join(' '), /Install update/);
  dlg._openPicker('select', 'haui');
  const choices = collectTemplateStrings(dlg._renderPicker('haui', null, { enabled: true })).join(' ');
  assert.match(choices, /Choose update type/);
  assert.ok(choices.includes('Display (TFT)'));
  assert.match(choices, /Firmware/);
});

test('the Device Info install picker is unavailable when updates are disabled', async () => {
  const { dlg } = dialog('nspanel-dialog-device-info', {
    deviceName: 'haui',
    deviceStatus: { device_info: {}, update: { enabled: false } },
    _picker: null,
  });

  await dlg._openPicker('select', 'haui');
  assert.equal(dlg._picker, null);
  const disabled = collectTemplateStrings(dlg._renderPicker('haui', null, { enabled: false })).join(' ');
  assert.match(disabled, /Updates are disabled for this device/);
  assert.doesNotMatch(disabled, /Choose update type/);
});

test('the Device Manager keeps update installation out of the More menu when versions are unknown', () => {
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
  assert.doesNotMatch(labels, /Install update/);
  assert.match(labels, /Display Unknown/);
  assert.match(labels, /Firmware Unknown/);
});

test('the Device Manager compares TFT status with the required TFT version', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: { kitchen: { config: {}, panels: [] } },
    selectedDevice: 'kitchen',
    _deviceMenuIndex: -1,
    hass: {},
  });

  dlg._deviceStatuses = {
    kitchen: {
      device_info: {
        yaml_version: '0.4.4',
        tft_required_version: '0.4.3',
        tft_version: '0.4.3',
      },
    },
  };
  let labels = collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' ');
  assert.match(labels, /Firmware 0\.4\.4/);
  assert.match(labels, /Display 0\.4\.3/);
  assert.doesNotMatch(labels, /update pending/);

  dlg._deviceStatuses.kitchen.device_info.tft_version = '0.4.2';
  labels = collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' ');
  assert.match(labels, /update pending/);
});

test('the Device Manager does not infer a required TFT version from firmware version', () => {
  const DeviceManager = customElements.get('nspanel-dialog-device-manager');
  const dlg = Object.create(DeviceManager.prototype);
  Object.assign(dlg, {
    devices: { kitchen: { config: {}, panels: [] } },
    selectedDevice: 'kitchen',
    _deviceMenuIndex: -1,
    hass: {},
    _deviceStatuses: {
      kitchen: {
        device_info: {
          yaml_version: '0.4.5.dev13+g5c57c0',
          tft_version: '0.4.3',
        },
      },
    },
  });

  const labels = collectTemplateStrings(dlg._renderDeviceRow('kitchen')).join(' ');
  assert.match(labels, /Display 0\.4\.3/);
  assert.doesNotMatch(labels, /update pending/);
});

/** The row menu's items as `{ label: disabled }`. */
function menuItems(value, result = {}) {
  if (Array.isArray(value)) value.forEach((item) => menuItems(item, result));
  else if (value && typeof value === 'object' && Array.isArray(value.values)) {
    if (value.strings.join('').includes('device-mgr-dropdown-item')) {
      result[value.values[4]] = Boolean(value.values[1]);
    }
    menuItems(value.values, result);
  }
  return result;
}

test('a disabled device offers no action that needs its running app', () => {
  const { dlg } = dialog('nspanel-dialog-device-manager', {
    devices: { kitchen: { config: { enabled: false }, panels: [] } },
    _deviceMenuIndex: 0,
    _deviceStatuses: {},
  });

  const items = menuItems(dlg._renderDeviceRow('kitchen'));
  assert.equal(items['Install update'], undefined);
  for (const label of ['Redraw display', 'Install TFT', 'Install firmware', 'Check for updates']) {
    assert.equal(items[label], undefined, label);
  }
  for (const label of ['Enable', 'Settings', 'Remove']) {
    assert.equal(items[label], false, label);
  }
});

/** Click the row menu item labelled `label`. */
function clickMenuItem(value, label) {
  if (Array.isArray(value)) return value.some((item) => clickMenuItem(item, label));
  if (!value || typeof value !== 'object' || !Array.isArray(value.values)) return false;
  if (value.strings.join('').includes('device-mgr-dropdown-item') && value.values[4] === label) {
    value.values[2]({ stopPropagation() {} });
    return true;
  }
  return clickMenuItem(value.values, label);
}

test('Remove asks for confirmation before the device is removed', () => {
  const { dlg, events } = dialog('nspanel-dialog-device-manager', {
    devices: { kitchen: { config: {}, panels: [], friendly_name: 'Kitchen Panel' } },
    _deviceMenuIndex: 0,
    _deviceStatuses: {},
  });

  assert.ok(clickMenuItem(dlg._renderDeviceRow('kitchen'), 'Remove'));
  assert.equal(events.length, 0);
  assert.equal(dlg._removeTarget, 'kitchen');
  assert.match(dlg._removeParams.message, /Remove Kitchen Panel from the hub\?/);

  dlg._confirmRemove();
  assert.deepEqual(events.map((e) => [e.type, e.detail]), [['remove-device', { name: 'kitchen' }]]);
  assert.equal(dlg._removeTarget, null);
  assert.equal(dlg._removeParams, null);
});

test('closing the Device Manager drops a removal waiting for confirmation', () => {
  const { dlg, events } = dialog('nspanel-dialog-device-manager', {
    devices: { kitchen: { config: {}, panels: [] } },
    _removeTarget: 'kitchen',
    open: false,
  });

  dlg.updated(new Map([['open', true]]));

  assert.equal(dlg._removeTarget, null);
  assert.equal(events.length, 0);
});

test('the TFT picker of Device Info names the required TFT version, not the firmware version', () => {
  const { dlg } = picker('tft', { releases: [] });
  dlg.deviceStatus.device_info.tft_required_version = '0.4.3';
  const labels = collectTemplateStrings(
    dlg._renderPicker('haui', dlg.deviceStatus.device_info.tft_required_version, {}),
  ).join(' ');
  assert.ok(labels.includes('Version the firmware needs (0.4.3)'));
});

test('the TFT picker does not list the required version twice', () => {
  const { dlg } = picker('tft', { releases: ['0.4.2'] });
  const strings = collectTemplateStrings(dlg._renderPicker('haui', '0.4.2', {}));
  assert.ok(strings.includes('Version the firmware needs (0.4.2)'));
  assert.ok(!strings.includes('0.4.2'));
});

test('scan results leave out devices that are already configured', () => {
  const { dlg, events } = dialog('nspanel-dialog-device-manager', {
    devices: { kitchen: { config: {}, panels: [] } },
    _deviceStatuses: {},
    _scannedDevices: [{ name: 'kitchen' }, { name: 'office' }],
    _scanError: '',
  });

  const labels = collectTemplateStrings(dlg.render()).join(' ');
  assert.match(labels, /Discovered Devices/);
  assert.match(labels, /office/);

  dlg.devices = { ...dlg.devices, office: { config: {}, panels: [] } };
  assert.doesNotMatch(collectTemplateStrings(dlg.render()).join(' '), /Discovered Devices/);
  assert.equal(events.length, 0);
});

function picker(kind, props = {}) {
  return dialog('nspanel-dialog-device-info', {
    deviceName: 'haui',
    deviceStatus: { device_info: {}, update: { enabled: true } },
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
  assert.match(labels, /From local file/);
  assert.match(labels, /From local file/);
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

test('the TFT picker selects the available TFT when firmware has no required version', async () => {
  const { dlg, events } = picker('tft');
  Object.assign(dlg, {
    entryId: 'entry1',
    hass: {
      async fetchWithAuth() {
        return {
          ok: true,
          status: 200,
          json: async () => ({ releases: ['0.4.5'], required: null, error: null }),
        };
      },
    },
    deviceStatus: { device_info: { yaml_version: '0.4.5' }, update: { enabled: true } },
  });

  await dlg._openPicker('tft', 'haui');

  assert.equal(dlg._picker.choice, '0.4.5');
  dlg._installFromPicker();
  assert.deepEqual(events.map((e) => [e.type, e.detail]), [
    ['update-tft', { name: 'haui', version: '0.4.5' }],
  ]);
});

test('the TFT picker falls back to a URL when firmware has no requirement or manifest TFT', async () => {
  const { dlg } = picker('tft');
  Object.assign(dlg, {
    entryId: 'entry1',
    hass: {
      async fetchWithAuth() {
        return {
          ok: true,
          status: 200,
          json: async () => ({ releases: [], required: null, error: 'No TFT in manifest' }),
        };
      },
    },
    deviceStatus: { device_info: {}, update: { enabled: true } },
  });

  await dlg._openPicker('tft', 'haui');

  assert.equal(dlg._picker.choice, 'url');
});

test('the TFT picker offers URL installation when the required TFT is not in the manifest', async () => {
  const { dlg } = picker('tft');
  Object.assign(dlg, {
    entryId: 'entry1',
    hass: {
      async fetchWithAuth() {
        return {
          ok: true,
          status: 200,
          json: async () => ({ releases: [], required: '0.4.5', error: 'No TFT in manifest' }),
        };
      },
    },
    deviceStatus: { device_info: { tft_required_version: '0.4.5' }, update: { enabled: true } },
  });

  await dlg._openPicker('tft', 'haui');

  assert.equal(dlg._picker.choice, 'url');
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

test('the TFT picker uploads a selected local .tft file', () => {
  const file = { name: 'custom.tft' };
  const { dlg, events } = picker('tft', { choice: 'file', file });

  const labels = collectTemplateStrings(dlg._renderPicker('haui', '0.4.2', {})).join(' ');
  dlg._installFromPicker();

  assert.match(labels, /Local TFT file/);
  assert.match(labels, /uploaded to Home Assistant/);
  assert.equal(dlg._picker.uploading, true);
  dlg._finishLocalUpload();
  assert.equal(dlg._picker, null);
  assert.deepEqual(events.map((e) => [e.type, e.detail]), [
    ['update-tft', { name: 'haui', file }],
  ]);
});

test('the TFT picker requires a .tft file before install', () => {
  const { dlg, events } = picker('tft', { choice: 'file', file: { name: 'wrong.bin' } });
  dlg._installFromPicker();
  assert.equal(events.length, 0);
  assert.equal(dlg._picker.error, 'Choose a Nextion TFT file (.tft)');
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

test('the firmware picker uploads a selected local OTA image', () => {
  const file = { name: 'nspanel_haui_ota.bin' };
  const { dlg, events } = picker('firmware', { choice: 'file', file });

  const labels = collectTemplateStrings(dlg._renderPicker('haui', '0.4.2', {})).join(' ');
  dlg._installFromPicker();

  assert.match(labels, /Local firmware OTA image/);
  assert.deepEqual(events.map((e) => [e.type, e.detail]), [
    ['update-firmware', { name: 'haui', file }],
  ]);
});

test('the firmware picker installs nothing before a release is chosen', () => {
  const { dlg, events } = picker('firmware', { releases: null, choice: null });
  dlg._installFromPicker();
  assert.equal(events.length, 0);
});
