import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { renderDeviceView, previewControls } from '../../custom_components/nspanel_haui/frontend/views/device.js';
import { deviceDetails } from '../../custom_components/nspanel_haui/frontend/ui/device-details.js';
import { panelActions, panelManager, deviceOptionPanel } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
import { idlePanelConfig, idlePanelKeys } from '../../custom_components/nspanel_haui/frontend/ui/panel-pills.js';
import { deviceActions } from '../../custom_components/nspanel_haui/frontend/ui/device-actions.js';
import { panelCatalog } from '../../custom_components/nspanel_haui/frontend/views/panel-catalog.js';
import { previewStage } from '../../custom_components/nspanel_haui/frontend/ui/preview-stage.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';

function templateText(template) {
  return `${template?.strings?.join(' ') || ''} ${template?.values?.map((value) => {
    if (Array.isArray(value)) return value.map((entry) => entry?.strings ? templateText(entry) : String(entry ?? '')).join(' ');
    return value?.strings ? templateText(value) : String(value ?? '');
  }).join(' ') || ''}`;
}

function templatesMatching(template, marker, found = []) {
  if (!template?.strings) return found;
  if (template.strings.join('').includes(marker)) found.push(template);
  for (const value of template.values) {
    if (Array.isArray(value)) value.forEach((entry) => templatesMatching(entry, marker, found));
    else templatesMatching(value, marker, found);
  }
  return found;
}

/** The `placeholder=` value bound to the input with `id`. */
function placeholderFor(template, id) {
  if (!template?.strings) return undefined;
  const idBound = template.values.includes(id) || template.strings.some((part) => part.includes(`id="${id}"`));
  const index = template.strings.findIndex((part) => part.includes('placeholder='));
  if (idBound && index >= 0) return template.values[index];
  for (const value of template.values) {
    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      const found = placeholderFor(entry, id);
      if (found !== undefined) return found;
    }
  }
  return undefined;
}

function eventBinding(template, id, eventName) {  if (!template?.strings) return undefined;
  const idBound = template.values.includes(id) || template.strings.some((part) => part.includes(`id="${id}"`));
  const eventIndex = template.strings.findIndex((part) => part.trimEnd().endsWith(`${eventName}=`));
  if (idBound && eventIndex >= 0) return template.values[eventIndex];
  for (const value of template.values) {
    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      const found = eventBinding(entry, id, eventName);
      if (found !== undefined) return found;
    }
  }
  return undefined;
}

test('the device options manager does not render Home or Idle page assignment controls', () => {
  const view = panelManager({ panels: [], config: { theme_id: 'dark', schedule: [], gestures: [] } });
  const text = templateText(view);
  assert.match(text, /haui-device-option-controls/);
  assert.doesNotMatch(text, /Home & idle panels|Home panel|Idle panels/);
});

test('the Theme button names the selected theme and leaves the editing to the theme sidebar', () => {
  const view = panelManager({
    panels: [],
    config: { theme_id: 'evening' },
    builtinThemes: { dark: {}, light: {} },
    customThemes: { evening: { name: 'Evening', colors: {} } },
  });
  const themeButton = templatesMatching(view, 'class=')
    .find((entry) => entry.values.includes('haui-button haui-button-outline haui-device-option')
      && templateText(entry).includes('Theme'));
  // The summary is the tooltip: the button itself stays a plain button.
  assert.equal(themeButton.values.includes('Evening'), true);
  assert.doesNotMatch(templateText(view), /haui-device-theme|Edit theme/);
});

const GESTURE_PANELS = [{ key: 'lights', title: 'Lights' }];
const GESTURE_SYSTEM_PANELS = [
  { key: 'sys_about', label: 'About' },
  { key: 'sys_settings', label: 'Settings' },
  { key: 'popup_notify', label: 'Notification', editable: true },
];
const SEQUENCE = { swipes: ['swipe_left', 'swipe_right'], action: 'lights', timeframe: 3 };

test('the Gestures button sums up what each gesture does, like the schedule', () => {
  const view = panelManager({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    config: { ...DEVICE_CONFIG_DEFAULTS, gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE] },
  });
  const text = templateText(view);
  assert.match(text, /5 entries/);
  assert.doesNotMatch(text, /panel-gesture_add/);

  const empty = templateText(panelManager({
    panels: [], config: { ...DEVICE_CONFIG_DEFAULTS, gestures: [] },
  }));
  assert.match(empty, /No gestures: swipes do nothing\./);
  assert.doesNotMatch(empty, /0 entries/);
});

test('the Gestures sidebar lists every gesture as a folded entry below the add button', () => {
  const view = deviceOptionPanel('gestures', {
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    config: { ...DEVICE_CONFIG_DEFAULTS, gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE] },
  });
  const text = templateText(view);
  assert.match(text, /Define swipe gestures to move between panels or open a specific panel/);
  assert.ok(text.indexOf('Define swipe gestures') < text.indexOf('Add gesture'));
  assert.ok(text.indexOf('Add gesture') < text.indexOf('class="haui-entry"'));
  // A single swipe and a sequence are the same kind of entry.
  const entries = templatesMatching(view, 'class="haui-entry"');
  assert.equal(entries.length, 5);
  assert.deepEqual(entries.map((entry) => entry.values[0]), [false, false, false, false, false]);
  assert.match(templateText(entries[0]), /Entry 1/);
  assert.ok(entries[0].values.includes('Swipe left'));
  assert.ok(entries[0].values.includes('Next panel'));
  assert.match(templateText(entries[4]), /Entry 5/);
  assert.ok(entries[4].values.includes('Swipe left → Swipe right'));
  assert.ok(entries[4].values.includes('Lights'));
  assert.ok(entries.every((entry) => templateText(entry).includes('Remove gesture')));
  // Every gesture offers the same actions; a popup needs its caller's context, so none is offered.
  assert.match(templateText(entries[0]), /Previous panel/);
  assert.match(templateText(entries[0]), /Lights \(lights\)/);
  assert.match(templateText(entries[0]), /About \(sys_about\)/);
  assert.doesNotMatch(text, /popup_notify/);
  // Only a sequence has a time limit.
  assert.doesNotMatch(templateText(entries[0]), /panel-gesture_0_timeframe/);
  assert.match(templateText(entries[4]), /panel-gesture_4_timeframe/);
  const root = render(view);
  const foldedEntries = root.querySelectorAll('details');
  assert.equal(foldedEntries.length, 5);
  assert.ok([...foldedEntries].every((entry) => !entry.open));
  assert.ok([...foldedEntries].every((entry) => entry.querySelector('button')));
  assert.ok([...root.querySelectorAll('button')].some((button) => button.textContent.includes('Save')));
});

test('gesture edits go to a draft that keeps every other gesture', () => {
  const drafts = [];
  const view = deviceOptionPanel('gestures', {
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    config: { ...DEVICE_CONFIG_DEFAULTS, locale: 'de_DE', gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE] }, onGestureChange: (draft) => drafts.push(draft),
  });

  eventBinding(view, 'panel-gesture_2_action', '@change')({ target: { value: 'lights' } });
  assert.deepEqual(drafts.at(-1).gestures, [
    ...DEVICE_CONFIG_DEFAULTS.gestures.slice(0, 2),
    { swipes: ['swipe_up'], action: 'lights', timeframe: 3 },
    DEVICE_CONFIG_DEFAULTS.gestures[3],
    SEQUENCE,
  ]);
  assert.equal('locale' in drafts.at(-1), false);

  eventBinding(view, 'panel-gesture_4_timeframe', '@input')({ target: { value: '90' } });
  assert.equal(drafts.at(-1).gestures[4].timeframe, 60);
  const before = drafts.length;
  eventBinding(view, 'panel-gesture_4_timeframe', '@input')({ target: { value: '' } });
  assert.equal(drafts.length, before, 'an emptied box is unfinished typing, not a time limit');

  eventBinding(view, 'panel-gesture_add', '@click')();
  assert.deepEqual(drafts.at(-1).gestures.at(-1), { swipes: [], action: '', timeframe: 3 });
  assert.equal(drafts.at(-1).gestures.length, 6);
  assert.equal(drafts.at(-1).expandedEntryIndex, 5);
});

test('a gesture\'s swipes can be added, dragged into order, and removed', () => {
  const drafts = [];
  const makeView = (gestures) => deviceOptionPanel('gestures', {
    panels: [], systemPanels: [], config: { ...DEVICE_CONFIG_DEFAULTS, gestures }, onGestureChange: (draft) => drafts.push(draft),
  });
  let view = makeView([{ swipes: ['swipe_left', 'swipe_right'], action: '', timeframe: 3 }]);
  let pills = templatesMatching(view, 'class="haui-pill"');
  assert.equal(pills.length, 2);
  assert.match(templateText(pills[0]), /Swipe left/);
  assert.match(templateText(pills[1]), /Swipe right/);
  assert.match(templateText(view), /Drag swipes into order/);

  const handle = templatesMatching(pills[0], 'draggable="true"')[0];
  const dragStartIndex = handle.strings.findIndex((part) => part.trimEnd().endsWith('@dragstart='));
  handle.values[dragStartIndex]({
    currentTarget: { closest: () => ({ classList: { add() {}, remove() {} } }) },
    dataTransfer: { setData() {}, setDragImage() {}, effectAllowed: '' },
  });
  const dropIndex = pills[1].strings.findIndex((part) => part.trimEnd().endsWith('@drop='));
  pills[1].values[dropIndex]({
    currentTarget: {
      classList: { remove() {} },
      getBoundingClientRect: () => ({ left: 0, right: 100, width: 100, top: 0, bottom: 26 }),
    },
    clientX: 80, clientY: 13, preventDefault() {},
  });
  assert.deepEqual(drafts.at(-1).gestures[0].swipes, ['swipe_right', 'swipe_left']);

  view = makeView(drafts.at(-1).gestures);
  const select = { value: 'swipe_up' };
  eventBinding(view, 'panel-gesture_0_add_swipe', '@change')({ currentTarget: select });
  assert.equal(select.value, '');
  assert.deepEqual(drafts.at(-1).gestures[0].swipes, ['swipe_right', 'swipe_left', 'swipe_up']);

  view = makeView(drafts.at(-1).gestures);
  pills = templatesMatching(view, 'class="haui-pill"');
  const removeIndex = pills[0].strings.findIndex((part) => part.trimEnd().endsWith('@click='));
  pills[0].values[removeIndex]();
  assert.deepEqual(drafts.at(-1).gestures[0].swipes, ['swipe_left', 'swipe_up']);

  // One swipe left: no order to drag and no time limit.
  view = makeView([{ swipes: ['swipe_up'], action: 'lights', timeframe: 3 }]);
  assert.doesNotMatch(templateText(view), /Drag swipes into order|panel-gesture_0_timeframe/);
});



test('the unified idle list composes and splits the existing string settings in order', () => {
  assert.deepEqual(idlePanelKeys('clock', 'weather, gone, clock'), ['clock', 'weather', 'gone']);
  assert.deepEqual(idlePanelConfig(['weather', 'gone', 'weather']), {
    idle_panel: 'weather', idle_panel_extra: 'gone',
  });
  assert.deepEqual(idlePanelConfig([]), { idle_panel: '', idle_panel_extra: '' });
});
