import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

import { getTheme } from '../../custom_components/nspanel_haui/frontend/dialogs/theme.js';
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

test('the firmware popover leads with its status, then versions, then settings', () => {
  const { dlg } = dialog('nspanel-firmware-popover', {
    open: true,
    deviceName: 'kitchen',
    deviceStatus: {
      connected: true,
      integration_version: '0.4.2',
      device_info: { name: 'Kitchen', yaml_version: '0.4.1', tft_version: '1.2.3' },
      update: { enabled: true, firmware_update_version: '0.4.3' },
    },
    config: { update: { enabled: true } },
    _actionBusy: false,
  });

  const markup = collectTemplateStrings(dlg.render()).join(' ');
  const status = markup.indexOf('haui-firmware-hero');
  const versions = markup.indexOf('haui-firmware-versions');
  const settings = markup.indexOf('haui-firmware-settings');
  assert.ok(status >= 0);
  assert.ok(versions > status);
  assert.ok(settings > versions);
  assert.equal(rowInstallActions(dlg.render()).length, 2);
  assert.doesNotMatch(markup, /Install update|Download firmware|Firmware download version/);
  assert.match(markup, /0\.4\.3/);
  assert.match(markup, /Integration/);
  assert.match(markup, /Firmware/);
  assert.ok(markup.includes('0.4.2'));
  assert.ok(markup.includes('0.4.1'));
  assert.doesNotMatch(markup, /Redraw display|Listeners/);
});

test('Redraw display calls the hub for the selected device', async () => {
  const calls = [];
  const host = document.createElement('nspanel-haui-editor');
  Object.assign(host, {
    entryId: 'entry1',
    _showToast(message, kind) { host.toasts.push([kind, message]); },
    toasts: [],
    hass: {
      async fetchWithAuth(path, options) {
        calls.push([path, options]);
        return { ok: true, json: async () => ({ status: 'ok', device: 'kitchen' }) };
      },
    },
  });
  host.api = createApiClient(() => host.hass);

  await host._redrawDisplay('kitchen');

  assert.deepEqual(
    calls.map(([path, options]) => [path, JSON.parse(options.body)]),
    [['/api/nspanel_haui/refresh_display/entry1', { device: 'kitchen' }]],
  );
  assert.deepEqual(host.toasts, [['success', 'Display refreshed for "kitchen"']]);
});

test('the install picker opens below the update settings in the popover', () => {
  const { dlg } = dialog('nspanel-firmware-popover', {
    open: true,
    deviceStatus: { device_info: {}, update: { enabled: true } },
    deviceName: 'kitchen',
    entryId: 'entry1',
    config: { update: { enabled: true } },
    _picker: {
      kind: 'firmware', device: 'kitchen', releases: [], releasesError: '', choice: '',
      url: '', file: null, error: '',
    },
    _actionBusy: false,
  });

  const markup = collectTemplateStrings(dlg.render()).join(' ');
  const settingsIndex = markup.indexOf('haui-firmware-settings');
  const pickerIndex = markup.indexOf('haui-update-picker');
  assert.ok(settingsIndex >= 0);
  assert.ok(pickerIndex > settingsIndex);
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

function rowInstallActions(value, result = []) {
  if (Array.isArray(value)) value.forEach((item) => rowInstallActions(item, result));
  else if (value && typeof value === 'object' && Array.isArray(value.strings) && Array.isArray(value.values)) {
    const clickIndex = value.strings.findIndex((part) => part.includes('@click='));
    if (clickIndex >= 0 && value.strings.join('').includes('mdi:download')) {
      result.push({
        onClick: value.values[clickIndex],
        disabled: value.values[2],
        ariaLabel: value.values[3],
      });
    }
    value.values.forEach((item) => rowInstallActions(item, result));
  }
  return result;
}

test('each firmware version row opens its matching install picker', async () => {
  const { dlg, events } = dialog('nspanel-firmware-popover', {
    open: true,
    deviceName: 'haui',
    entryId: 'entry1',
    deviceStatus: {
      integration_version: '0.4.2',
      device_info: { tft_version: '1.2.3', tft_required_version: '1.2.4' },
      update: { enabled: true, firmware_update_available: true, tft_update_available: true },
    },
    api: {
      updates: {
        firmwareReleases: async () => ({ releases: ['0.4.5'] }),
        tftReleases: async () => ({ releases: ['1.2.4', '1.2.3'], required: '1.2.4' }),
      },
    },
    _picker: null,
    _actionBusy: false,
  });

  const actions = rowInstallActions(dlg.render());
  assert.equal(actions.length, 2);
  assert.deepEqual(actions.map(({ ariaLabel }) => ariaLabel), ['Install Firmware', 'Install Display (TFT)']);
  assert.ok(actions.every(({ disabled }) => !disabled));

  await actions[0].onClick();
  assert.equal(dlg._picker.kind, 'firmware');
  assert.equal(dlg._picker.choice, '');
  dlg._updatePicker({ choice: '0.4.5' });
  dlg._installFromPicker();

  const displayAction = rowInstallActions(dlg.render())[1];
  await displayAction.onClick();
  assert.equal(dlg._picker.kind, 'tft');
  assert.equal(dlg._picker.choice, '');
  dlg._updatePicker({ choice: '1.2.3' });
  dlg._installFromPicker();

  assert.deepEqual(events.map((event) => [event.type, event.detail]), [
    ['update-firmware', { name: 'haui', version: '0.4.5' }],
    ['update-tft', { name: 'haui', version: '1.2.3' }],
  ]);
});

test('firmware row actions are unavailable when updates are disabled or busy', async () => {
  const { dlg } = dialog('nspanel-firmware-popover', {
    open: true,
    deviceName: 'haui',
    deviceStatus: { device_info: {}, update: { enabled: false } },
    _picker: null,
  });

  assert.equal(rowInstallActions(dlg.render()).length, 0);
  await dlg._openPicker('firmware', 'haui');
  assert.equal(dlg._picker, null);
  const disabled = collectTemplateStrings(dlg._renderPicker('haui', null, { enabled: false })).join(' ');
  assert.match(disabled, /Updates are disabled for this device/);

  dlg.deviceStatus.update = { enabled: true, state: 'checking' };
  dlg._actionBusy = true;
  assert.equal(rowInstallActions(dlg.render()).length, 2);
  assert.ok(rowInstallActions(dlg.render()).every(({ disabled }) => disabled));
  await dlg._openPicker('tft', 'haui');
  assert.equal(dlg._picker, null);
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
