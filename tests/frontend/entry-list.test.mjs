import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { entryCount } from '../../custom_components/nspanel_haui/frontend/ui/entry-list.js';
import { scheduleEditor } from '../../custom_components/nspanel_haui/frontend/ui/schedule-editor.js';
import { gestureEditor } from '../../custom_components/nspanel_haui/frontend/ui/gesture-editor.js';
import { render } from './support/render.mjs';

test('schedule and gesture entries show their summary and report removal', () => {
  const changes = [];
  const scheduleRoot = render(scheduleEditor({
    schedule: [{ start: '22:00', end: '07:00', sound: false, display_off: true }],
    onChange: (next) => changes.push(['schedule', next]),
  }));
  const gestureRoot = render(gestureEditor({
    gestures: [{ swipes: ['swipe_left', 'swipe_up'], action: 'next_panel', timeframe: 3 }],
    onChange: (next) => changes.push(['gesture', next]),
  }));

  assert.equal(scheduleRoot.querySelectorAll('details').length, 1);
  assert.equal(gestureRoot.querySelectorAll('details').length, 1);
  assert.ok(scheduleRoot.querySelector('summary').textContent.includes('22:00 → 07:00'));
  assert.ok(gestureRoot.querySelector('summary').textContent.includes('Swipe left → Swipe up'));
  assert.ok(gestureRoot.querySelector('summary').textContent.includes('Next panel'));

  scheduleRoot.querySelector('button[aria-label="Remove entry"]').click();
  gestureRoot.querySelector('button[aria-label="Remove gesture"]').click();
  assert.deepEqual(changes, [['schedule', []], ['gesture', []]]);
});

test('the count badge formats singular and plural entry counts', () => {
  assert.equal(entryCount(1), '1 entry');
  assert.equal(entryCount(4), '4 entries');
});
