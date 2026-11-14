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
    installable: 1,
    onInstallUpdates() {},
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
  const orb = summary?.querySelector('.haui-fleet-orb');
  const heading = summary?.querySelector('#haui-inventory-heading');
  const lead = summary?.querySelector('.haui-fleet-lead');
  const headingRow = lead?.querySelector('.haui-fleet-lead-heading');
  const count = headingRow?.querySelector('strong');
  const health = lead?.lastElementChild;
  assert.ok(orb && heading && lead && headingRow && count && health);
  assert.ok(orb.compareDocumentPosition(lead) & Node.DOCUMENT_POSITION_FOLLOWING);
  assert.ok(lead.contains(heading));
  assert.ok(heading.compareDocumentPosition(count) & Node.DOCUMENT_POSITION_FOLLOWING);
  assert.equal(heading.closest('.haui-fleet-inventory-heading')?.parentElement, count.parentElement);
  assert.ok(lead.compareDocumentPosition(health) & Node.DOCUMENT_POSITION_FOLLOWING);
  assert.ok(summary?.querySelector('.haui-inventory-update'));
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
  assert.match(atEnd, /aria-label="Scroll devices left"/);
  assert.match(atEnd, /aria-label="Scroll devices right"/);
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


const ROLLOUT_DEVICES = [
  {
    name: 'kitchen',
    device: { friendlyName: 'Kitchen', config: {}, panels: [] },
    status: {
      connected: false, device_info: {}, logs: [],
      update: { firmware_progress: {
        phase: 'transferring', started_at: new Date().toISOString(),
        phase_started_at: new Date().toISOString(), expected_seconds: 180,
      } },
    },
    updates: true,
  },
  {
    name: 'office',
    device: { friendlyName: 'Office', config: {}, panels: [] },
    status: { connected: true, device_info: {}, update: {}, logs: [] },
    updates: true,
  },
];

function rolloutView(rollout, callbacks = {}) {
  return renderFleetView({
    devices: ROLLOUT_DEVICES, events: [], version: '0.5.0',
    onOpenDevice() {}, onReorderDevices() {}, rollout, ...callbacks,
  });
}

test('a running rollout lists every device with its step and can be cancelled', () => {
  const cancelled = [];
  const view = rolloutView({
    id: 1, state: 'running', devices: [
      { name: 'kitchen', kind: 'firmware', state: 'installing', error: null },
      { name: 'office', kind: 'tft', state: 'queued', error: null },
    ],
  }, { onCancelRollout: (device) => cancelled.push(device) });
  const root = render(view);
  const card = root.querySelector('.haui-rollout');

  assert.ok(card, 'the rollout card shows');
  assert.match(card.textContent, /Kitchen/);
  assert.match(card.textContent, /Installing/);
  assert.match(card.textContent, /Queued/);
  assert.ok(card.querySelector('[role="progressbar"]'), 'the installing device shows its progress');
  [...card.querySelectorAll('button')].find((button) => button.getAttribute('aria-label') === 'Cancel Office').click();
  [...card.querySelectorAll('button')].find((button) => /Cancel remaining/.test(button.textContent)).click();
  assert.deepEqual(cancelled, ['office', null]);
});

test('a stopped rollout names the failure and offers no cancel', () => {
  const root = render(rolloutView({
    id: 1, state: 'stopped', devices: [
      { name: 'kitchen', kind: 'firmware', state: 'failed', error: 'the panel did not reboot' },
      { name: 'office', kind: 'tft', state: 'not_started', error: null },
    ],
  }));
  const card = root.querySelector('.haui-rollout');

  assert.match(card.textContent, /the panel did not reboot/);
  assert.match(card.textContent, /Not started/);
  assert.equal([...card.querySelectorAll('button')].filter((button) => /Cancel/.test(button.textContent + (button.getAttribute('aria-label') || ''))).length, 0);
});

test('no rollout card without a rollout', () => {
  const root = render(rolloutView({ id: 0, state: 'idle', devices: [] }));

  assert.equal(root.querySelector('.haui-rollout'), null);
});
