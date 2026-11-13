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
  const dlg = document.createElement('nspanel-theme-sidebar');
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
  const actionRow = findTemplateResult(loadedTemplate, (template) =>
    template.strings.join('').includes('class="haui-theme-selector-actions"'));
  assert.ok(actionRow);
  assert.match(actionRow.strings.join(''), /type="file"/);

  // The sidebar frame carries the title and close control: no dialog of its own.
  assert.doesNotMatch(loaded, /<ha-dialog[\s>]/);
  const resetToggle = findTemplateResult(loadedTemplate, (template) => template.values[0] === 'cp-reset-overrides');
  assert.ok(resetToggle);
  assert.equal(resetToggle.values[1], 'native-toggle');
  resetToggle.values[3]({ target: { checked: true } });
  assert.equal(dlg._resetPanelColors, true);
  assert.ok(findTemplateResult(loadedTemplate, (template) => template.values[0] === 'cp-icon-theme'));
  assert.ok(findTemplateResult(loadedTemplate, (template) => template.values[0] === 'cp-icon-variant'));
  // Both intro notes use the shared intro style, like the other sidebars' notes.
  assert.doesNotMatch(loaded, /haui-theme-section-description|haui-theme-color-scope-note/);
  assert.equal((loaded.match(/class="config-section-intro"/g) || []).length, 2);
});


test('theme color edits update the selected shared palette', () => {
  const ThemeSidebar = customElements.get('nspanel-theme-sidebar');
  const dlg = document.createElement('nspanel-theme-sidebar');
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
