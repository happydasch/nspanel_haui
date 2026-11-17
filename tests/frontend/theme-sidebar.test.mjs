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
  'nspanel-backup-sidebar',
  'nspanel-updates-sidebar',
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

test('every editor dialog shares the dialog base class', () => {
  for (const tag of DIALOGS) {
    assert.ok(customElements.get(tag).prototype instanceof HauiDialog, tag);
  }
});

test('theme sidebar loads themes, switches palette, and edits custom definitions', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
  const palettes = (dark, light) => ({
    dark: { weather: { default: dark }, alarm: { armed: dark + 1 }, climate: { off: dark + 2 } },
    light: { weather: { default: light }, alarm: { armed: light + 1 }, climate: { off: light + 2 } },
  });
  const builtins = {
    dark: { name: 'Dark', colors: { background: 2 }, icons: palettes(3, 30) },
    light: { name: 'Light', colors: { background: 65535 }, icons: palettes(7, 70) },
    black: { name: 'Black', colors: { background: 10 }, icons: palettes(11, 110) },
  };
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass),
    open: true,
    entryId: 'entry',
    themeId: 'dark',
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
  // The theme's own page background picks the icon palette its edits land in.
  dlg._applyTheme('light');
  assert.equal(dlg.themeId, 'light');
  dlg._onColorChange('icons.weather.default', { target: { value: '#ff0000' } });
  assert.equal(dlg._icons.light.weather.default, hexToRgb565('#ff0000'));
  assert.equal(dlg._icons.dark.weather.default, 7);
});
test('the Theme sidebar shows a loading note, then the preview, palettes and actions without a dialog', async () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
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
    _loading: true,
    _themes: {},
    _builtins: {},
    _customThemes: {},
    requestUpdate() {},
    _changedCount: () => 1,
    _renderPreview: () => '',
    _isBuiltin: () => true,
    _themeData: () => dark,
    _renderGroup: () => '',
  });

  const loadingTemplate = dlg.render();
  await dlg._loadThemes();
  const loadedTemplate = dlg.render();

  const loaded = loadedTemplate.strings.join('');
  assert.match(loaded, /class="haui-theme-sidebar"/);
  assert.match(loaded, /class="haui-footer-wrapper"/);
  // The theme selector (library dropdown plus its one action row) is a template value.
  const selector = findTemplateResult(loadedTemplate, (template) =>
    template.strings.join('').includes('class="haui-theme-selector"'));
  assert.ok(selector);
  assert.doesNotMatch(loaded, /haui-theme-tweak/);
  assert.doesNotMatch(loaded, /cp-color-target|This device|These colors override/);
  const actionRow = findTemplateResult(loadedTemplate, (template) =>
    template.strings.join('').includes('class="haui-theme-selector-actions"'));
  assert.ok(actionRow);
  assert.match(actionRow.strings.join(''), /type="file"/);

  // The sidebar frame carries the title and close control: no dialog of its own.
  assert.doesNotMatch(loaded, /<ha-dialog[\s>]/);
  const templateValues = [];
  const collectValues = (value) => {
    if (Array.isArray(value)) value.forEach(collectValues);
    else if (value && Array.isArray(value.values)) {
      templateValues.push(...value.values.filter((item) => typeof item === 'string'));
      collectValues(value.values);
    }
  };
  collectValues(loadedTemplate);
  assert.ok(templateValues.includes('Reset theme'));
  assert.ok(!templateValues.includes('Reset colors'));
  const changedIndicator = findTemplateResult(loadedTemplate, (template) =>
    template.strings.join('').includes('haui-footer-changed'));
  assert.deepEqual(changedIndicator.values, ['1 changed']);
  // Both intro notes use the shared intro style, like the other sidebars' notes.
  assert.doesNotMatch(loaded, /haui-theme-section-description|haui-theme-color-scope-note/);
});


test('theme color edits update the selected shared palette', () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
  const icons = { dark: { weather: { sunny: 1 } }, light: { weather: { sunny: 2 } } };
  Object.assign(dlg, {
    themeId: 'custom',
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
    _saveDeviceConfig: async (config) => {
      savedConfig = config;
      return true;
    },
    store: { actions: { closeOverlay: (kind) => closed.push(kind) } },
    requestUpdate() {},
  };

  await saveTheme(host, { themeId: 'custom-theme' });

  assert.equal(savedConfig.theme_id, 'custom-theme');
  assert.equal('theme_overrides' in savedConfig, false);
  // A saved theme closes the Theme sidebar; Device settings below it stays open.
  assert.deepEqual(closed, ['theme']);
});

test('opening the theme sidebar selects the saved theme', () => {
  const host = {
    _selectedDevice: 'panel',
    _panels: { devices: { panel: { config: { theme_id: 'evening' } } } },
    _loadDeviceConfig() {},
    store: { actions: { pushOverlay: (overlay) => { host.overlay = overlay; } } },
    requestUpdate() {},
  };

  openThemeSidebar(host);

  assert.equal(host._themeId, 'evening');
  assert.deepEqual([host.overlay.kind, host.overlay.subject], ['theme', 'panel']);
});
