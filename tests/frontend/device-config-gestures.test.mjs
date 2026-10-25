import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { GESTURE_NAMES } from '../../custom_components/nspanel_haui/frontend/constants.js';

/** A dialog instance without Lit's constructor (which needs a real DOM). */
function dialog(props = {}) {
  const dlg = Object.create(customElements.get('nspanel-dialog-device-config').prototype);
  const events = [];
  Object.assign(dlg, { requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

const PANELS = [{ value: '', label: '- None -' }, { value: 'lights', label: 'lights' }];

test('the gesture names offered match the Python GESTURES tuple', () => {
  assert.deepEqual(GESTURE_NAMES, ['swipe_left', 'swipe_right', 'swipe_up', 'swipe_down']);
});

test('adding, editing and removing a gesture sequence updates the form the dialog saves', () => {
  const { dlg, events } = dialog({ _deviceConfigForm: { locale: 'en_US' } });

  dlg._updateGestureSequences((list) => [...list, { sequence: ['swipe_left', 'swipe_right'], timeframe: 3, open: '' }]);
  assert.deepEqual(dlg._deviceConfigForm.gesture_sequences, [
    { sequence: ['swipe_left', 'swipe_right'], timeframe: 3, open: '' },
  ]);

  dlg._updateGestureSequences((list) => { list[0] = { ...list[0], open: 'lights', timeframe: 5 }; return list; });
  assert.equal(dlg._deviceConfigForm.gesture_sequences[0].open, 'lights');
  assert.equal(dlg._deviceConfigForm.gesture_sequences[0].timeframe, 5);
  assert.equal(dlg._deviceConfigForm.locale, 'en_US', 'other settings are kept');

  dlg._dispatchSave();
  assert.equal(events[0].type, 'dialog-save');
  assert.deepEqual(events[0].detail.config.gesture_sequences[0].sequence, ['swipe_left', 'swipe_right']);

  dlg._updateGestureSequences((list) => list.filter((_, i) => i !== 0));
  assert.deepEqual(dlg._deviceConfigForm.gesture_sequences, []);
});

test('a sequence row shows its swipes, time limit and target panel', () => {
  const { dlg } = dialog({ _deviceConfigForm: {} });
  const row = flat(dlg._renderGestureSequence({ sequence: ['swipe_up', 'swipe_down'], timeframe: 7, open: 'lights' }, 2, PANELS));
  assert.match(row, /dc-gesture_sequence_2/);
  assert.match(row, /swipe_up, swipe_down/);
  assert.match(row, /dc-gesture_timeframe_2/);
  assert.match(row, /dc-gesture_open_2/);
  assert.match(row, /mdi:delete-outline/);
});
