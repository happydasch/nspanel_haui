import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { entryCount } from '../../custom_components/nspanel_haui/frontend/ui/entry-list.js';
import { scheduleEditor } from '../../custom_components/nspanel_haui/frontend/ui/schedule-editor.js';
import { gestureEditor } from '../../custom_components/nspanel_haui/frontend/ui/gesture-editor.js';

function templates(value) {
  if (Array.isArray(value)) return value.flatMap(templates);
  if (value && value.strings) return [value, ...value.values.flatMap(templates)];
  return [];
}

const cards = (view) => templates(view).filter((template) =>
  template.strings[0].includes('<details class="haui-entry"'));

test('the schedule and the gestures draw their entries with the same card', () => {
  const schedule = scheduleEditor({
    schedule: [{ start: '22:00', end: '07:00', sound: false, display_off: true }],
    onChange() {},
  });
  const gestures = gestureEditor({
    gestures: [{ swipes: ['swipe_left', 'swipe_up'], action: 'next_panel', timeframe: 3 }],
    onChange() {},
  });
  const [scheduleCard] = cards(schedule);
  const [gestureCard] = cards(gestures);

  // One tagged template: Lit hands both the same strings array.
  assert.equal(scheduleCard.strings, gestureCard.strings);
  // The head reads what starts the entry, then what it does.
  assert.ok(scheduleCard.values.includes('22:00 → 07:00'));
  assert.ok(scheduleCard.values.includes('Silent · Screen off'));
  assert.ok(gestureCard.values.includes('Swipe left → Swipe up'));
  assert.ok(gestureCard.values.includes('Next panel'));
  assert.ok(templates(schedule).some((template) => template.values.includes('Remove entry')));
  assert.ok(templates(gestures).some((template) => template.values.includes('Remove gesture')));
});

test('a schedule entry that changes nothing it could turn off has an empty note', () => {
  const [card] = cards(scheduleEditor({
    schedule: [{ start: '08:00', end: '09:00', sound: true, display_off: false }],
    onChange() {},
  }));
  assert.ok(card.values.includes(''));
});

test('the count badge says entries', () => {
  assert.equal(entryCount(1), '1 entry');
  assert.equal(entryCount(4), '4 entries');
});
