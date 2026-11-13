import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

import { hexToRgb565 } from '../../custom_components/nspanel_haui/frontend/color-utils.js';
import { openThemeSidebar, saveTheme } from '../../custom_components/nspanel_haui/frontend/theme-editor.js';
import { filterLogEntries, logEntries, logText } from '../../custom_components/nspanel_haui/frontend/dialogs/logs.js';

const DIALOGS = [
  'nspanel-panel-editor',
  'nspanel-dialog-confirm',
  'nspanel-device-settings',
  'nspanel-firmware-popover',
  'nspanel-logs-sidebar',
  'nspanel-theme-sidebar',
];

/** A dialog instance without Lit's constructor (which needs a real DOM), recording its events. */
function dialog(tag, props = {}) {
  const dlg = document.createElement(tag);
  const events = [];
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass), requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

function collectTemplateStrings(value, result = []) {
  if (typeof value === 'string') result.push(value);
  else if (Array.isArray(value)) value.forEach((item) => collectTemplateStrings(item, result));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collectTemplateStrings(value.strings, result);
    if (Array.isArray(value.values)) collectTemplateStrings(value.values, result);
  }
  return result;
}

test('the TFT picker names the required TFT version, not the firmware version', () => {
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

function picker(kind, props = {}) {
  return dialog('nspanel-firmware-popover', {
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
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass), entryId: 'entry1', hass: releasesHass(urls, ['v0.4.2', 'v0.4.1']) });

  await dlg._openPicker('tft', 'haui');

  assert.deepEqual(urls, ['/api/nspanel_haui/tft_releases/entry1?device=haui']);
  assert.deepEqual(dlg._picker.releases, ['v0.4.2', 'v0.4.1']);
  assert.equal(dlg._picker.choice, '');
});

test('the TFT picker selects the available TFT when firmware has no required version', async () => {
  const { dlg, events } = picker('tft');
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
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
    api: createApiClient(() => dlg.hass),
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
    api: createApiClient(() => dlg.hass),
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
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass), entryId: 'entry1', hass: releasesHass(urls, ['v0.4.3', 'v0.4.2']) });

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
