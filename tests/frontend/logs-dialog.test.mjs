import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

import { hexToRgb565 } from '../../custom_components/nspanel_haui/frontend/color-utils.js';
import { openThemeSidebar, saveTheme } from '../../custom_components/nspanel_haui/frontend/theme-editor.js';
import { filterLogEntries, logEntries, logText } from '../../custom_components/nspanel_haui/frontend/dialogs/logs.js';

const DIALOGS = [
  'nspanel-panel-editor',
  'nspanel-dialog-confirm',
  'nspanel-device-settings',
  'nspanel-firmware-popover',
  'nspanel-logs-sidebar',
  'nspanel-theme-sidebar',
];

/** A dialog instance without Lit's constructor (which needs a real DOM), recording its events. */
function dialog(tag, props = {}) {
  const dlg = document.createElement(tag);
  const events = [];
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass), requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

// Two days apart, so they fall on different calendar days in every time zone.
const LOG_LINES = [
  '[2026-11-09T12:00:00+00:00] INFO Device is starting',
  '[2026-11-11T12:00:00+00:00] WARN Slow render on grid',
  '[2026-11-11T12:00:05+00:00] ERROR Template failed\nTraceback (most recent call last)',
];

test('the logs sidebar parses the hub lines newest first and filters them by level and text', () => {
  const entries = logEntries([...LOG_LINES, { line: '[2026-11-11T12:00:06+00:00] DEBUG Heartbeat', deviceName: 'Hall' }]);
  assert.deepEqual(entries.map((entry) => entry.level), ['debug', 'error', 'warning', 'info']);
  assert.equal(entries[1].message, 'Template failed\nTraceback (most recent call last)');
  assert.ok(entries.every((entry) => entry.time instanceof Date));

  assert.deepEqual(filterLogEntries(entries, 'warning', '').map((entry) => entry.message), ['Slow render on grid']);
  assert.deepEqual(filterLogEntries(entries, 'all', ' TEMPLATE ').map((entry) => entry.level), ['error']);
  // The search also finds a device by its name.
  assert.deepEqual(filterLogEntries(entries, 'all', 'hall').map((entry) => entry.level), ['debug']);
  assert.deepEqual(filterLogEntries(entries, 'error', 'slow'), []);
});

test('logs copy oldest first with the full timestamp and the device in front of the message', () => {
  const entries = logEntries([
    { line: LOG_LINES[0], deviceName: 'Kitchen' },
    { line: LOG_LINES[1], deviceName: 'Hall' },
  ]);
  assert.equal(logText(entries), [
    '[2026-11-09T12:00:00+00:00] INFO Kitchen: Device is starting',
    '[2026-11-11T12:00:00+00:00] WARNING Hall: Slow render on grid',
  ].join('\n'));
});

test('the logs sidebar groups by day, tags problems, and hands Copy the visible entries', () => {
  const { dlg, events } = dialog('nspanel-logs-sidebar', { open: true, logs: LOG_LINES, _level: 'all', _query: '' });
  const markup = collectTemplateStrings(dlg.render()).join(' ');
  assert.equal(markup.split('<h3>').length - 1, 2);
  assert.match(markup, /haui-log-error/);
  assert.match(markup, /Slow render on grid/);
  assert.match(markup, /Search logs/);

  dlg._level = 'error';
  assert.doesNotMatch(collectTemplateStrings(dlg.render()).join(' '), /Slow render on grid/);
  dlg._copy(filterLogEntries(logEntries(LOG_LINES), 'error', ''));
  assert.deepEqual(events.map((event) => event.type), ['copy-logs']);
  assert.match(events[0].detail.text, /^\[2026-11-11T12:00:05\+00:00\] ERROR Template failed/);
});

test('the logs sidebar tells an empty log from a search that matches nothing', () => {
  const empty = dialog('nspanel-logs-sidebar', { open: true, logs: [], _level: 'all', _query: '' }).dlg;
  assert.match(collectTemplateStrings(empty.render()).join(' '), /No log entries yet\./);
  const unmatched = dialog('nspanel-logs-sidebar', { open: true, logs: LOG_LINES, _level: 'all', _query: 'zigbee' }).dlg;
  assert.match(collectTemplateStrings(unmatched.render()).join(' '), /No log entries match\./);
});

function collectTemplateStrings(value, result = []) {
  if (typeof value === 'string') result.push(value);
  else if (Array.isArray(value)) value.forEach((item) => collectTemplateStrings(item, result));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collectTemplateStrings(value.strings, result);
    if (Array.isArray(value.values)) collectTemplateStrings(value.values, result);
  }
  return result;
}
