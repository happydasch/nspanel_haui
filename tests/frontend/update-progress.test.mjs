import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

import { updateProgress } from '../../custom_components/nspanel_haui/frontend/ui/update-progress.js';

const START = Date.parse('2026-11-13T12:00:00Z');
const at = (seconds) => START + seconds * 1000;
const progress = (phase, extra = {}) => ({
  phase,
  started_at: new Date(START).toISOString(),
  phase_started_at: new Date(START).toISOString(),
  expected_seconds: 900,
  ...extra,
});

test('the current step is marked and the time left is estimated', () => {
  const root = render(updateProgress({ progress: progress('transferring'), now: at(300), label: 'Display update' }));
  const bar = root.querySelector('[role="progressbar"]');

  assert.equal(bar.getAttribute('aria-label'), 'Display update');
  assert.equal(bar.getAttribute('aria-valuenow'), '33');
  assert.equal(root.querySelector('[aria-current="step"]').textContent.trim(), 'Transferring');
  assert.match(root.textContent, /About 10 min left/);
});

test('the estimate stops short of done until the device confirms', () => {
  const root = render(updateProgress({ progress: progress('verifying'), now: at(1200), label: 'Update' }));

  assert.equal(root.querySelector('[role="progressbar"]').getAttribute('aria-valuenow'), '95');
  assert.match(root.textContent, /Taking longer than usual/);
  assert.equal(root.querySelector('[aria-current="step"]').textContent.trim(), 'Restarting and checking');
});

test('a finished update is complete', () => {
  const root = render(updateProgress({ progress: progress('done'), now: at(600), label: 'Update' }));

  assert.equal(root.querySelector('[role="progressbar"]').getAttribute('aria-valuenow'), '100');
  assert.equal(root.querySelector('[aria-current="step"]').textContent.trim(), 'Done');
});

test('a failed update says so in text', () => {
  const root = render(updateProgress({ progress: progress('failed'), now: at(600), label: 'Update' }));

  assert.equal(root.querySelector('[role="progressbar"]'), null);
  assert.match(root.textContent, /The update failed/);
});

test('nothing shows before an install starts', () => {
  assert.equal(render(updateProgress({ progress: null, label: 'Update' })).textContent.trim(), '');
  assert.equal(render(updateProgress({ progress: progress('scheduled'), label: 'Update' })).textContent.trim(), '');
});
