import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { relativeTime, uptimeLabel, versionLabel } from '../../custom_components/nspanel_haui/frontend/ui/format.js';

test('relative time localizes known past and future dates and labels invalid values', () => {
  const now = Date.UTC(2026, 0, 1, 12);
  assert.equal(relativeTime(new Date(now - 60_000).toISOString(), { now }), '1 minute ago');
  assert.equal(relativeTime(new Date(now + 3_600_000).toISOString(), { now }), 'in 1 hour');
  assert.equal(relativeTime('not-a-date', { now }), 'Unknown');
});

test('relative time rounds into the next unit and reads a slightly early clock as now', () => {
  const now = Date.UTC(2026, 0, 1, 12);
  const ago = (seconds) => relativeTime(new Date(now - seconds * 1000).toISOString(), { now });
  assert.equal(ago(3_599), '1 hour ago');
  assert.equal(ago(364 * 86_400), 'last year');
  assert.equal(ago(90), '2 minutes ago');
  // The hub's clock runs 3 s ahead of the browser's.
  assert.equal(relativeTime(new Date(now + 3_000).toISOString(), { now }), 'now');
});

test('uptime labels choose compact units and reject missing or invalid durations', () => {
  assert.equal(uptimeLabel(3 * 86_400 + 14 * 3_600), '3d 14h');
  assert.equal(uptimeLabel(90 * 60), '1h 30m');
  assert.equal(uptimeLabel(25 * 60), '25m');
  assert.equal(uptimeLabel(32), '32s');
  assert.equal(uptimeLabel(Number.NaN), 'Unknown');
});

test('version labels do not pretend an empty report is a version', () => {
  assert.equal(versionLabel('0.5.0'), '0.5.0');
  assert.equal(versionLabel(''), 'Unknown');
});
