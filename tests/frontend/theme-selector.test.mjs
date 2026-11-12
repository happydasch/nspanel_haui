import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { themeSelector } from '../../custom_components/nspanel_haui/frontend/ui/theme-selector.js';

/** The markup of a Lit template, nested templates included. */
const source = (template) => `${template.strings.join(' ')} ${template.values.map((value) => {
  if (Array.isArray(value)) return value.map((nested) => nested?.strings ? source(nested) : String(nested ?? '')).join(' ');
  return value?.strings ? source(value) : String(value ?? '');
}).join(' ')}`;

/** A theme with the four swatch colors the selector draws. */
function theme(name, background) {
  return {
    name,
    colors: { background, header_background: 0, component_active: 0, entity_on: 0 },
    icons: { dark: {}, light: {} },
  };
}

function selector(fields = {}) {
  return themeSelector({
    builtins: { dark: theme('Dark', 1), light: theme('Light', 2) },
    custom: {},
    selectedId: 'dark',
    builtinLabel: (id) => id,
    onSelect: () => {},
    onNew: () => {},
    onExportAll: () => {},
    onImport: () => {},
    ...fields,
  });
}

/** A device settings view without Lit's constructor (which needs a real DOM). */
function deviceSettings(fields = {}) {
  const form = { theme_id: 'dark', ...fields };
  return Object.assign(Object.create(customElements.get('nspanel-device-settings').prototype), {
    requestUpdate() {},
    config: form,
    _deviceConfigForm: form,
    entryId: 'entry',
    _builtinThemes: { dark: theme('Dark', 1), light: theme('Light', 2) },
    _customThemes: {},
    _themesLoading: false,
    _themeError: '',
    _themeNotice: '',
    _nameAction: '',
    _themeName: '',
    ...fields,
  });
}

/** Every value of a Lit template, nested templates included. */
function values(template) {
  const found = [];
  const walk = (value) => {
    if (Array.isArray(value)) { value.forEach(walk); return; }
    if (value?.strings) { value.values.forEach(walk); return; }
    found.push(value);
  };
  walk(template);
  return found;
}

test('the theme selector offers predefined and custom themes in one dropdown', () => {
  const template = selector({ custom: { evening: theme('Evening', 3) } });
  const markup = source(template);
  assert.match(markup, /id="haui-theme-select"/);
  assert.equal((markup.match(/<optgroup label=/g) || []).length, 2);
  assert.ok(values(template).includes('Predefined themes'));
  assert.ok(values(template).includes('Custom themes'));
  assert.ok(values(template).includes('Evening'));
  assert.doesNotMatch(markup, /haui-theme-card/);
});

test('the theme selector leaves out the custom group while the library has none', () => {
  const markup = source(selector());
  assert.match(markup, /Predefined themes/);
  assert.doesNotMatch(markup, /Custom themes/);
});

test('the theme selector carries the library controls and the selected theme actions', () => {
  const markup = source(selector({
    custom: { evening: theme('Evening', 3) },
    selectedId: 'evening',
    actions: [{ label: 'Delete', onClick: () => {} }],
  }));
  assert.match(markup, /cp-theme-actions/);
  assert.match(markup, /type="file"/);
  assert.match(markup, /New theme/);
  assert.match(markup, /Export all/);
  assert.match(markup, /Import/);
  assert.match(markup, /haui-theme-selector-actions/);
  assert.match(markup, /Delete/);
});

test('the theme selector shows the name input, notice and error it is given', () => {
  const markup = source(selector({
    nameAction: 'new',
    themeName: 'Evening',
    notice: 'Created the custom theme.',
    error: 'A color theme with this name already exists.',
  }));
  assert.match(markup, /cp-theme-name/);
  assert.match(markup, /Color theme name/);
  assert.match(markup, /role="status"/);
  assert.match(markup, /role="alert"/);
});

test('device settings select a theme into the device config draft', () => {
  const dlg = deviceSettings();
  dlg._selectTheme('light');
  assert.equal(dlg._deviceConfigForm.theme_id, 'light');
});

test('device settings create a custom theme from the selected one', async () => {
  const dlg = deviceSettings();
  let persisted;
  dlg._persistThemes = async (themes) => { persisted = themes; return true; };

  dlg._startNewTheme();
  assert.equal(dlg._nameAction, 'new');
  dlg._themeName = 'Evening';
  await dlg._saveNamedTheme();

  assert.equal(persisted.evening.name, 'Evening');
  assert.equal(persisted.evening.colors.background, 1);
  assert.equal(dlg._deviceConfigForm.theme_id, 'evening');
  assert.match(dlg._themeNotice, /Evening/);
});

test('device settings refuse a custom theme name that is taken', async () => {
  const dlg = deviceSettings();
  let persisted = false;
  dlg._persistThemes = async () => { persisted = true; return true; };

  dlg._startNewTheme();
  dlg._themeName = 'Dark';
  await dlg._saveNamedTheme();

  assert.equal(persisted, false);
  assert.match(dlg._themeError, /already exists/);
});

test('device settings import theme files and reject colliding names', async () => {
  const dlg = deviceSettings();
  let persisted;
  dlg._persistThemes = async (themes) => { persisted = themes; return true; };
  const file = (themes) => ({ target: { files: [{ text: async () => JSON.stringify({ version: 1, themes }) }], value: 'file' } });

  await dlg._importThemes(file({ evening: theme('Evening', 3) }));
  assert.equal(persisted.evening.name, 'Evening');

  await dlg._importThemes(file({ dark: theme('Dark', 4) }));
  assert.match(dlg._themeError, /already exists/);

  await dlg._importThemes({ target: { files: [{ text: async () => '{"version":2}' }], value: 'file' } });
  assert.match(dlg._themeError, /Invalid color theme file/);
});

test('device settings render the theme selector in their Theme section', () => {
  const dlg = deviceSettings();
  const markup = source(dlg.render());
  assert.match(markup, /Theme/);
  assert.match(markup, /id="haui-theme-select"/);
  assert.match(markup, /Predefined themes/);
});
