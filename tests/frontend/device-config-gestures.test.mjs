import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { gestureEditor, gestureSummary } from '../../custom_components/nspanel_haui/frontend/ui/gesture-editor.js';
import { deviceOptionPanel } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
import { DEVICE_CONFIG_DEFAULTS, GESTURE_NAMES } from '../../custom_components/nspanel_haui/frontend/constants.js';

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

test('device settings include Special pages and save Home and Idle assignments', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, use_relay_left: false, use_relay_right: false };
  const panels = [
    { key: 'kitchen', title: 'Kitchen' },
    { key: 'clock', title: 'Clock' },
    { key: 'weather', title: 'Weather' },
  ];
  const { dlg, events } = dialog({ config, _deviceConfigForm: config, inline: true, panels });
  const output = flat(dlg.render());
  const separatelyManagedDefaults = new Set([
    'theme_variant', 'theme_id', 'home_panel', 'idle_panel', 'idle_panel_extra', 'schedule', 'gestures',
  ]);

  assert.match(output, /haui-device-settings-sidebar/);
  assert.doesNotMatch(output, /Configure colors|Appearance/);
  assert.doesNotMatch(output, /<ha-dialog[ >]/);
  for (const key of Object.keys(DEVICE_CONFIG_DEFAULTS).filter((name) => !separatelyManagedDefaults.has(name))) {
    const renderedKey = key === 'snapshot_max_age_seconds' ? 'snapshot_max_age_mode' : key;
    assert.ok(output.includes(renderedKey), `settings form exposes ${key}`);
  }
  assert.match(output, /Special pages/);
  assert.match(output, /Home panel/);
  assert.match(output, /Idle panels/);
  assert.doesNotMatch(output, /Panel Assignments|<summary>Schedule|<summary>Gestures/);
  assert.doesNotMatch(output, /dc-schedule|dc-gesture/);

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

test('the gesture names offered match the Python GESTURES tuple', () => {
  assert.deepEqual(GESTURE_NAMES, ['swipe_left', 'swipe_right', 'swipe_up', 'swipe_down']);
});

test('Special pages preserves idle order and lets panels be reordered by dragging', () => {
  const config = {
    ...DEVICE_CONFIG_DEFAULTS, home_panel: 'light', idle_panel: 'clock',
    idle_panel_extra: 'weather, photo',
  };
  const panels = [
    { key: 'clock', title: 'Clock' }, { key: 'weather', title: 'Weather' },
    { key: 'photo', title: 'Photo' }, { key: 'light', title: 'Light' },
  ];
  const { dlg, events } = dialog({ config, _deviceConfigForm: config, panels });
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
  assert.equal(gestureSummary([{ swipes: [], action: '', timeframe: 3 }]), 'No swipes: No action');
  assert.equal(gestureSummary([{ swipes: ['swipe_up'], action: 'gone', timeframe: 3 }]), 'Swipe up: gone');
});

test('gestures are edited in a draft: only a new one opens, and Save writes them', async () => {
  const { NSPanelEditor } = await import('../../custom_components/nspanel_haui/frontend/app/shell.js');
  const editor = Object.assign(document.createElement('nspanel-haui-editor'), {
    _selectedDevice: 'kitchen', _deviceConfig: { ...DEVICE_CONFIG_DEFAULTS, locale: 'de_DE' }, _saving: false,
    _store: { actions: { closeOverlay() {} } },
    _restoreSidebarFocus() {},
  });
  const render = () => deviceOptionPanel('gestures', {
    panels: [], config: editor._deviceConfig, gestureDraft: editor._gestureDraft,
    onGestureChange: (draft) => editor._changeGestures(draft),
    onGestureEntryToggle: (index, isOpen) => editor._onGestureEntryToggle(index, isOpen),
    onGestureSave: () => editor._saveGestures(),
  });
  const entries = (view) => templates(view).filter((template) =>
    template.strings[0].includes('<details class="haui-entry"'));
  const openStates = (view) => entries(view).map((entry) => entry.values[0]);
  const saveButton = (view) => templates(view).find((template) =>
    template.strings.join('').includes('class=') && template.values.includes('Save'));

  assert.deepEqual(openStates(render()), [false, false, false, false]);
  const add = templates(render()).find((template) => template.values.includes('panel-gesture_add'));
  add.values.find((value) => typeof value === 'function')();
  assert.deepEqual(openStates(render()), [false, false, false, false, true]);
  assert.ok(saveButton(render()));

  const added = entries(render())[4];
  added.values.find((value) => typeof value === 'function')({ target: { open: false } });
  assert.deepEqual(openStates(render()), [false, false, false, false, false]);

  const saved = [];
  editor._devicePanels = () => [];
  editor._savePanels = async (_panels, _message, config) => {
    saved.push(config);
    editor._deviceConfig = config;
    return true;
  };
  editor.requestUpdate = () => {};
  await editor._saveGestures();
  assert.equal(saved.length, 1);
  assert.equal(saved[0].locale, 'de_DE');
  assert.deepEqual(saved[0].gestures, [
    ...DEVICE_CONFIG_DEFAULTS.gestures, { swipes: [], action: '', timeframe: 3 },
  ]);
  assert.equal('expandedEntryIndex' in saved[0], false);
  assert.equal(editor._gestureDraft, null);
});
