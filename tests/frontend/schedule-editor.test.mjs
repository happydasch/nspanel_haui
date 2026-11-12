import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { panelManager } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';

const config = {
  schedule: [],
  brightness: 100,
  sound_on_notification: false,
  timeout_dimming: 10,
  duration_dimming: 2,
  use_auto_display_off: true,
  timeout_display_off: 120,
};

function findBinding(template, id, marker) {
  if (Array.isArray(template)) {
    for (const child of template) {
      const binding = findBinding(child, id, marker);
      if (binding !== undefined) return binding;
    }
    return undefined;
  }
  if (!template?.strings) return undefined;

  for (let i = 0; i < template.strings.length; i++) {
    if (!template.strings[i].includes(`id="${id}"`) &&
      !(template.strings[i].includes('id=') && template.values[i] === id)) continue;
    for (let j = i; j < template.strings.length; j++) {
      if (template.strings[j].trimEnd().endsWith(marker)) return template.values[j];
    }
  }
  for (const child of template.values) {
    const binding = findBinding(child, id, marker);
    if (binding !== undefined) return binding;
  }
  return undefined;
}

function renderSchedule(onScheduleChange) {
  return panelManager({
    panels: [], config, expanded: ['schedule'], onScheduleChange,
    onSetRole() {},
  });
}

test('schedule entries are collapsed by default and only a newly added one opens', async () => {
  const { NSPanelEditor } = await import('../../custom_components/nspanel_haui/frontend/app/shell.js');
  const existing = { start: '08:00', end: '09:00', sound: true, display_off: false };
  const editor = Object.assign(Object.create(NSPanelEditor.prototype), {
    _selectedDevice: 'kitchen', _deviceConfig: { ...config, schedule: [existing] }, _saving: false,
  });
  const render = () => panelManager({
    panels: [], config: editor._deviceConfig, scheduleDraft: editor._scheduleDraft,
    expanded: ['schedule'], onSetRole() {},
    onScheduleChange: (draft) => editor._changeSchedule(draft),
    onScheduleEntryToggle: (index, isOpen) => editor._onScheduleEntryToggle(index, isOpen),
  });
  const assertOpenStates = (view, states) => {
    const entries = findScheduleEntries(view);
    assert.equal(entries.length, states.length);
    assert.deepEqual(entries.map((entry) => entry.values[0]), states);
  };

  assertOpenStates(render(), [false]);
  const addButton = findBinding(render(), 'panel-schedule_add', '@click=');
  assert.equal(typeof addButton, 'function');
  addButton();
  assertOpenStates(render(), [false, true]);

  const addedEntry = findScheduleEntries(render())[1];
  const onToggle = addedEntry.values.find((value) => typeof value === 'function');
  onToggle({ target: { open: false } });
  assertOpenStates(render(), [false, false]);

  editor._devicePanels = () => [];
  editor._savePanels = async (_panels, _message, savedConfig) => {
    editor._deviceConfig = savedConfig;
    return true;
  };
  editor.requestUpdate = () => {};
  await editor._saveSchedule();
  assertOpenStates(render(), [false, false]);
  assert.equal('expandedEntryIndex' in editor._deviceConfig, false);
});

test('removing a schedule entry keeps every other entry folded as it was', () => {
  const entries = ['08:00', '12:00', '18:00'].map((start) => ({ start, end: '20:00', sound: true }));
  const changes = [];
  const view = panelManager({
    panels: [], config: { ...config, schedule: entries }, expanded: ['schedule'], onSetRole() {},
    onScheduleChange: (draft) => changes.push(draft.schedule),
  });
  const removeButton = findTemplate(findScheduleEntries(view)[0], (template) => template.values.includes('Remove entry'));
  const remove = removeButton.values.find((value) => typeof value === 'function');
  // The rendered rows, by position: only the second one is open.
  const rows = [{ open: false }, { open: true }, { open: false }];
  const editorElement = {
    querySelectorAll: (selector) => (selector === ':scope > details.haui-entry' ? rows : []),
  };
  remove({
    preventDefault() {},
    currentTarget: { closest: (selector) => (selector === '.haui-entry-list' ? editorElement : null) },
  });

  assert.deepEqual(changes, [[entries[1], entries[2]]]);
  // Lit drops the last row; the open 12:00 entry now renders in the first one and stays open.
  assert.deepEqual(rows.slice(0, 2).map((row) => row.open), [true, false]);
});

function findTemplate(template, predicate) {
  if (Array.isArray(template)) return template.map((child) => findTemplate(child, predicate)).find(Boolean);
  if (!template?.strings) return undefined;
  if (predicate(template)) return template;
  return template.values.map((child) => findTemplate(child, predicate)).find(Boolean);
}

function findScheduleEntries(template, found = []) {
  if (Array.isArray(template)) {
    template.forEach((child) => findScheduleEntries(child, found));
    return found;
  }
  if (!template?.strings) return found;
  if (template.strings[0].includes('<details class="haui-entry"')) found.push(template);
  template.values.forEach((child) => findScheduleEntries(child, found));
  return found;
}

test('schedule defaults expose every device setting overridden by an entry', () => {
  const rendered = renderSchedule(() => {});

  for (const id of [
    'panel-schedule-base-brightness',
    'panel-schedule-base-brightness_dim',
    'panel-schedule-base-timeout_dimming',
    'panel-schedule-base-duration_dimming',
    'panel-schedule-base-timeout_display_off',
  ]) {
    assert.notEqual(findBinding(rendered, id, '.value='), undefined, `${id} is rendered`);
  }
  assert.equal(findBinding(rendered, 'panel-schedule-base-sound_on_notification', '?checked='), false);
  assert.equal(findBinding(rendered, 'panel-schedule-base-use_auto_display_off', '?checked='), true);
});

test('schedule default fields update their device settings without dropping other values', () => {
  const cases = [
    ['panel-schedule-base-timeout_dimming', '@input=', { timeout_dimming: 25 }, { target: { value: '25' } }],
    ['panel-schedule-base-duration_dimming', '@input=', { duration_dimming: 1.5 }, { target: { value: '1.5' } }],
    ['panel-schedule-base-sound_on_notification', '@change=', { sound_on_notification: true }, { target: { checked: true } }],
    ['panel-schedule-base-use_auto_display_off', '@change=', { use_auto_display_off: false }, { target: { checked: false } }],
  ];

  for (const [id, marker, expected, event] of cases) {
    let draft;
    const handler = findBinding(renderSchedule((value) => { draft = value; }), id, marker);
    assert.equal(typeof handler, 'function', `${id} has an event handler`);
    handler(event);
    assert.deepEqual(draft, { ...config, ...expected });
  }
});
test('saving schedule defaults persists them with the schedule', async () => {
  const { NSPanelEditor } = await import('../../custom_components/nspanel_haui/frontend/app/shell.js');
  const editor = Object.assign(Object.create(NSPanelEditor.prototype), {
    _selectedDevice: 'kitchen',
    _deviceConfig: config,
    _saving: false,
    _devicePanels: () => [],
    requestUpdate() {},
    async _savePanels(_panels, _message, deviceConfig) {
      this.savedConfig = deviceConfig;
      return true;
    },
  });
  const draft = {
    ...config,
    schedule: [{ start: '22:00', end: '07:00', sound: true, brightness: 20, display_off: true }],
    sound_on_notification: true,
    timeout_dimming: 25,
    duration_dimming: 1.5,
    use_auto_display_off: false,
    timeout_display_off: 60,
  };

  editor._changeSchedule(draft);
  await editor._saveSchedule();

  assert.equal(editor.savedConfig.sound_on_notification, true);
  assert.equal(editor.savedConfig.timeout_dimming, 25);
  assert.equal(editor.savedConfig.duration_dimming, 1.5);
  assert.equal(editor.savedConfig.use_auto_display_off, false);
  assert.equal(editor.savedConfig.timeout_display_off, 60);
  assert.deepEqual(editor.savedConfig.schedule, draft.schedule);
});

