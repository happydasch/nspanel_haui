import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scheduleSection } from '../../custom_components/nspanel_haui/frontend/ui/schedule-section.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';

function templateText(template) {
  return `${template?.strings?.join(' ') || ''} ${template?.values?.map((value) => {
    if (Array.isArray(value)) return value.map((entry) => entry?.strings ? templateText(entry) : String(entry ?? '')).join(' ');
    return value?.strings ? templateText(value) : String(value ?? '');
  }).join(' ') || ''}`;
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

/**
 * The schedule of the settings' Screen group, with everything it edits
 * collected: each change is the entries plus the fields it merges into the draft.
 */
function scheduleGroup(config, extra = {}) {
  const changes = [];
  const view = scheduleSection({
    config,
    schedule: config.schedule || [],
    onChange: (schedule, fields = {}) => changes.push({ schedule, ...fields }),
    onAdd: (schedule, fields = {}) => changes.push({ schedule, ...fields }),
    ...extra,
  });
  return { view, changes };
}

test('the schedule of the Screen group edits the settings draft and has no Save of its own', () => {
  const config = {
    ...DEVICE_CONFIG_DEFAULTS,
    brightness: 80,
    schedule: [{
      start: '22:00', end: '07:00', sound: true, brightness: 20,
      display_off: true, timeout_display_off: 30,
    }],
  };
  const { view, changes } = scheduleGroup(config);
  const text = templateText(view);
  assert.match(text, /Set the display by time of day/);
  assert.doesNotMatch(text, /YAML configuration/);
  // The values the entries inherit are the Screen group's own fields, not a copy.
  assert.doesNotMatch(text, /panel-schedule-base-/);
  assert.doesNotMatch(text, /Outside the entries/);
  assert.match(text, /panel-schedule_0_start_time/);
  // The sidebar's one footer saves, not a button of this group.
  assert.doesNotMatch(text, /Save/);

  const onInput = eventBinding(view, 'panel-schedule_0_start_time', '@input');
  onInput({ target: { value: '21:30' } });
  assert.equal(changes.at(-1).schedule[0].start, '21:30');
});

test('the first entry brings the panel brightness along when the hub sets none', () => {
  const { view, changes } = scheduleGroup(
    { brightness: null, brightness_dim: null, schedule: [] },
    { deviceBrightness: { full: 62, dimmed: 15 } },
  );

  // A new entry takes the panel's full brightness, not an invented 100.
  eventBinding(view, 'panel-schedule_add', '@click')();
  assert.equal(changes[0].brightness, 62);

  // The group says that saving sets it.
  const added = templateText(scheduleSection({
    config: { brightness: 62, schedule: changes[0].schedule },
    schedule: changes[0].schedule,
    addedBrightness: 62,
  }));
  assert.match(added, /full brightness to 62%/);

  // A hub setting stays: the entry brings none of its own.
  eventBinding(scheduleGroup(
    { brightness: 40, schedule: [] },
    { deviceBrightness: { full: 62 } },
  ).view, 'panel-schedule_add', '@click')();
});

test('an entry that dims brings the panel dimmed brightness along when the hub sets none', () => {
  const entry = { start: '22:00', end: '07:00', sound: true, brightness: 20, display_off: true };
  const { view, changes } = scheduleGroup(
    { brightness: 80, brightness_dim: null, schedule: [entry] },
    { deviceBrightness: { full: 80, dimmed: 15 } },
  );

  // The entry's dimmed brightness needs one to return to when it ends.
  eventBinding(view, 'panel-schedule_0_brightness_dim', '@input')({ target: { value: '2' } });
  assert.equal(changes.at(-1).brightness_dim, 15);

  const added = templateText(scheduleSection({
    config: { brightness: 80, brightness_dim: 15, schedule: [entry] },
    schedule: [entry],
    addedBrightnessDim: 15,
  }));
  assert.match(added, /dimmed brightness to 15%/);

  // A hub setting stays, and an entry that leaves it empty needs none.
  const kept = scheduleGroup(
    { brightness: 80, brightness_dim: 30, schedule: [entry] },
    { deviceBrightness: { dimmed: 15 } },
  );
  eventBinding(kept.view, 'panel-schedule_0_brightness_dim', '@input')({ target: { value: '2' } });
  assert.equal(kept.changes.at(-1).brightness_dim, undefined);
  eventBinding(view, 'panel-schedule_0_start_time', '@input')({ target: { value: '21:30' } });
  assert.equal(changes.at(-1).brightness_dim, undefined);
});

test('an entry inherit hint names the panel brightness when the hub sets none', () => {
  const { view } = scheduleGroup({
    brightness: null,
    brightness_dim: null,
    timeout_dimming: 10,
    schedule: [{ start: '22:00', end: '07:00', sound: true, display_off: true, timeout_display_off: 30 }],
  }, { deviceBrightness: { full: 62, dimmed: 15 } });

  assert.equal(placeholderFor(view, 'panel-schedule_0_brightness'), 'Inherit (62)');
  assert.equal(placeholderFor(view, 'panel-schedule_0_brightness_dim'), 'Inherit (15)');
});

test('adding the first inline Schedule entry sets the required outside brightness', () => {
  const { view, changes } = scheduleGroup({ brightness: null, schedule: [] });
  eventBinding(view, 'panel-schedule_add', '@click')();
  assert.equal(changes[0].brightness, 100);
  assert.deepEqual(changes[0].schedule, [{
    start: '22:00', start_offset: 0, end: '07:00', end_offset: 0,
    sound: true, brightness: 20, brightness_dim: null, display_off: true,
    timeout_dimming: null, timeout_display_off: 30, duration_dimming: null,
  }]);
});
