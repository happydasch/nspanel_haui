import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

function templateText(template) {
  return render(template).innerHTML;
}

import { eventList, eventsInLast24Hours, latestEvents, parseEvent } from '../../custom_components/nspanel_haui/frontend/ui/event-list.js';

test('Latest events keeps warnings and errors only, lists a repeated message once with its count', () => {
  const missing = "Entity 'cover.hall' not available for state";
  const events = [
    { deviceName: 'Kitchen', line: `[2026-01-01T12:00:00Z] WARNING ${missing}` },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:01Z] DEBUG Heartbeat sent' },
    { deviceName: 'Kitchen', line: `[2026-01-01T12:00:02Z] WARNING ${missing}` },
    { deviceName: 'Office', line: `[2026-01-01T12:00:03Z] WARNING ${missing}` },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:04Z] ERROR Template failed\nTraceback (most recent call last)' },
    // Everything else is the Logs sidebar's: a Fleet timeline of problems only.
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:05Z] INFO Device is starting' },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:06Z] WARN Short form of warning' },
  ];
  const latest = latestEvents(events);
  assert.deepEqual(latest.map((event) => [event.deviceName, parseEvent(event.line).level, event.count]), [
    ['Kitchen', 'warn', 1],
    ['Kitchen', 'error', 1],
    // The same message from another device is another event.
    ['Office', 'warning', 1],
    ['Kitchen', 'warning', 2],
  ]);
  // The newest of the repeats stands for them, so its time is the latest one.
  assert.match(latest[3].line, /12:00:02/);
  // The limit counts different events; later repeats of a listed one still count.
  assert.deepEqual(latestEvents(events, 1).map((event) => event.count), [1]);

  const root = render(eventList({ events: latest, onOpenLogs() {} }));
  const text = root.innerHTML;
  const header = root.querySelector('.haui-event-list > header');
  assert.equal(header?.querySelector('h2')?.textContent, 'Latest events');
  assert.equal(header?.querySelector('p')?.textContent, 'Last 24 hours');
  assert.equal(header?.querySelector('.haui-badge-count')?.textContent, '4');
  assert.ok(header?.querySelector('button')?.textContent.includes('Logs'));
  assert.match(text, /Repeated 2 times/);
  assert.match(text, /haui-event-repeat/);
  // The timeline shows an exception's first line; Logs has the traceback.
  assert.doesNotMatch(text, /Traceback/);
  assert.doesNotMatch(text, /View logs/);
});

test('a screen reader hears each event\'s level and a machine-readable time', () => {
  const root = render(eventList({ events: [
    { deviceName: 'Kitchen', line: '[2026-01-01 12:00:00,123] ERROR Template failed' },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:02Z] WARNING Entity missing' },
    { deviceName: 'Kitchen', line: '[2026-01-01T12:00:03Z] INFO Connected' },
  ] }));
  const items = [...root.querySelectorAll('ol[role="list"] > li')];
  assert.deepEqual(items.map((item) => item.querySelector('p').textContent.trim()),
    ['Error: Template failed', 'Warning: Entity missing', 'Info: Connected']);
  for (const time of root.querySelectorAll('time')) {
    assert.ok(!Number.isNaN(Date.parse(time.getAttribute('datetime'))), time.getAttribute('datetime'));
  }
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
