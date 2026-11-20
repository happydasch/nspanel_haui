import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';
import {
  themeLabel,
  updatesSummary,
} from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
import { gestureSection } from '../../custom_components/nspanel_haui/frontend/ui/gesture-section.js';
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

test("the update summary carries what the Updates row of Connection & device shows", () => {
  const config = {
    ...DEVICE_CONFIG_DEFAULTS,
    update: { ...DEVICE_CONFIG_DEFAULTS.update, firmware_update_channel: 'stable', firmware_auto_update: false },
  };
  assert.equal(updatesSummary(config), 'Stable · Manual');
  const automatic = { ...config, update: { ...config.update, firmware_update_channel: 'dev', firmware_auto_update: true } };
  assert.equal(updatesSummary(automatic), 'Development · Auto');
  const off = { ...config, update: { ...config.update, enabled: false } };
  assert.equal(updatesSummary(off), 'Off');
});

test("the Themes row names the device's theme, not its key", () => {
  // A predefined theme reads with its label before the theme library has loaded.
  assert.equal(themeLabel('dark', {}, {}), 'Dark Color');
  assert.equal(themeLabel('midnight', {}, {}), 'Midnight');
  // A device without a stored choice draws with the predefined dark theme.
  assert.equal(themeLabel('', {}, {}), 'Dark Color');
  // A custom theme reads with the name the library holds.
  assert.equal(themeLabel('evening', {}, { evening: { name: 'Evening' } }), 'Evening');
  // A predefined theme this editor has no label for still reads with the hub's name.
  assert.equal(themeLabel('aurora', { aurora: { name: 'Aurora' } }, {}), 'Aurora');
  // Nothing known at all: the key is all there is to show.
  assert.equal(themeLabel('gone', {}, {}), 'gone');
});

const GESTURE_PANELS = [{ key: 'lights', title: 'Lights' }];
const GESTURE_SYSTEM_PANELS = [
  { key: 'sys_about', label: 'About' },
  { key: 'sys_settings', label: 'Settings' },
  { key: 'popup_notify', label: 'Notification', editable: true },
];
const SEQUENCE = { swipes: ['swipe_left', 'swipe_right'], action: 'lights', timeframe: 3 };

test('the Gestures group lists every gesture as a folded entry below the add button', () => {
  const view = gestureSection({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE],
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
  // The sidebar's one footer saves; the group has no Save of its own.
  assert.doesNotMatch(text, /Save/);
});

test('gesture edits go to the settings draft and keep every other gesture', () => {
  const drafts = [];
  const view = gestureSection({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE],
    onChange: (gestures) => drafts.push(gestures),
  });

  eventBinding(view, 'panel-gesture_2_action', '@change')({ target: { value: 'lights' } });
  assert.deepEqual(drafts.at(-1), [
    ...DEVICE_CONFIG_DEFAULTS.gestures.slice(0, 2),
    { swipes: ['swipe_up'], action: 'lights', timeframe: 3 },
    DEVICE_CONFIG_DEFAULTS.gestures[3],
    SEQUENCE,
  ]);

  eventBinding(view, 'panel-gesture_4_timeframe', '@input')({ target: { value: '90' } });
  assert.equal(drafts.at(-1)[4].timeframe, 60);
  const before = drafts.length;
  eventBinding(view, 'panel-gesture_4_timeframe', '@input')({ target: { value: '' } });
  assert.equal(drafts.length, before, 'an emptied box is unfinished typing, not a time limit');

  const added = [];
  eventBinding(gestureSection({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE],
    onAdd: (gestures) => added.push(gestures),
  }), 'panel-gesture_add', '@click')();
  assert.deepEqual(added.at(-1).at(-1), { swipes: [], action: '', timeframe: 3 });
  assert.equal(added.at(-1).length, 6);
});

test('a gesture\'s swipes can be added, dragged into order, and removed', () => {
  const drafts = [];
  const makeView = (gestures) => gestureSection({
    panels: [], systemPanels: [], gestures, onChange: (next) => drafts.push(next),
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
  assert.deepEqual(drafts.at(-1)[0].swipes, ['swipe_right', 'swipe_left']);

  view = makeView(drafts.at(-1));
  const select = { value: 'swipe_up' };
  eventBinding(view, 'panel-gesture_0_add_swipe', '@change')({ currentTarget: select });
  assert.equal(select.value, '');
  assert.deepEqual(drafts.at(-1)[0].swipes, ['swipe_right', 'swipe_left', 'swipe_up']);

  view = makeView(drafts.at(-1));
  pills = templatesMatching(view, 'class="haui-pill"');
  const removeIndex = pills[0].strings.findIndex((part) => part.trimEnd().endsWith('@click='));
  pills[0].values[removeIndex]();
  assert.deepEqual(drafts.at(-1)[0].swipes, ['swipe_left', 'swipe_up']);

  // One swipe left: no order to drag and no time limit.
  view = makeView([{ swipes: ['swipe_up'], action: 'lights', timeframe: 3 }]);
  assert.doesNotMatch(templateText(view), /Drag swipes into order|panel-gesture_0_timeframe/);
});
