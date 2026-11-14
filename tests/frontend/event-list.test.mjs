import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

function templateText(template) {
  return render(template).innerHTML;
}

import { eventList, eventsInLast24Hours, latestEvents, parseEvent } from '../../custom_components/nspanel_haui/frontend/ui/event-list.js';

test('Latest events lists a repeated message once with its count, and no debug lines', () => {
  const missing = "Entity 'cover.hall' not available for state";
  const events = [
    { deviceName: 'Kitchen', line: `[2026-01-01T12:00:00Z] WARNING ${missing}` },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:01Z] DEBUG Heartbeat sent' },
    { deviceName: 'Kitchen', line: `[2026-01-01T12:00:02Z] WARNING ${missing}` },
    { deviceName: 'Office', line: `[2026-01-01T12:00:03Z] WARNING ${missing}` },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:04Z] ERROR Template failed\nTraceback (most recent call last)' },
  ];
  const latest = latestEvents(events);
  assert.deepEqual(latest.map((event) => [event.deviceName, parseEvent(event.line).level, event.count]), [
    ['Kitchen', 'error', 1],
    // The same message from another device is another event.
    ['Office', 'warning', 1],
    ['Kitchen', 'warning', 2],
  ]);
  // The newest of the repeats stands for them, so its time is the latest one.
  assert.match(latest[2].line, /12:00:02/);
  // The limit counts different events; later repeats of a listed one still count.
  assert.deepEqual(latestEvents(events, 1).map((event) => event.count), [1]);

  const text = templateText(eventList({ events: latest, onOpenLogs() {} }));
  assert.match(text, /Repeated 2 times/);
  assert.match(text, /haui-event-repeat/);
  // The timeline shows an exception's first line; Logs has the traceback.
  assert.doesNotMatch(text, /Traceback/);
  assert.match(text, /Logs/);
  assert.doesNotMatch(text, /View logs/);
});

test('empty Latest events shows a centered all-clear state and keeps Logs available', () => {
  const view = eventList({ events: [], onOpenLogs() {} });
  const text = templateText(view);
  assert.match(text, /mdi:check/);
  assert.match(text, /No events yet/);
  assert.match(text, /Logs/);
});

test('event parser maps hub log levels and preserves unstructured lines', () => {
  assert.deepEqual(parseEvent('[2026-01-01T12:00:00Z] ERROR Link lost'), {
    timestamp: '2026-01-01T12:00:00Z', level: 'error', message: 'Link lost',
  });
  assert.deepEqual(parseEvent('link resumed'), { timestamp: '', level: 'info', message: 'link resumed' });
  // A message that spans lines keeps its time and level.
  assert.deepEqual(parseEvent('[2026-01-01T12:00:00Z] ERROR Template failed\n  at line 3'), {
    timestamp: '2026-01-01T12:00:00Z', level: 'error', message: 'Template failed\n  at line 3',
  });
});

test('the 24-hour event window includes its boundary and ignores older, future, and undated logs', () => {
  const now = Date.parse('2026-11-14T12:00:00Z');
  const entry = (time, line = 'INFO event') => ({ line: `[${time}] ${line}` });
  const events = [
    entry('2026-11-13T12:00:00Z'),
    entry('2026-11-13T11:59:59.999Z'),
    entry('2026-11-14T12:00:00Z'),
    entry('2026-11-14T12:00:01Z'),
    { line: 'unstructured event' },
  ];

  assert.deepEqual(eventsInLast24Hours(events, now), [events[0], events[2]]);
});
