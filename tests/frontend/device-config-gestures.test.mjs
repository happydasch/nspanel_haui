import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import {
  gestureActionLabel, gestureEditor, gestureSwipesLabel,
} from '../../custom_components/nspanel_haui/frontend/ui/gesture-editor.js';
import { SETTINGS_SECTIONS } from '../../custom_components/nspanel_haui/frontend/device-settings-sections.js';
import { DEVICE_CONFIG_DEFAULTS, GESTURE_NAMES } from '../../custom_components/nspanel_haui/frontend/constants.js';
import { render } from './support/render.mjs';
import { byRole } from './support/queries.mjs';

/** A dialog instance without Lit's constructor (which needs a real DOM). */
function dialog(props = {}) {
  const dlg = document.createElement('nspanel-device-settings');
  const events = [];
  Object.assign(dlg, { requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

/** Flatten a Lit TemplateResult tree to text. */
function flat(value) {
  if (Array.isArray(value)) return value.map(flat).join('');
  if (value && value.strings) return value.strings.reduce((text, part, index) =>
    text + part + (index < value.values.length ? flat(value.values[index]) : ''), '');
  return value == null ? '' : String(value);
}

function templates(value) {
  if (Array.isArray(value)) return value.flatMap(templates);
  if (value && value.strings) return [value, ...value.values.flatMap(templates)];
  return [];
}

test('every device config key is edited by one of the settings groups', () => {
  // The entity pickers only show while their relay is off.
  const config = { ...DEVICE_CONFIG_DEFAULTS, use_relay_left: false, use_relay_right: false };
  // Edited through the panel pills, which name neither key.
  const separatelyManagedDefaults = new Set(['home_panel', 'idle_panel', 'idle_panel_extra']);
  const output = SETTINGS_SECTIONS
    .map((section) => flat(dialog({ config, _deviceConfigForm: config, section: section.key }).dlg.render()))
    .join('\n');

  assert.doesNotMatch(output, /Configure colors|Appearance/);
  assert.doesNotMatch(output, /<ha-dialog[ >]/);
  for (const key of Object.keys(DEVICE_CONFIG_DEFAULTS).filter((name) => !separatelyManagedDefaults.has(name))) {
    const renderedKey = key === 'snapshot_max_age_seconds' ? 'snapshot_max_age_mode' : key;
    assert.ok(output.includes(renderedKey), `settings form exposes ${key}`);
  }
});

test('the home and idle panels keep their assignments and save them', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const panels = [
    { key: 'kitchen', title: 'Kitchen' },
    { key: 'clock', title: 'Clock' },
    { key: 'weather', title: 'Weather' },
  ];
  const { dlg, events } = dialog({ config, _deviceConfigForm: config, panels, section: 'home' });
  const output = flat(dlg.render());
  assert.match(output, /haui-device-settings-sidebar/);
  assert.match(output, /Home panel/);
  assert.match(output, /Idle panels/);
  assert.doesNotMatch(output, /Panel Assignments/);

  const selectFor = (id) => {
    const select = templates(dlg.render()).find((template) =>
      template.strings[0].includes('<select id=') && template.values.includes(id));
    assert.ok(select, `${id} select is rendered`);
    const eventIndex = select.strings.findIndex((part) => part.trimEnd().endsWith('@change='));
    return select.values[eventIndex];
  };
  selectFor('dc-home-panel')({ currentTarget: { value: 'kitchen' } });
  selectFor('dc-idle-panels')({ currentTarget: { value: 'clock' } });

  dlg._dispatchSave();
  assert.deepEqual(events[0].detail.config, {
    ...config, home_panel: 'kitchen', idle_panel: 'clock', idle_panel_extra: '',
  });
});

test('the General group carries the theme choice instead of a theme sidebar row', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const { dlg, events } = dialog({
    config, _deviceConfigForm: config, panels: [], section: 'general',
    builtinThemes: { dark: {}, light: {} },
    customThemes: { evening: { name: 'Evening' } },
  });
  const root = render(dlg.render());

  assert.ok(root.querySelector('#dc-theme_id'));
  // The theme choice is a field of the form now, not a row that opens an editor.
  assert.equal(byRole(root, 'button', { name: 'Theme' }), null);
  assert.deepEqual(events, []);
});

test('a save in a sidebar opened from the settings survives saving the settings', () => {
  const before = { ...DEVICE_CONFIG_DEFAULTS, schedule: [] };
  const { dlg, events } = dialog({ config: before, panels: [], section: 'advanced' });
  dlg.willUpdate(new Map([['config', undefined]]));
  const level = render(dlg.render()).querySelector('#dc-log_level');
  level.value = 'DEBUG';
  level.dispatchEvent(new Event('change', { bubbles: true }));

  // A sidebar opened from the settings (theme, updates) saved: the store hands them its new config.
  const after = { ...before, schedule: [{ start: '22:00', end: 'sunrise', sound: false }], brightness: 40 };
  dlg.config = after;
  dlg.willUpdate(new Map([['config', before]]));
  dlg._dispatchSave();

  assert.deepEqual(events.at(-1).detail.config, { ...after, log_level: 'DEBUG' });
});

test('the gesture names offered match the Python GESTURES tuple', () => {
  assert.deepEqual(GESTURE_NAMES, ['swipe_left', 'swipe_right', 'swipe_up', 'swipe_down']);
});

test('the idle panels keep their order and can be reordered by dragging', () => {
  const config = {
    ...DEVICE_CONFIG_DEFAULTS, home_panel: 'light', idle_panel: 'clock',
    idle_panel_extra: 'weather, photo',
  };
  const panels = [
    { key: 'clock', title: 'Clock' }, { key: 'weather', title: 'Weather' },
    { key: 'photo', title: 'Photo' }, { key: 'light', title: 'Light' },
  ];
  const { dlg, events } = dialog({ config, _deviceConfigForm: config, panels, section: 'home' });
  const view = dlg.render();
  const idleRows = templates(view).filter((template) => template.strings[0].includes('<li class="haui-pill"'));
  const row = (name) => idleRows.find((template) => flat(template).includes(name));
  const weather = row('Weather');
  const clock = row('Clock');
  assert.ok(weather);
  assert.ok(clock);

  const handle = templates(weather).find((template) => template.strings[0].includes('haui-sort-handle'));
  assert.ok(handle, 'the idle pill has a drag handle');
  const start = handle.values[handle.strings.findIndex((part) => part.trimEnd().endsWith('@dragstart='))];
  const sourceRow = { classList: { add() {}, remove() {} } };
  start({
    currentTarget: { closest: () => sourceRow },
    dataTransfer: { setData() {}, setDragImage() {}, effectAllowed: '' },
  });
  const drop = clock.values[clock.strings.findIndex((part) => part.trimEnd().endsWith('@drop='))];
  const targetRow = {
    classList: { remove() {} },
    getBoundingClientRect: () => ({ top: 0, height: 20 }),
  };
  drop({ currentTarget: targetRow, clientY: 1, preventDefault() {} });

  dlg._dispatchSave();
  assert.deepEqual(events[0].detail.config, {
    ...config, idle_panel: 'weather', idle_panel_extra: 'clock, photo',
  });
});

test('removing a gesture keeps the others, and their fold states, as they were', () => {
  const gestures = DEVICE_CONFIG_DEFAULTS.gestures;
  const changes = [];
  const result = gestureEditor({ gestures, onChange: (next) => changes.push(next) });
  const removeButtons = templates(result).filter((template) => template.values.includes('Remove gesture'));
  assert.equal(removeButtons.length, 4);
  const remove = removeButtons[1].values.find((value) => typeof value === 'function');
  // The rendered rows, by position: only the third one is open.
  const rows = [{ open: false }, { open: false }, { open: true }, { open: false }];
  const editorElement = {
    querySelectorAll: (selector) => (selector === ':scope > details.haui-entry' ? rows : []),
  };
  remove({
    preventDefault() {},
    currentTarget: { closest: (selector) => (selector === '.haui-entry-list' ? editorElement : null) },
  });

  assert.deepEqual(changes, [[gestures[0], gestures[2], gestures[3]]]);
  // Lit drops the last row; the open Swipe up entry now renders in the second one and stays open.
  assert.deepEqual(rows.slice(0, 3).map((row) => row.open), [false, true, false]);
});

test('an unfinished gesture says what it still lacks', () => {
  assert.equal(gestureSwipesLabel({ swipes: [] }), 'No swipes');
  assert.equal(gestureActionLabel(''), 'No action');
  assert.equal(gestureSwipesLabel({ swipes: ['swipe_up'] }), 'Swipe up');
  assert.equal(gestureActionLabel('gone'), 'gone');
});

test('a new gesture opens, folding it again keeps it, and the settings save it', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, locale: 'de_DE' };
  const { dlg, events } = dialog({ config, _deviceConfigForm: config, panels: [], section: 'gestures' });
  const entries = (view) => templates(view).filter((template) =>
    template.strings[0].includes('<details class="haui-entry"'));
  const openStates = (view) => entries(view).map((entry) => entry.values[0]);

  assert.deepEqual(openStates(dlg.render()), [false, false, false, false]);
  const add = templates(dlg.render()).find((template) => template.values.includes('panel-gesture_add'));
  add.values.find((value) => typeof value === 'function')();
  assert.deepEqual(openStates(dlg.render()), [false, false, false, false, true]);

  const added = entries(dlg.render())[4];
  added.values.find((value) => typeof value === 'function')({ target: { open: false } });
  assert.deepEqual(openStates(dlg.render()), [false, false, false, false, false]);

  // The one footer saves the entries with the rest of the settings.
  dlg._dispatchSave();
  const saved = events.at(-1).detail.config;
  assert.equal(saved.locale, 'de_DE');
  assert.deepEqual(saved.gestures, [
    ...DEVICE_CONFIG_DEFAULTS.gestures, { swipes: [], action: '', timeframe: 3 },
  ]);
  // Which entry is unfolded is view state, never config.
  assert.equal('expandedEntryIndex' in saved, false);
});
