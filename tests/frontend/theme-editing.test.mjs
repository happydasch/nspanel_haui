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

test('changing a color of a built-in theme switches to a custom copy and saves it', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
  const icons = {
    dark: { weather: { sunny: 20 }, alarm: { armed: 21 }, climate: { off: 22 } },
    light: { weather: { sunny: 30 }, alarm: { armed: 31 }, climate: { off: 32 } },
  };
  const dark = { name: 'Dark', colors: { background: 10, text: 20 }, icons };
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    themeVariant: 'dark',
    themeId: 'dark',
    _themes: { dark },
    _builtins: { dark },
    _customThemes: {},
    _colors: { background: 10, text: 20 },
    _icons: JSON.parse(JSON.stringify(icons)),
    _edited: false,
    _themeError: '',
    _themeNotice: '',
    _autoThemeId: '',
    _keepThemeColors: false,
    requestUpdate() {},
  });

  dlg._onColorChange('background', { target: { value: '#ff0000' } });

  assert.equal(dlg.themeId, 'dark-custom');
  assert.equal(dlg._isBuiltin(), false);
  assert.equal(dlg._themes['dark-custom'].name, 'Dark (custom)');
  assert.equal(dlg._colors.background, hexToRgb565('#ff0000'));
  assert.match(dlg._themeNotice, /Dark \(custom\)/);
  assert.equal(dlg._edited, true);

  dlg.willUpdate(new Map([['themeId', 'dark']]));
  assert.equal(dlg._colors.background, hexToRgb565('#ff0000'));
  assert.equal(dlg._edited, true);

  let persisted;
  dlg._persistThemes = async (themes) => { persisted = themes; return true; };
  let emitted;
  dlg._emit = (type, detail) => { emitted = { type, detail }; };
  await dlg._dispatchSave();
  assert.equal(persisted['dark-custom'].name, 'Dark (custom)');
  assert.equal(persisted['dark-custom'].colors.background, hexToRgb565('#ff0000'));
  assert.equal(emitted.detail.themeId, 'dark-custom');

  dlg._applyTheme('dark');
  assert.equal(dlg._themes['dark-custom'], undefined);
  assert.equal(dlg._themeNotice, '');
});



test('theme JSON import rejects collisions and persists valid collections', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
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
  const eveningTheme = {
    name: 'Evening',
    colors,
    icons: { dark: iconPalette, light: JSON.parse(JSON.stringify(iconPalette)) },
  };
  const darkTheme = { ...eveningTheme, name: 'Dark' };

  const custom = { evening: eveningTheme };
  let posted;
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    entryId: 'entry',
    themeId: 'dark',
    _themes: { dark: darkTheme },
    _builtins: { dark: darkTheme },
    _colors: { ...colors },
    _icons: { dark: iconPalette, light: JSON.parse(JSON.stringify(iconPalette)) },
    _customThemes: {},
    _themeError: '',
    hass: {
      fetchWithAuth: async (_url, options) => {
        posted = JSON.parse(options.body).themes;
        return { ok: true, json: async () => ({ themes: posted }) };
      },
    },
    requestUpdate() {},
  });

  await dlg._importThemes({ target: { files: [{ text: async () => JSON.stringify({ version: 1, themes: custom }) }], value: 'file' } });
  assert.equal(posted.evening.name, 'Evening');
  assert.equal(dlg._customThemes.evening.name, 'Evening');

  await dlg._importThemes({ target: { files: [{ text: async () => JSON.stringify({ version: 1, themes: custom }) }], value: 'file' } });
  assert.match(dlg._themeError, /already exists/);
  assert.equal(posted.evening.name, 'Evening');
});




test('custom color themes can be saved, renamed, exported, and deleted', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
  let current;
  const darkTheme = {
    name: 'Dark',
    colors: { background: 10 },
    icons: { dark: { weather: { sunny: 20 } }, light: { weather: { sunny: 30 } } },
  };
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    entryId: 'entry',
    themeId: 'dark',
    _themes: { dark: darkTheme },
    _builtins: { dark: darkTheme },
    _customThemes: {},
    _colors: { background: 10 },
    _icons: { dark: { weather: { sunny: 20 } }, light: { weather: { sunny: 30 } } },
    _nameAction: 'save-as',
    _themeName: 'Evening',
    _themeError: '',
    requestUpdate() {},
    hass: {
      fetchWithAuth: async (_url, options) => {
        current = JSON.parse(options.body).themes;
        return { ok: true, json: async () => ({ themes: current }) };
      },
    },
  });

  await dlg._saveNamedTheme();
  assert.equal(dlg.themeId, 'evening');
  assert.equal(dlg._customThemes.evening.name, 'Evening');

  dlg._startNameAction('rename');
  dlg._themeName = 'Evening v2';
  await dlg._saveNamedTheme();
  assert.equal(dlg._customThemes.evening.name, 'Evening v2');

  const originalCreate = URL.createObjectURL;
  const originalRevoke = URL.revokeObjectURL;
  const originalCreateElement = document.createElement;
  let exportedBlob;
  let downloadName;
  let clicked = false;
  URL.createObjectURL = (blob) => { exportedBlob = blob; return 'blob:themes'; };
  URL.revokeObjectURL = () => {};
  document.createElement = () => ({
    set download(name) { downloadName = name; },
    click() { clicked = true; },
  });
  try {
    dlg._colors = { background: 42 };
    dlg._icons = { dark: { weather: { sunny: 21 } }, light: { weather: { sunny: 30 } } };
    dlg._exportSelectedTheme();
    assert.equal(clicked, true);
    assert.equal(downloadName, 'nspanel-haui-evening.json');
    assert.deepEqual(JSON.parse(await exportedBlob.text()).themes, {
      evening: { name: 'Evening v2', colors: dlg._colors, icons: dlg._icons },
    });

    dlg.themeId = 'dark';
    dlg._colors = { background: 10 };
    dlg._icons = darkTheme.icons;
    dlg._exportSelectedTheme();
    assert.equal(downloadName, 'nspanel-haui-dark.json');
    assert.deepEqual(JSON.parse(await exportedBlob.text()).themes, {
      dark: { name: 'Dark', colors: dlg._colors, icons: dlg._icons },
    });
  } finally {
    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
    document.createElement = originalCreateElement;
  }

  dlg.themeId = 'evening';
  await dlg._deleteTheme();
  assert.equal(Object.hasOwn(dlg._customThemes, 'evening'), false);
  assert.equal(dlg.themeId, 'dark');
});
test('changed count tolerates a theme with a missing icon variant', () => {
  const dlg = document.createElement('nspanel-theme-sidebar');
  const theme = {
    name: 'Custom',
    colors: { background: 10 },
    icons: { dark: { weather: { sunny: 20 } } },
  };
  Object.assign(dlg, {
    themeId: 'custom',
    themeVariant: 'dark',
    _originalThemeId: 'custom',
    _originalThemeVariant: 'dark',
    _themes: { custom: theme },
    _colors: { background: 10 },
    _icons: {
      dark: { weather: { sunny: 20 } },
      light: { weather: { sunny: 30 } },
    },
  });

  assert.equal(dlg._changedCount(), 1);
});

test('reverting a changed color restores only that saved theme value', () => {
  const dlg = document.createElement('nspanel-theme-sidebar');
  const theme = {
    name: 'Custom',
    colors: { background: 10, text: 20 },
    icons: {
      dark: { weather: { sunny: 30 } },
      light: { weather: { sunny: 40 } },
    },
  };
  Object.assign(dlg, {
    themeId: 'custom',
    iconVariant: 'dark',
    _themes: { custom: theme },
    _colors: { background: 11, text: 21 },
    _icons: structuredClone(theme.icons),
    requestUpdate() {},
  });
  dlg._icons.dark.weather.sunny = 31;

  dlg._resetColor('background');

  assert.equal(dlg._colors.background, 10);
  assert.equal(dlg._colors.text, 21);
  assert.equal(dlg._icons.dark.weather.sunny, 31);
});

test('resetting the theme restores its saved colors and icons without changing panels', () => {
  const dlg = document.createElement('nspanel-theme-sidebar');
  const theme = {
    name: 'Custom',
    colors: { background: 10, text: 20 },
    icons: {
      dark: { weather: { sunny: 30 } },
      light: { weather: { sunny: 40 } },
    },
  };
  const panels = [{ items: [{ text_color: 100, back_color: 200 }] }];
  Object.assign(dlg, {
    themeId: 'custom',
    _themes: { custom: theme },
    _colors: { background: 11, text: 21 },
    _icons: {
      dark: { weather: { sunny: 31 } },
      light: { weather: { sunny: 41 } },
    },
    panels,
    requestUpdate() {},
  });

  dlg._resetTheme();

  assert.deepEqual(dlg._colors, theme.colors);
  assert.deepEqual(dlg._icons, theme.icons);
  assert.strictEqual(dlg.panels, panels);
  assert.deepEqual(panels, [{ items: [{ text_color: 100, back_color: 200 }] }]);
});

test('applying a theme saves settings separately and preserves panel color overrides', async () => {
  let savedPanels;
  let savedConfig;
  let message;
  const panels = [{
    type: 'grid',
    items: [{ text_color: 123, back_color: 456, color: 789 }],
    keypad_bg_color: 42,
    off_color: 11,
  }];
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: {},
    _devicePanels: () => panels,
    _saveDeviceConfig: async (config, nextMessage) => {
      savedConfig = config;
      message = nextMessage;
      return true;
    },
    _savePanels: async () => assert.fail('Theme apply without reset must not save panels'),
    store: { actions: { closeOverlay() {} } },
    requestUpdate() {},
  };

  await saveTheme(host, { themeId: 'dark', themeVariant: 'dark' });

  assert.equal(savedPanels, undefined);
  assert.deepEqual(panels, [{
    type: 'grid',
    items: [{ text_color: 123, back_color: 456, color: 789 }],
    keypad_bg_color: 42,
    off_color: 11,
  }]);
  assert.equal(message, 'Theme applied');
  assert.equal(savedConfig.theme_id, 'dark');
});
test('theme color reset saves settings first, then saves that device’s panels', async () => {
  const calls = [];
  const panels = [{ type: 'grid', key: 'one' }];
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: {},
    _devicePanels: () => panels,
    _saveDeviceConfig: async (config, message) => {
      calls.push(['settings', config.theme_id, message]);
      return true;
    },
    _savePanels: async (saved, message) => {
      calls.push(['panels', saved, message]);
      return true;
    },
    store: { actions: { closeOverlay() {} } },
    requestUpdate() {},
  };

  await saveTheme(host, { themeId: 'dark', themeVariant: 'dark', resetPanelColors: true });

  assert.deepEqual(calls, [
    ['settings', 'dark', 'Theme applied'],
    ['panels', panels, ''],
  ]);
});
