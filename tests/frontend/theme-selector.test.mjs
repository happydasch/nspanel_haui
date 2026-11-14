import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/views/device-settings.js';
import { themeSelector } from '../../custom_components/nspanel_haui/frontend/ui/theme-selector.js';
import { accessibleName, byLabel, byRole, byText } from './support/queries.mjs';
import { mount, render } from './support/render.mjs';

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
    onExport: () => {},
    onImport: () => {},
    ...fields,
  });
}

test('selecting a built-in or custom theme reports its id', () => {
  const selected = [];
  const root = render(selector({
    custom: { evening: theme('Evening', 3) },
    onSelect: (id) => selected.push(id),
  }));
  const group = byRole(root, 'radiogroup', { name: 'Theme' });
  const radios = [...group.querySelectorAll('input[type=radio]')];

  assert.deepEqual(radios.map((radio) => accessibleName(radio)), ['dark', 'light', 'Evening']);
  assert.deepEqual(radios.filter((radio) => radio.checked).map((radio) => radio.value), ['dark']);

  byRole(group, 'radio', { name: 'Evening' }).dispatchEvent(new Event('change', { bubbles: true }));
  assert.deepEqual(selected, ['evening']);
});

test('the selector only offers the custom theme group when custom themes exist', () => {
  const root = render(selector());

  assert.ok(byText(root, 'Predefined themes'));
  assert.equal(byText(root, 'Custom themes'), null);
  assert.equal(root.querySelectorAll('input[type=radio]').length, 2);
});

test('theme library controls and selected-theme actions call their callbacks', () => {
  const called = [];
  const root = render(selector({
    custom: { evening: theme('Evening', 3) },
    selectedId: 'evening',
    actions: [{ label: 'Delete', iconName: 'delete', onClick: () => called.push('delete') }],
    onNew: () => called.push('new'),
    onExport: () => called.push('export'),
    onImport: () => called.push('import'),
  }));
  const action = (name) => [...root.querySelectorAll('ha-button, button')]
    .find((button) => accessibleName(button) === name);

  assert.ok(action('New'));
  assert.ok(action('Export'));
  assert.ok(action('Import'));
  assert.ok(action('Delete'));
  action('New').click();
  action('Export').click();
  action('Delete').click();
  root.querySelector('input[type="file"]').dispatchEvent(new Event('change', { bubbles: true }));

  assert.deepEqual(called, ['new', 'export', 'delete', 'import']);
});

test('name editing reports input and save actions and exposes status and error roles', () => {
  const called = [];
  const root = render(selector({
    nameAction: 'new',
    themeName: 'Evening',
    notice: 'Saved',
    error: 'Duplicate',
    onNameInput: (value) => called.push(['input', value]),
    onSaveName: () => called.push(['save']),
    onCancelName: () => called.push(['cancel']),
  }));
  const name = byRole(root, 'textbox', { name: 'Color theme name' });

  assert.ok(name);
  assert.equal(name.value, 'Evening');
  assert.equal(byRole(root, 'status')?.textContent.trim(), 'Saved');
  assert.equal(byRole(root, 'alert')?.textContent.trim(), 'Duplicate');

  name.value = 'Evening 2';
  name.dispatchEvent(new Event('input', { bubbles: true }));
  const action = (name) => [...root.querySelectorAll('ha-button')]
    .find((button) => button.textContent.trim() === name);
  action('Save').click();
  action('Cancel').click();
  assert.deepEqual(called, [['input', 'Evening 2'], ['save'], ['cancel']]);
});

test('device settings is mounted without a theme selector', async () => {
  const settings = await mount('nspanel-device-settings', {
    config: { locale: 'en', snapshot_max_age_seconds: -1 },
  });

  assert.ok(settings.shadowRoot.querySelector('form'));
  assert.equal(byLabel(settings.shadowRoot, 'Theme'), null);
});
