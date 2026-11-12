import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderFleetView, carouselEdgesFrom } from '../../custom_components/nspanel_haui/frontend/views/fleet.js';
import { eventList, latestEvents, parseEvent } from '../../custom_components/nspanel_haui/frontend/ui/event-list.js';

function templateText(template) {
  return `${template.strings.join(' ')} ${template.values.map((value) => {
    if (Array.isArray(value)) return value.map((entry) => entry?.strings ? templateText(entry) : String(entry ?? '')).join(' ');
    return value?.strings ? templateText(value) : String(value ?? '');
  }).join(' ')}`;
}

function nestedTemplate(template, predicate) {
  if (Array.isArray(template)) {
    return template.map((value) => nestedTemplate(value, predicate)).find(Boolean) ?? null;
  }
  if (!template?.strings) return null;
  if (predicate(template)) return template;
  return template.values.map((value) => nestedTemplate(value, predicate)).find(Boolean) ?? null;
}

/** Every template in `template` that renders a button. */
function buttons(template, found = []) {
  if (!template?.strings) return found;
  if (template.strings.join('').includes('<button')) found.push(template);
  for (const value of template.values.flat()) buttons(value, found);
  return found;
}

test('Fleet uses real device status and versions in the summary, inventory and events', () => {
  const view = renderFleetView({
    devices: [{
      name: 'kitchen',
      device: { friendlyName: 'Kitchen', config: { display_model: 'nspanel' }, panels: [] },
      status: {
        connected: true,
        haui_version: '0.5.0',
        current_page: 'light',
        device_info: { ip: '192.0.2.10', tft_version: '53.3.1' },
        update: { firmware_update_available: true },
        logs: [],
      },
      updates: true,
      onSelect() {},
    }],
    events: [{ deviceName: 'Kitchen', line: '[2026-01-01T12:00:00Z] WARNING Connection recovered' }],
    version: '0.5.0',
    onOpenDevice() {},
   
    onReorderDevices() {},
   
  });
  const text = templateText(view);
  assert.match(text, /Kitchen/);
  assert.match(text, /192\.0\.2\.10/);
  assert.match(text, /53\.3\.1/);
  assert.match(text, /0\.5\.0/);
  assert.match(text, /Connection recovered/);
  assert.match(text, /Update available/);
});

test('the summary strip reports health and one segment per device', () => {
  const deviceFor = (name, status) => ({
    name, device: { friendlyName: name, config: {}, panels: [] }, status, updates: false,
  });
  const base = { events: [], version: '0.5.0', onOpenDevice() {}, onReorderDevices() {} };
  const allOnlineView = renderFleetView({
    ...base,
    devices: [deviceFor('kitchen', { connected: true }), deviceFor('office', { connected: true })],
  });
  const allOnline = templateText(allOnlineView);
  assert.match(allOnline, /All devices connected/);
  assert.match(allOnline, /2 \/ 2/);
  assert.match(allOnline, /haui-fleet-band-success/);
  const inventory = nestedTemplate(allOnlineView, ({ strings }) => {
    const markup = strings.join('');
    return markup.includes('haui-device-inventory') && markup.includes('haui-device-table');
  });
  assert.ok(inventory);
  const markup = inventory.strings.join('');
  assert.ok(markup.indexOf('haui-inventory-heading') < markup.indexOf('haui-device-table'));
  assert.ok(markup.includes('haui-inventory-overview'));
  const summary = inventory.values.find((template) => template?.strings && templateText(template).includes('haui-fleet-summary'));
  const bar = inventory.values.find((template) => template?.strings?.join('').includes('haui-inventory-bar'));
  assert.ok(summary, 'the connection details are grouped with the inventory heading');
  assert.ok(bar, 'the connection bar remains a separate element below the overview');
  assert.doesNotMatch(templateText(summary), /haui-fleet-bar/);
  assert.ok(inventory.values.indexOf(summary) < inventory.values.indexOf(bar));
  // Every device segment carries its tone as the class value.
  assert.match(allOnline, /online/);

  const partial = templateText(renderFleetView({
    ...base,
    devices: [deviceFor('kitchen', { connected: true }), deviceFor('office', { connected: false })],
  }));
  assert.match(partial, /1 offline/);
  assert.match(partial, /haui-fleet-band-warning/);

  const none = templateText(renderFleetView({
    ...base,
    devices: [deviceFor('kitchen', null), deviceFor('office', { connected: false })],
  }));
  assert.match(none, /No device connected/);
  assert.match(none, /haui-fleet-band-danger/);
  // An unanswered status is not an offline device: its segment keeps the unknown tone.
  assert.match(none, /unknown/);
});

test('inventory title has no count chip and events read as a timeline', () => {
  const view = renderFleetView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen', config: {}, panels: [] }, status: { connected: true } }],
    events: [
      { deviceName: 'Kitchen', line: '[2026-01-01T12:00:00Z] WARNING Slow heartbeat' },
      { deviceName: 'Office', line: '[2026-01-01T12:01:00Z] INFO Started' },
    ],
    version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-section-heading/);
  const inventory = nestedTemplate(view, (template) => template.strings.join('').includes('haui-inventory-heading'));
  assert.ok(inventory);
  assert.doesNotMatch(templateText(inventory), /haui-section-count/);
  assert.match(text, /haui-section-count/);
  assert.match(text, /haui-event-node/);
  assert.match(text, /haui-event-meta/);
  assert.match(text, /haui-event-device/);
  // The warning colours its own dot; a plain line keeps the default tone.
  assert.match(text, /haui-event-warning/);
  assert.match(text, /haui-event-info/);
});

test('Fleet has a useful empty state when there are no devices or events', () => {
  const view = renderFleetView({
    devices: [], events: [], version: 'Unknown', onOpenDevice() {},
    onReorderDevices() {},
  });
  const text = templateText(view);
  assert.match(text, /No devices yet/);
  assert.doesNotMatch(text, /Scan for devices/);
});

test('Fleet scans for devices and offers the ones it found', () => {
  const calls = [];
  const view = renderFleetView({
    devices: [], events: [], version: 'Unknown', onOpenDevice() {}, onReorderDevices() {},
    discovered: [{ name: 'nspanel-office', friendly_name: 'Office' }, { name: 'nspanel-hall' }],
    onScan: () => calls.push('scan'),
    onAddDevices: (devices) => calls.push(devices.map((device) => device.name)),
  });
  const text = templateText(view);
  assert.match(text, /Scan for devices/);
  assert.match(text, /Discovered Devices/);
  assert.match(text, /Office/);
  assert.match(text, /nspanel-hall/);
  const press = (label) => buttons(view).filter((entry) => templateText(entry).includes(label))
    .at(-1).values.find((value) => typeof value === 'function')();
  press('Add All');
  press('Scan for devices');
  assert.deepEqual(calls, [['nspanel-office', 'nspanel-hall'], 'scan']);

  const scanning = templateText(renderFleetView({
    devices: [], events: [], version: 'Unknown', onOpenDevice() {}, onReorderDevices() {},
    scanning: true, scanError: 'Scan failed', onScan() {},
  }));
  assert.match(scanning, /Scanning/);
  assert.match(scanning, /Scan failed/);

  const stale = templateText(renderFleetView({
    devices: [], events: [], version: 'Unknown', onOpenDevice() {}, onReorderDevices() {},
    statusError: 'offline',
  }));
  assert.match(stale, /Device status could not be refreshed: offline/);
});

test('the carousel arrows follow the scroll extents and the summary waits for statuses', () => {
  const deviceFor = (name) => ({
    name,
    device: { friendlyName: name, config: {}, panels: [] },
    status: null,
    updates: false,
  });
  const base = {
    devices: [deviceFor('kitchen'), deviceFor('office')],
    events: [], version: '0.5.0',
    onOpenDevice() {}, onReorderDevices() {},
  };
  const atStart = templateText(renderFleetView({
    ...base, statusPending: true, carousel: { atStart: true, atEnd: false },
  }));
  assert.match(atStart, /haui-fleet-summary-pending/);
  const atEnd = templateText(renderFleetView({
    ...base, carousel: { atStart: false, atEnd: true },
  }));
  assert.match(atEnd, /haui-carousel-arrow is-left/);
  assert.match(atEnd, /haui-carousel-arrow is-right/);
});

test('the carousel edges follow scroll position', () => {
  assert.deepEqual(carouselEdgesFrom({ scrollWidth: 1000, clientWidth: 400, scrollLeft: 0 }), { atStart: true, atEnd: false });
  assert.deepEqual(carouselEdgesFrom({ scrollWidth: 1000, clientWidth: 400, scrollLeft: 600 }), { atStart: false, atEnd: true });
  assert.deepEqual(carouselEdgesFrom({ scrollWidth: 300, clientWidth: 400, scrollLeft: 0 }), { atStart: true, atEnd: true });
});

test('an open device menu renders its actions for that device', () => {
  const view = renderFleetView({
    devices: [{
      name: 'kitchen', device: { friendlyName: 'Kitchen', config: {}, panels: [] },
      status: { connected: true, logs: [] }, updates: false,
    }],
    events: [], version: '0.5.0',
    menu: {
      key: 'kitchen', anchorKey: 'device-menu:kitchen', label: 'Actions for kitchen',
      items: [
        { label: 'Open device', onSelect() {} },
        'divider',
        { label: 'View logs', onSelect() {} },
      ],
    },
    onMenu() {}, onOpenDevice() {}, onReorderDevices() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-device-menu/);
  assert.match(text, /\bmenuitem\b/);
  assert.match(text, /Open device/);
  assert.match(text, /device-menu:kitchen/);
});

test('Fleet lists the newest events of every device first', () => {
  const line = (minute, message) => `[2026-01-01T12:${String(minute).padStart(2, '0')}:00+01:00] INFO ${message}`;
  const view = renderFleetView({
    devices: [{
      name: 'kitchen', device: { friendlyName: 'Kitchen', config: {}, panels: [] },
      status: { connected: true, logs: [] }, updates: false,
    }],
    events: [
      ...Array.from({ length: 9 }, (_, index) => ({ deviceName: 'Kitchen', line: line(index, `kitchen ${index}`) })),
      { deviceName: 'Hall', line: line(30, 'hall newest') },
      { deviceName: 'Hall', line: 'no timestamp' },
    ],
    version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
  });
  const text = templateText(view);
  const shown = [...text.matchAll(/hall newest|kitchen \d|no timestamp/g)].map((match) => match[0]);
  assert.deepEqual(shown, [
    'hall newest', 'kitchen 8', 'kitchen 7', 'kitchen 6', 'kitchen 5', 'kitchen 4', 'kitchen 3', 'kitchen 2',
  ]);
});

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
  assert.match(text, /haui-event-empty/);
  assert.match(text, /haui-event-empty-icon/);
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

test('a device card shows only the connection and the name; the row keeps the actions', async () => {
  const { deviceCard } = await import('../../custom_components/nspanel_haui/frontend/ui/device-card.js');
  const card = templateText(deviceCard({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} },
    status: { connected: true, current_page: 'grid' }, disabled: true, onSelect() {},
  }));
  assert.match(card, /haui-status-dot-online/);
  assert.match(card, /Kitchen/);
  assert.match(card, /Disabled/);
  assert.doesNotMatch(card, /nspanel-kitchen/);
  assert.doesNotMatch(card, /grid/);
  assert.doesNotMatch(card, /Landscape/);
  assert.doesNotMatch(card, /Actions for/);
});

test('a device row shows the connection icon of the device card in front of the name', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const row = (status) => templateText(deviceRow({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status, onOpen() {},
  }));
  const online = row({ connected: true, device_info: { rssi: -50 } });
  assert.match(online, /haui-conn-status haui-conn-status-icon online/);
  assert.match(online, /Connected · -50 dBm/);
  assert.match(online, /wifi-strength-4/);
  assert.ok(online.indexOf('wifi-strength-4') < online.indexOf('Kitchen'));
  assert.match(row({ connected: false, device_info: { rssi: -50 } }), /wifi-off/);
  assert.match(row(null), /wifi-strength-off-outline/);
  assert.doesNotMatch(online, /haui-status-dot/);
});

test('the connection icon of a device row is coloured by the Wi-Fi strength', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const row = (status) => templateText(deviceRow({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status, onOpen() {},
  }));
  assert.match(row({ connected: true, device_info: { rssi: -50 } }), /wifi-excellent/);
  assert.match(row({ connected: true, device_info: { rssi: -65 } }), /wifi-fair/);
  assert.match(row({ connected: true, device_info: { rssi: -80 } }), /wifi-weak/);
  assert.doesNotMatch(row({ connected: false, device_info: { rssi: -80 } }), /wifi-weak/);
});
