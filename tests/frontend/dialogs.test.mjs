import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';

import { getColorScheme } from '../../custom_components/nspanel_haui/frontend/dialogs/colors.js';
import { hexToRgb565 } from '../../custom_components/nspanel_haui/frontend/color-utils.js';
import { openColorsDialog, saveColors } from '../../custom_components/nspanel_haui/frontend/colors-editor.js';

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

test('color schemes read complete palettes from the backend scheme catalog', () => {
  const dark = { background: 10, text: 20 };
  const light = { background: hexToRgb565('#ffffff'), text: hexToRgb565('#101010') };
  const schemes = { dark: { colors: dark }, light: { colors: light } };

  assert.deepEqual(getColorScheme('dark', schemes), dark);
  assert.deepEqual(getColorScheme('light', schemes), light);
  assert.throws(() => getColorScheme('unknown', schemes), /Unknown color scheme/);
});

test('color dialog loads schemes, switches palette, and edits custom definitions', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  const builtins = {
    dark: { name: 'Dark', colors: { background: 2 }, icons: { weather: { default: 3 }, alarm: { armed: 4 }, climate: { off: 5 } } },
    light: { name: 'Light', colors: { background: 6 }, icons: { weather: { default: 7 }, alarm: { armed: 8 }, climate: { off: 9 } } },
    black: { name: 'Black', colors: { background: 10 }, icons: { weather: { default: 11 }, alarm: { armed: 12 }, climate: { off: 13 } } },
  };
  Object.assign(dlg, {
    open: true,
    entryId: 'entry',
    schemeId: 'dark',
    overrides: {},
    scheme: 'dark',
    hass: { fetchWithAuth: async (url) => url.endsWith('color_defaults')
      ? { json: async () => ({ background: 2 }) }
      : { ok: true, json: async () => ({ builtins, schemes: {} }) } },
    _colors: {},
    _loading: false,
    requestUpdate() {},
  });

  dlg.willUpdate(new Map([['open', false]]));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(dlg._selectedScheme(), 'dark');
  dlg._applyScheme('black');
  assert.equal(dlg._selectedScheme(), 'black');
  assert.equal(dlg._colors.background, 10);
});
test('color dialog keeps its open ha-dialog mounted while schemes load', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  const dark = { name: 'Dark', colors: {}, icons: { dark: {}, light: {} } };
  Object.assign(dlg, {
    hass: {
      fetchWithAuth: async (url) => url.endsWith('color_defaults')
        ? { json: async () => ({}) }
        : { ok: true, json: async () => ({ builtins: { dark }, schemes: {} }) },
    },
    open: true,
    entryId: 'entry',
    schemeId: 'dark',
    scheme: 'dark',
    _loading: true,
    _schemes: {},
    _builtins: {},
    _customSchemes: {},
    requestUpdate() {},
    _changedCount: () => 0,
    _renderPreview: () => '',
    _selectedScheme: () => 'dark',
    _isBuiltin: () => true,
    _legacyOverrideCount: () => 0,
    _renderGroup: () => '',
    _schemeData: () => dark,
  });

  const loadingTemplate = dlg.render();
  await dlg._loadSchemes();
  const loadedTemplate = dlg.render();

  assert.deepEqual(loadingTemplate.strings, loadedTemplate.strings);
  assert.equal(loadingTemplate.strings.join('').match(/<ha-dialog/g)?.length, 1);
});


test('saving a color scheme persists its active ID and can clear legacy overrides', async () => {
  let savedConfig;
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: { color_overrides: { background: 123 } },
    _devicePanels: () => [],
    _savePanels: async (_panels, _message, config) => {
      savedConfig = config;
      return true;
    },
    requestUpdate() {},
  };

  await saveColors(host, { schemeId: 'custom-theme', resetOverrides: true });

  assert.equal(savedConfig.color_scheme_id, 'custom-theme');
  assert.deepEqual(savedConfig.color_overrides, {});
});

test('opening the color dialog selects the saved scheme and icon variant', () => {
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: { color_overrides: {} },
    _panels: { devices: { panel: { config: { color_scheme_id: 'evening', color_scheme: 'light' } } } },
    _loadDeviceConfig() {},
    requestUpdate() {},
  };

  openColorsDialog(host);

  assert.equal(host._colorsSchemeId, 'evening');
  assert.equal(host._colorsScheme, 'light');
  assert.equal(host._showColorsDialog, true);
});
test('the color dialog marks the saved scheme as selected in its options', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  const icons = {
    dark: { weather: { sunny: 20 }, alarm: { armed: 21 }, climate: { off: 22 } },
    light: { weather: { sunny: 30 }, alarm: { armed: 31 }, climate: { off: 32 } },
  };
  const builtins = {
    dark: { name: 'Dark', colors: { background: 2 }, icons },
    light: { name: 'Light', colors: { background: 6 }, icons },
  };
  Object.assign(dlg, {
    open: true,
    entryId: 'entry',
    schemeId: 'evening',
    overrides: {},
    panels: [],
    scheme: 'dark',
    hass: {
      fetchWithAuth: async (url) => url.endsWith('color_defaults')
        ? { json: async () => ({ background: 2 }) }
        : { ok: true, json: async () => ({ builtins, schemes: { evening: { name: 'Evening', colors: { background: 10 }, icons } } }) },
    },
    _colors: {},
    _loading: true,
    requestUpdate() {},
  });

  await dlg._loadSchemes();

  const options = optionTemplates(dlg.render()).map((tpl) => ({
    value: tpl.values[0],
    selected: tpl.values[1],
  }));
  assert.deepEqual(options, [
    { value: 'dark', selected: false },
    { value: 'light', selected: false },
    { value: 'evening', selected: true },
  ]);
});

/** The dynamically bound `<option>` templates of the scheme selector. */
function optionTemplates(value, result = []) {
  if (Array.isArray(value)) value.forEach((item) => optionTemplates(item, result));
  else if (value && typeof value === 'object' && Array.isArray(value.values)) {
    if (value.values.length === 3 && value.strings.join('').includes('<option value=')) {
      result.push(value);
    }
    optionTemplates(value.values, result);
  }
  return result;
}

test('changing a color of a built-in scheme switches to a custom copy and saves it', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  const icons = {
    dark: { weather: { sunny: 20 }, alarm: { armed: 21 }, climate: { off: 22 } },
    light: { weather: { sunny: 30 }, alarm: { armed: 31 }, climate: { off: 32 } },
  };
  const dark = { name: 'Dark', colors: { background: 10, text: 20 }, icons };
  Object.assign(dlg, {
    scheme: 'dark',
    schemeId: 'dark',
    _schemes: { dark },
    _builtins: { dark },
    _customSchemes: {},
    _colors: { background: 10, text: 20 },
    _icons: JSON.parse(JSON.stringify(icons)),
    _edited: false,
    _schemeError: '',
    _schemeNotice: '',
    _autoSchemeId: '',
    _keepSchemeColors: false,
    _resetOverrides: false,
    requestUpdate() {},
  });

  dlg._onColorChange('background', { target: { value: '#ff0000' } });

  assert.equal(dlg.schemeId, 'dark-custom');
  assert.equal(dlg._isBuiltin(), false);
  assert.equal(dlg._schemes['dark-custom'].name, 'Dark (custom)');
  assert.equal(dlg._colors.background, hexToRgb565('#ff0000'));
  assert.match(dlg._schemeNotice, /Dark \(custom\)/);
  assert.equal(dlg._edited, true);

  dlg.willUpdate(new Map([['schemeId', 'dark']]));
  assert.equal(dlg._colors.background, hexToRgb565('#ff0000'));
  assert.equal(dlg._edited, true);

  let persisted;
  dlg._persistSchemes = async (schemes) => { persisted = schemes; return true; };
  let emitted;
  dlg._emit = (type, detail) => { emitted = { type, detail }; };
  await dlg._dispatchSave();
  assert.equal(persisted['dark-custom'].name, 'Dark (custom)');
  assert.equal(persisted['dark-custom'].colors.background, hexToRgb565('#ff0000'));
  assert.equal(emitted.detail.schemeId, 'dark-custom');

  dlg._applyScheme('dark');
  assert.equal(dlg._schemes['dark-custom'], undefined);
  assert.equal(dlg._schemeNotice, '');
});



test('color scheme JSON import rejects collisions and persists valid collections', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  const colors = Object.fromEntries([
    'header_background', 'header_text', 'header_accent', 'background', 'text',
    'text_inactive', 'text_disabled', 'component_text', 'component_pressed',
    'component_active', 'component_active_dark', 'component_accent',
    'component_background', 'entity_on', 'entity_off', 'entity_unavailable',
  ].map((key, index) => [key, index]));
  const iconPalette = {
    weather: Object.fromEntries([
      'default', 'clear_night', 'sunny', 'partlycloudy', 'windy', 'windy_variant',
      'rainy', 'pouring', 'lightning', 'lightning_rainy', 'hail', 'snowy', 'snowy_rainy',
    ].map((key, index) => [key, index])),
    alarm: { armed: 1, disarmed: 2, arming: 3 },
    climate: { auto: 1, heat_cool: 2, heat: 3, off: 4, cool: 5, dry: 6, fan_only: 7 },
  };
  const eveningScheme = {
    name: 'Evening',
    colors,
    icons: { dark: iconPalette, light: JSON.parse(JSON.stringify(iconPalette)) },
  };
  const darkScheme = { ...eveningScheme, name: 'Dark' };

  const custom = { evening: eveningScheme };
  let posted;
  Object.assign(dlg, {
    entryId: 'entry',
    schemeId: 'dark',
    _schemes: { dark: darkScheme },
    _builtins: { dark: darkScheme },
    _colors: { ...colors },
    _icons: { dark: iconPalette, light: JSON.parse(JSON.stringify(iconPalette)) },
    _customSchemes: {},
    _schemeError: '',
    hass: {
      fetchWithAuth: async (_url, options) => {
        posted = JSON.parse(options.body).schemes;
        return { ok: true, json: async () => ({ schemes: posted }) };
      },
    },
    requestUpdate() {},
  });

  await dlg._importSchemes({ target: { files: [{ text: async () => JSON.stringify({ version: 1, schemes: custom }) }], value: 'file' } });
  assert.equal(posted.evening.name, 'Evening');
  assert.equal(dlg._customSchemes.evening.name, 'Evening');

  await dlg._importSchemes({ target: { files: [{ text: async () => JSON.stringify({ version: 1, schemes: custom }) }], value: 'file' } });
  assert.match(dlg._schemeError, /already exists/);
  assert.equal(posted.evening.name, 'Evening');
});




test('custom color schemes can be saved, renamed, exported, and deleted', async () => {
  const ColorsDialog = customElements.get('nspanel-dialog-colors');
  const dlg = Object.create(ColorsDialog.prototype);
  let current;
  const darkScheme = {
    name: 'Dark',
    colors: { background: 10 },
    icons: { dark: { weather: { sunny: 20 } }, light: { weather: { sunny: 30 } } },
  };
  Object.assign(dlg, {
    entryId: 'entry',
    schemeId: 'dark',
    _schemes: { dark: darkScheme },
    _builtins: { dark: darkScheme },
    _customSchemes: {},
    _colors: { background: 10 },
    _icons: { dark: { weather: { sunny: 20 } }, light: { weather: { sunny: 30 } } },
    _nameAction: 'save-as',
    _schemeName: 'Evening',
    _schemeError: '',
    _resetOverrides: false,
    requestUpdate() {},
    hass: {
      fetchWithAuth: async (_url, options) => {
        current = JSON.parse(options.body).schemes;
        return { ok: true, json: async () => ({ schemes: current }) };
      },
    },
  });

  await dlg._saveNamedScheme();
  assert.equal(dlg.schemeId, 'evening');
  assert.equal(dlg._customSchemes.evening.name, 'Evening');

  dlg._startNameAction('rename');
  dlg._schemeName = 'Evening v2';
  await dlg._saveNamedScheme();
  assert.equal(dlg._customSchemes.evening.name, 'Evening v2');

  const originalCreate = URL.createObjectURL;
  const originalRevoke = URL.revokeObjectURL;
  const originalCreateElement = document.createElement;
  let exportedBlob;
  let clicked = false;
  URL.createObjectURL = (blob) => { exportedBlob = blob; return 'blob:schemes'; };
  URL.revokeObjectURL = () => {};
  document.createElement = () => ({ click() { clicked = true; } });
  try {
    dlg._exportSchemes();
    assert.equal(clicked, true);
    assert.deepEqual(JSON.parse(await exportedBlob.text()).schemes, dlg._customSchemes);
  } finally {
    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
    document.createElement = originalCreateElement;
  }

  await dlg._deleteScheme();
  assert.equal(Object.hasOwn(dlg._customSchemes, 'evening'), false);
  assert.equal(dlg.schemeId, 'dark');
});
test('applying a scheme clears legacy page-specific color overrides', async () => {
  let savedPanels;
  let savedConfig;
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: { color_overrides: { background: 65535 } },
    _devicePanels: () => [{
      type: 'grid',
      items: [{ text_color: 123, back_color: 456, color: 789 }],
      keypad_bg_color: 42,
      off_color: 11,
    }],
    _savePanels: async (panels, _message, config) => {
      savedPanels = panels;
      savedConfig = config;
      return true;
    },
    requestUpdate() {},
  };

  await saveColors(host, { schemeId: 'dark', resetOverrides: true, scheme: 'dark' });

  assert.deepEqual(savedConfig.color_overrides, {});
  assert.equal('text_color' in savedPanels[0].items[0], false);
  assert.equal('back_color' in savedPanels[0].items[0], false);
  assert.equal(savedPanels[0].items[0].color, 789);
  assert.equal('keypad_bg_color' in savedPanels[0], false);
  assert.equal('off_color' in savedPanels[0], false);
});
test('closing a dialog emits dialog-closed', () => {
  const { dlg, events } = dialog('nspanel-dialog-logs');
  dlg._dispatchClose();
  assert.deepEqual(events.map((e) => e.type), ['dialog-closed']);
});

test('Device Info groups the versions in one grid and update actions below them', () => {
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
  assert.match(collectTemplateStrings(healthSection).join(' '), /Reset interaction timer/);
  assert.doesNotMatch(collectTemplateStrings(healthSection).join(' '), /slot="secondaryAction"/);
  assert.doesNotMatch(collectTemplateStrings(rendered).join(' '), /slot="secondaryAction"/);
});

test('Device Info resets the selected device interaction timer', async () => {
  const calls = [];
  const { dlg } = dialog('nspanel-dialog-device-info', {
    deviceName: 'kitchen',
    entryId: 'entry1',
    hass: {
      async fetchWithAuth(path, options) {
        calls.push([path, options]);
        return { ok: true, json: async () => ({ status: 'ok', device: 'kitchen' }) };
      },
    },
    _actionBusy: false,
  });
  const originalSetTimeout = globalThis.setTimeout;
  globalThis.setTimeout = () => 0;
  try {
    await dlg._resetInteractionTimer();
  } finally {
    globalThis.setTimeout = originalSetTimeout;
  }

  assert.deepEqual(
    calls.map(([path, options]) => [path, JSON.parse(options.body)]),
    [['/api/nspanel_haui/reset_interaction/entry1', { device: 'kitchen' }]],
  );
  assert.equal(dlg._toast.message, 'Interaction timer reset');
  assert.equal(dlg._actionBusy, false);
});

test('Device Info opens the install picker below the device action buttons', () => {
  const DeviceInfo = customElements.get('nspanel-dialog-device-info');
  const dlg = Object.create(DeviceInfo.prototype);
  Object.assign(dlg, {
    deviceStatus: { device_info: {}, update: { enabled: true } },
    deviceName: 'kitchen',
    entryId: 'entry1',
    _picker: { kind: 'select', device: 'kitchen' },
    _actionBusy: false,
  });

  const texts = dlg.render().values.map((value) => collectTemplateStrings(value).join(' '));
  const deviceIndex = texts.findIndex((text) => text.includes('di-device-actions'));
  const pickerIndex = texts.findIndex((text) => text.includes('device-update-picker'));
  assert.ok(deviceIndex >= 0);
  assert.ok(pickerIndex > deviceIndex);
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
