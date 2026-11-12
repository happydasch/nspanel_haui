import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { jsonResponse } from './fake-host.mjs';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';

const Editor = customElements.get('nspanel-haui-editor');

/** An editor instance without Lit's constructor, recording saves and API calls. */
function editor(previousModel, { saveOk = true } = {}) {
  const host = Object.create(Editor.prototype);
  Object.assign(host, {
    entryId: 'entry1',
    hass: {
      async fetchWithAuth(url, opts) {
        host.calls.push([url, JSON.parse(opts.body)]);
        return jsonResponse({ status: 'ok', devices_updated: ['kitchen'] });
      },
    },
    _selectedDevice: 'kitchen',
    _deviceConfig: { display_model: previousModel, update: { enabled: true } },
    _deviceConfigForm: { display_model: previousModel },
    _editingDeviceConfig: true,
    _saving: false,
    _tftInstallTarget: null,
    store: { actions: { closeOverlay() {} } },
    calls: [],
    toasts: [],
    _devicePanels() { return []; },
    async _savePanels(_panels, _message, config) {
      if (saveOk) host._deviceConfig = config;
      return saveOk;
    },
    _showToast(msg, kind) { this.toasts.push([kind, msg]); },
    requestUpdate() {},
  });
  host.api = createApiClient(() => host.hass);
  return host;
}

test('special-panel save feedback uses panel titles and splits the idle list into stored fields', async () => {
  const host = editor('landscape');
  host._deviceConfig = { home_panel: '', idle_panel: '', idle_panel_extra: '' };
  host._devicePanels = () => [
    { key: 'clock', title: 'Desk clock' }, { key: 'weather', title: 'Forecast' },
  ];
  const saves = [];
  host._savePanels = async (...args) => saves.push(args);

  await host._setSpecialPanel('idle_panels', 'clock, weather');
  assert.equal(saves[0][1], 'Idle panels set to "Desk clock, Forecast"');
  assert.deepEqual(saves[0][2], {
    home_panel: '', idle_panel: 'clock', idle_panel_extra: 'weather',
  });

  await host._setSpecialPanel('idle_panels', '');
  assert.equal(saves[1][1], 'Idle panels cleared');
  assert.deepEqual(saves[1][2], { home_panel: '', idle_panel: '', idle_panel_extra: '' });
});

test('changing the display model asks before installing the TFT', async () => {
  const host = editor('eu');

  await host._onDeviceConfigSave({
    detail: { config: { display_model: 'us', update: { enabled: true } } },
  });

  assert.equal(host._tftInstallTarget, 'kitchen');
  assert.equal(host._editingDeviceConfig, false);
  assert.deepEqual(host.calls, [], 'no TFT install runs before the answer');
});

test('saving other settings does not ask to install the TFT', async () => {
  const host = editor('eu');

  await host._onDeviceConfigSave({
    detail: { config: { display_model: 'eu', update: { enabled: true } } },
  });

  assert.equal(host._tftInstallTarget, null);
});

test('a failed save does not ask to install the TFT', async () => {
  const host = editor('eu', { saveOk: false });

  await host._onDeviceConfigSave({
    detail: { config: { display_model: 'us', update: { enabled: true } } },
  });

  assert.equal(host._tftInstallTarget, null);
});

test('a model change with updates disabled does not ask', async () => {
  const host = editor('eu');

  await host._onDeviceConfigSave({
    detail: { config: { display_model: 'us', update: { enabled: false } } },
  });

  assert.equal(host._tftInstallTarget, null);
});

test('confirming the question installs the matching TFT', async () => {
  const host = editor('eu');
  host._tftInstallTarget = 'kitchen';

  await host._confirmTftInstall();

  assert.equal(host._tftInstallTarget, null);
  assert.deepEqual(host.calls, [
    ['/api/nspanel_haui/update_tft/entry1', { device: 'kitchen' }],
  ]);
  assert.deepEqual(host.toasts.at(-1), ['success', 'TFT update started for "kitchen"']);
});

test('declining the question leaves the TFT alone', () => {
  const host = editor('eu');
  host._tftInstallTarget = 'kitchen';

  host._cancelTftInstall();

  assert.equal(host._tftInstallTarget, null);
  assert.deepEqual(host.calls, []);
});
