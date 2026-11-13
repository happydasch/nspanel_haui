import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

import { renderFleetView, carouselEdgesFrom } from '../../custom_components/nspanel_haui/frontend/views/fleet.js';

function templateText(template) {
  return render(template).innerHTML;
}

function buttons(template) {
  return [...render(template).querySelectorAll('button')];
}

test('Fleet uses real device status and versions in the summary, inventory and events', () => {
  const view = renderFleetView({
    devices: [{
      name: 'kitchen',
      device: { friendlyName: 'Kitchen', config: { display_model: 'nspanel' }, panels: [] },
      status: {
        connected: true,
        integration_version: '0.5.0',
        current_page: 'light',
        device_info: { ip: '192.0.2.10', yaml_version: '0.5.0-dev62', tft_version: '53.3.1' },
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
  assert.match(text, /0\.5\.0-dev62/);
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
  const allOnline = render(allOnlineView);
  assert.match(allOnline.textContent, /All devices connected/);
  assert.match(allOnline.textContent, /2 \/ 2/);
  const inventory = allOnline.querySelector('.haui-device-inventory');
  assert.ok(inventory);
  const overview = inventory.querySelector('.haui-inventory-overview');
  const table = inventory.querySelector('.haui-device-table');
  const summary = inventory.querySelector('.haui-fleet-summary');
  const bar = inventory.querySelector('.haui-inventory-bar');
  assert.ok(overview && table && overview.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING);
  assert.ok(summary && overview.contains(summary));
  assert.ok(bar && table.compareDocumentPosition(bar) & Node.DOCUMENT_POSITION_PRECEDING);
  assert.match(summary.textContent, /All devices connected/);

  const partial = render(renderFleetView({
    ...base,
    devices: [deviceFor('kitchen', { connected: true }), deviceFor('office', { connected: false })],
  }));
  assert.match(partial.textContent, /1 offline/);

  const none = render(renderFleetView({
    ...base,
    devices: [deviceFor('kitchen', null), deviceFor('office', { connected: false })],
  }));
  assert.match(none.textContent, /No device connected/);
});

test('Fleet renders inventory and latest-event content', () => {
  const view = renderFleetView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen', config: {}, panels: [] }, status: { connected: true } }],
    events: [
      { deviceName: 'Kitchen', line: '[2026-01-01T12:00:00Z] WARNING Slow heartbeat' },
      { deviceName: 'Office', line: '[2026-01-01T12:01:00Z] INFO Started' },
    ],
    version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
  });
  const root = render(view);
  assert.ok(root.querySelector('.haui-device-inventory'));
  assert.ok(root.querySelector('.haui-event-list'));
  assert.match(root.textContent, /Slow heartbeat/);
  assert.match(root.textContent, /Started/);
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
  const press = (label) => buttons(view).filter((button) => button.textContent.includes(label))
    .at(-1).click();
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
