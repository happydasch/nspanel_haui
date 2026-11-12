import './dom-shim.mjs';

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
  const dlg = Object.create(customElements.get(tag).prototype);
  const events = [];
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass), requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

test('every editor dialog shares the dialog base class', () => {
  for (const tag of DIALOGS) {
    assert.ok(customElements.get(tag).prototype instanceof HauiDialog, tag);
  }
});

test('color themes read complete palettes from the backend theme catalog', () => {
  const dark = { background: 10, text: 20 };
  const light = { background: hexToRgb565('#ffffff'), text: hexToRgb565('#101010') };
  const themes = { dark: { colors: dark }, light: { colors: light } };

  assert.deepEqual(getTheme('dark', themes), dark);
  assert.deepEqual(getTheme('light', themes), light);
  assert.throws(() => getTheme('unknown', themes), /Unknown color theme/);
});

test('theme sidebar loads themes, switches palette, and edits custom definitions', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = Object.create(ThemeSidebar.prototype);
  const builtins = {
    dark: { name: 'Dark', colors: { background: 2 }, icons: { weather: { default: 3 }, alarm: { armed: 4 }, climate: { off: 5 } } },
    light: { name: 'Light', colors: { background: 6 }, icons: { weather: { default: 7 }, alarm: { armed: 8 }, climate: { off: 9 } } },
    black: { name: 'Black', colors: { background: 10 }, icons: { weather: { default: 11 }, alarm: { armed: 12 }, climate: { off: 13 } } },
  };
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    open: true,
    entryId: 'entry',
    themeId: 'dark',
    themeVariant: 'dark',
    hass: { fetchWithAuth: async (url) => url.endsWith('color_defaults')
      ? { ok: true, json: async () => ({ background: 2 }) }
      : { ok: true, json: async () => ({ builtins, themes: {} }) } },
    _colors: {},
    _loading: false,
    requestUpdate() {},
  });

  dlg.willUpdate(new Map([['open', false]]));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(dlg.themeId, 'dark');
  dlg._applyTheme('black');
  assert.equal(dlg.themeId, 'black');
  assert.equal(dlg._colors.background, 10);
});
test('the Theme sidebar shows a loading note, then the preview, palettes and actions without a dialog', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = Object.create(ThemeSidebar.prototype);
  const dark = { name: 'Dark', colors: {}, icons: { dark: {}, light: {} } };
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    hass: {
      fetchWithAuth: async (url) => url.endsWith('color_defaults')
        ? { json: async () => ({}) }
        : { ok: true, json: async () => ({ builtins: { dark }, themes: {} }) },
    },
    open: true,
    entryId: 'entry',
    themeId: 'dark',
    themeVariant: 'dark',
    _loading: true,
    _themes: {},
    _builtins: {},
    _customThemes: {},
    requestUpdate() {},
    _changedCount: () => 0,
    _renderPreview: () => '',
    _isBuiltin: () => true,
    _panelColorOverrideCount: () => 1,
    _themeData: () => dark,
    _renderGroup: () => '',
  });

  const loadingTemplate = dlg.render();
  await dlg._loadThemes();
  const loadedTemplate = dlg.render();

  assert.match(loadingTemplate.strings.join(''), /haui-theme-loading/);
  const loaded = loadedTemplate.strings.join('');
  assert.match(loaded, /class="haui-theme-sidebar"/);
  assert.match(loaded, /class="footer-wrapper"/);
  assert.match(loaded, /haui-theme-color-controls/);
  assert.doesNotMatch(loaded, /haui-theme-tweak/);
  assert.doesNotMatch(loaded, /cp-color-target|This device|These colors override/);
  const actionMarkup = findTemplateResult(loadedTemplate, (template) =>
    template.strings.join('').includes('class="cp-theme-actions"'));
  assert.ok(actionMarkup);
  const actions = actionMarkup.strings.join('');
  assert.equal((actions.match(/variant="neutral"\s+appearance="plain"/g) || []).length, 3);
  assert.match(actions, /type="file"/);
  assert.doesNotMatch(actions, /class="cp-import-label"/);

  // The sidebar frame carries the title and close control: no dialog of its own.
  assert.doesNotMatch(loaded, /<ha-dialog[\s>]/);
  const resetToggle = findTemplateResult(loadedTemplate, (template) => template.values[0] === 'cp-reset-overrides');
  assert.ok(resetToggle);
  assert.equal(resetToggle.values[1], 'native-toggle');
  resetToggle.values[3]({ target: { checked: true } });
  assert.equal(dlg._resetPanelColors, true);
  assert.ok(findTemplateResult(loadedTemplate, (template) => template.values[0] === 'cp-icon-theme'));
  assert.ok(findTemplateResult(loadedTemplate, (template) => template.values[0] === 'cp-icon-variant'));
});


test('theme color edits update the selected shared palette', () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = Object.create(ThemeSidebar.prototype);
  const icons = { dark: { weather: { sunny: 1 } }, light: { weather: { sunny: 2 } } };
  Object.assign(dlg, {
    themeId: 'custom',
    iconVariant: 'dark',
    _colors: { background: 0x1234 },
    _icons: structuredClone(icons),
    _themeData: () => ({ colors: { background: 0x1234 }, icons }),
    _isBuiltin: () => false,
    requestUpdate() {},
  });

  dlg._onColorChange('background', { target: { value: '#ff0000' } });

  assert.equal(dlg._colors.background, hexToRgb565('#ff0000'));
  assert.equal(dlg._edited, true);
});

function findTemplateResult(value, predicate) {
  if (Array.isArray(value)) {
    for (const item of value) {
      const match = findTemplateResult(item, predicate);
      if (match) return match;
    }
  } else if (value && Array.isArray(value.strings) && Array.isArray(value.values)) {
    if (predicate(value)) return value;
    return findTemplateResult(value.values, predicate);
  }
  return null;
}

test('saving a theme persists its active ID without device color overrides', async () => {
  let savedConfig;
  const closed = [];
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: {},
    _devicePanels: () => [],
    _savePanels: async (_panels, _message, config) => {
      savedConfig = config;
      return true;
    },
    store: { actions: { closeOverlay: (kind) => closed.push(kind) } },
    requestUpdate() {},
  };

  await saveTheme(host, { themeId: 'custom-theme', themeVariant: 'dark' });

  assert.equal(savedConfig.theme_id, 'custom-theme');
  assert.equal('theme_overrides' in savedConfig, false);
  // A saved theme closes the Theme sidebar; Device settings below it stays open.
  assert.deepEqual(closed, ['theme']);
});

test('opening the theme sidebar selects the saved theme and icon variant', () => {
  const host = {
    _selectedDevice: 'panel',
    _panels: { devices: { panel: { config: { theme_id: 'evening', theme_variant: 'light' } } } },
    _loadDeviceConfig() {},
    store: { actions: { pushOverlay: (overlay) => { host.overlay = overlay; } } },
    requestUpdate() {},
  };

  openThemeSidebar(host);

  assert.equal(host._themeId, 'evening');
  assert.equal(host._themeVariant, 'light');
  assert.deepEqual([host.overlay.kind, host.overlay.subject], ['theme', 'panel']);
});
test('the theme selector lists predefined and custom themes in one dropdown', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = Object.create(ThemeSidebar.prototype);
  const icons = {
    dark: { weather: { sunny: 20 }, alarm: { armed: 21 }, climate: { off: 22 } },
    light: { weather: { sunny: 30 }, alarm: { armed: 31 }, climate: { off: 32 } },
  };
  const builtins = {
    dark: { name: 'Dark', colors: { background: 2 }, icons },
    light: { name: 'Light', colors: { background: 6 }, icons },
  };
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    open: true,
    entryId: 'entry',
    themeId: 'evening',
    panels: [],
    themeVariant: 'dark',
    hass: {
      fetchWithAuth: async (url) => url.endsWith('color_defaults')
        ? { ok: true, json: async () => ({ background: 2 }) }
        : { ok: true, json: async () => ({ builtins, themes: { evening: { name: 'Evening', colors: { background: 10 }, icons } } }) },
    },
    _colors: {},
    _loading: true,
    requestUpdate() {},
    _changedCount: () => 0,
    _panelColorOverrideCount: () => 0,
    _renderGroup: () => '',
  });

  await dlg._loadThemes();

  const select = themeSelect(dlg.render());
  assert.ok(select, 'the sidebar renders one theme dropdown');
  assert.equal(select.value, 'evening');
  assert.deepEqual(select.options, [
    { group: 'Predefined themes', value: 'dark', selected: false },
    { group: 'Predefined themes', value: 'light', selected: false },
    { group: 'Custom themes', value: 'evening', selected: true },
  ]);
});

/** The theme dropdown of a Lit result tree: its value and its grouped options. */
function themeSelect(value) {
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = themeSelect(item);
      if (found) return found;
    }
    return null;
  }
  if (!value || typeof value !== 'object' || !Array.isArray(value.values)) return null;
  if (!value.strings.join('').includes('id="haui-theme-select"')) return themeSelect(value.values);

  const valueIndex = value.strings.findIndex((part) => part.trimEnd().endsWith('.value='));
  const options = [];
  const walk = (node, group) => {
    if (Array.isArray(node)) { node.forEach((item) => walk(item, group)); return; }
    if (!node || typeof node !== 'object' || !Array.isArray(node.values)) return;
    let current = group;
    node.strings.forEach((part, index) => {
      if (part.includes('<optgroup label=')) current = node.values[index];
      if (part.includes('<option')) {
        options.push({ group: current, value: node.values[index], selected: node.values[index + 1] === true });
      }
    });
    node.values.forEach((item) => walk(item, current));
  };
  walk(value, '');
  return { value: value.values[valueIndex], options };
}

test('changing a color of a built-in theme switches to a custom copy and saves it', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = Object.create(ThemeSidebar.prototype);
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
    _resetPanelColors: false,
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
  const dlg = Object.create(ThemeSidebar.prototype);
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
  const dlg = Object.create(ThemeSidebar.prototype);
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
    _resetPanelColors: false,
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
  let clicked = false;
  URL.createObjectURL = (blob) => { exportedBlob = blob; return 'blob:themes'; };
  URL.revokeObjectURL = () => {};
  document.createElement = () => ({ click() { clicked = true; } });
  try {
    dlg._exportThemes();
    assert.equal(clicked, true);
    assert.deepEqual(JSON.parse(await exportedBlob.text()).themes, dlg._customThemes);
  } finally {
    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
    document.createElement = originalCreateElement;
  }

  await dlg._deleteTheme();
  assert.equal(Object.hasOwn(dlg._customThemes, 'evening'), false);
  assert.equal(dlg.themeId, 'dark');
});
test('applying a theme clears legacy page-specific color overrides', async () => {
  let savedPanels;
  let savedConfig;
  const host = {
    _selectedDevice: 'panel',
    _deviceConfig: {},
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
    store: { actions: { closeOverlay() {} } },
    requestUpdate() {},
  };

  await saveTheme(host, { themeId: 'dark', resetPanelColors: true, themeVariant: 'dark' });

  assert.equal('theme_overrides' in savedConfig, false);
  assert.equal('text_color' in savedPanels[0].items[0], false);
  assert.equal('back_color' in savedPanels[0].items[0], false);
  assert.equal(savedPanels[0].items[0].color, 789);
  assert.equal('keypad_bg_color' in savedPanels[0], false);
  assert.equal('off_color' in savedPanels[0], false);
});
test('closing a dialog emits dialog-closed', () => {
  const { dlg, events } = dialog('nspanel-dialog-confirm');
  dlg._dispatchClose();
  assert.deepEqual(events.map((e) => e.type), ['dialog-closed']);
});

// Two days apart, so they fall on different calendar days in every time zone.
const LOG_LINES = [
  '[2026-11-09T12:00:00+00:00] INFO Device is starting',
  '[2026-11-11T12:00:00+00:00] WARN Slow render on grid',
  '[2026-11-11T12:00:05+00:00] ERROR Template failed\nTraceback (most recent call last)',
];

test('the logs sidebar parses the hub lines newest first and filters them by level and text', () => {
  const entries = logEntries([...LOG_LINES, { line: '[2026-11-11T12:00:06+00:00] DEBUG Heartbeat', deviceName: 'Hall' }]);
  assert.deepEqual(entries.map((entry) => entry.level), ['debug', 'error', 'warning', 'info']);
  assert.equal(entries[1].message, 'Template failed\nTraceback (most recent call last)');
  assert.ok(entries.every((entry) => entry.time instanceof Date));

  assert.deepEqual(filterLogEntries(entries, 'warning', '').map((entry) => entry.message), ['Slow render on grid']);
  assert.deepEqual(filterLogEntries(entries, 'all', ' TEMPLATE ').map((entry) => entry.level), ['error']);
  // The search also finds a device by its name.
  assert.deepEqual(filterLogEntries(entries, 'all', 'hall').map((entry) => entry.level), ['debug']);
  assert.deepEqual(filterLogEntries(entries, 'error', 'slow'), []);
});

test('logs copy oldest first with the full timestamp and the device in front of the message', () => {
  const entries = logEntries([
    { line: LOG_LINES[0], deviceName: 'Kitchen' },
    { line: LOG_LINES[1], deviceName: 'Hall' },
  ]);
  assert.equal(logText(entries), [
    '[2026-11-09T12:00:00+00:00] INFO Kitchen: Device is starting',
    '[2026-11-11T12:00:00+00:00] WARNING Hall: Slow render on grid',
  ].join('\n'));
});

test('the logs sidebar groups by day, tags problems, and hands Copy the visible entries', () => {
  const { dlg, events } = dialog('nspanel-logs-sidebar', { open: true, logs: LOG_LINES, _level: 'all', _query: '' });
  const markup = collectTemplateStrings(dlg.render()).join(' ');
  assert.equal(markup.split('<h3>').length - 1, 2);
  assert.match(markup, /haui-log-error/);
  assert.match(markup, /Slow render on grid/);
  assert.match(markup, /Search logs/);

  dlg._level = 'error';
  assert.doesNotMatch(collectTemplateStrings(dlg.render()).join(' '), /Slow render on grid/);
  dlg._copy(filterLogEntries(logEntries(LOG_LINES), 'error', ''));
  assert.deepEqual(events.map((event) => event.type), ['copy-logs']);
  assert.match(events[0].detail.text, /^\[2026-11-11T12:00:05\+00:00\] ERROR Template failed/);
});

test('the logs sidebar tells an empty log from a search that matches nothing', () => {
  const empty = dialog('nspanel-logs-sidebar', { open: true, logs: [], _level: 'all', _query: '' }).dlg;
  assert.match(collectTemplateStrings(empty.render()).join(' '), /No log entries yet\./);
  const unmatched = dialog('nspanel-logs-sidebar', { open: true, logs: LOG_LINES, _level: 'all', _query: 'zigbee' }).dlg;
  assert.match(collectTemplateStrings(unmatched.render()).join(' '), /No log entries match\./);
});

test('the firmware popover leads with its status, then versions, then settings', () => {
  const { dlg } = dialog('nspanel-firmware-popover', {
    open: true,
    deviceName: 'kitchen',
    deviceStatus: {
      connected: true,
      haui_version: '0.4.2',
      device_info: { name: 'Kitchen', tft_version: '1.2.3' },
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
  assert.doesNotMatch(markup, /Redraw display|Listeners/);
});

test('Redraw display calls the hub for the selected device', async () => {
  const calls = [];
  const host = Object.create(NSPanelEditor.prototype);
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
  const pickerIndex = markup.indexOf('device-update-picker');
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
      haui_version: '0.4.2',
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
  assert.deepEqual(actions.map(({ ariaLabel }) => ariaLabel), ['Install Firmware', 'Install Display']);
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
