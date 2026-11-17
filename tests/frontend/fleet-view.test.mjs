import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { flush, render } from './support/render.mjs';

import { renderFleetView, carouselEdgesFrom } from '../../custom_components/nspanel_haui/frontend/views/fleet.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import { makeHost } from './fake-host.mjs';

function templateText(template) {
  return render(template).innerHTML;
}

function buttons(template) {
  return [...render(template).querySelectorAll('button')];
}

function eventLine(level, message, ageMs = 0) {
  return `[${new Date(Date.now() - ageMs).toISOString()}] ${level} ${message}`;
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
    events: [{ deviceName: 'Kitchen', line: eventLine('WARNING', 'Connection recovered') }],
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

test('the summary strip reports health and the footer one segment per device', () => {
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
  // The segments close the card: always drawn, in the inventory's footer under the table.
  const footer = inventory.querySelector('.haui-inventory-footer');
  const bar = footer?.querySelector('.haui-fleet-bar');
  assert.ok(bar && table.compareDocumentPosition(footer) & Node.DOCUMENT_POSITION_FOLLOWING);
  assert.deepEqual([...bar.querySelectorAll('span')].map(({ className }) => className),
    ['is-online', 'is-online']);
  assert.equal(bar.getAttribute('aria-label'), '2 of 2 devices connected');
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
      { deviceName: 'Kitchen', line: eventLine('WARNING', 'Slow heartbeat') },
      { deviceName: 'Office', line: eventLine('ERROR', 'Template failed', 60_000) },
      { deviceName: 'Office', line: eventLine('INFO', 'Started', 120_000) },
    ],
    version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
  });
  const root = render(view);
  assert.ok(root.querySelector('.haui-device-inventory'));
  assert.ok(root.querySelector('.haui-event-list'));
  assert.match(root.textContent, /Slow heartbeat/);
  assert.match(root.textContent, /Template failed/);
  // The timeline shows the last day's problems only; the Logs sidebar has every line.
  assert.doesNotMatch(root.textContent, /Started/);
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

test('the carousel fades only the edges with cards beyond them', () => {
  const deviceFor = (name) => ({ name, device: { friendlyName: name, config: {}, panels: [] }, status: null, updates: false });
  const wrap = (carousel) => render(renderFleetView({
    devices: [deviceFor('kitchen'), deviceFor('office')], events: [], version: '0.5.0',
    onOpenDevice() {}, onReorderDevices() {}, carousel,
  })).querySelector('.haui-fleet-carousel-wrap').classList;
  assert.deepEqual([...wrap({ atStart: true, atEnd: true })], ['haui-fleet-carousel-wrap']);
  assert.ok(wrap({ atStart: true, atEnd: false }).contains('is-clipped-end'));
  assert.ok(!wrap({ atStart: true, atEnd: false }).contains('is-clipped-start'));
  const middle = wrap({ atStart: false, atEnd: false });
  assert.ok(middle.contains('is-clipped-start') && middle.contains('is-clipped-end'));
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

test('an inventory row selects its device on Fleet and brings its card into view', () => {
  const deviceFor = (name) => ({
    name, device: { friendlyName: name, config: {}, panels: [] }, status: { connected: true, logs: [] }, updates: false,
  });
  const chosen = [];
  const view = (selectedDevice) => renderFleetView({
    devices: [deviceFor('kitchen'), deviceFor('office')],
    events: [], version: '0.5.0', selectedDevice,
    onSelectDevice: (name) => chosen.push(name), onOpenDevice() {}, onReorderDevices() {},
  });
  const root = render(view(null));
  const carousel = root.querySelector('.haui-fleet-carousel');
  const scrolled = [];
  carousel.scrollBy = (options) => scrolled.push(options.left);
  carousel.getBoundingClientRect = () => ({ left: 0, right: 400, width: 400 });
  const officeCard = [...root.querySelectorAll('.haui-device-card')].find((card) => card.textContent.includes('office'));
  officeCard.getBoundingClientRect = () => ({ left: 600, right: 900, width: 300 });
  const officeRow = [...root.querySelectorAll('.haui-device-row[tabindex]')].find((row) => row.textContent.includes('office'));
  officeRow.querySelector('.haui-device-row-ip').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  assert.deepEqual(chosen, ['office']);
  assert.equal(scrolled.length, 1);
  assert.ok(scrolled[0] > 0);

  render(view('office'), root);
  const current = [...root.querySelectorAll('[aria-current="true"]')];
  assert.equal(current.length, 2);
  assert.ok(current.every((node) => node.textContent.includes('office')));
  // Selecting the selected device again clears it without moving the carousel.
  officeRow.querySelector('.haui-device-row-ip').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  assert.deepEqual(chosen, ['office', 'office']);
  assert.equal(scrolled.length, 1);
  // The strip under a card selects the same device.
  officeCard.querySelector('.haui-device-card-info').click();
  assert.deepEqual(chosen, ['office', 'office', 'office']);
});

test('Fleet comes back with the selected device centred in the carousel', () => {
  const editor = makeHost({
    device_order: ['kitchen', 'hall', 'office'],
    devices: {
      kitchen: { config: {}, panels: [] }, hall: { config: {}, panels: [] }, office: { config: {}, panels: [] },
    },
  }, () => { throw new Error('unexpected request'); });
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  const deviceFor = (name) => ({
    name, device: { friendlyName: name, config: {}, panels: [] }, status: { connected: true, logs: [] }, updates: false,
  });
  const row = render(renderFleetView({
    devices: ['kitchen', 'hall', 'office'].map(deviceFor),
    events: [], version: '0.5.0', selectedDevice: 'office',
    onOpenDevice() {}, onReorderDevices() {},
  }));
  const carousel = row.querySelector('.haui-fleet-carousel');
  const scrolled = [];
  carousel.scrollBy = (options) => scrolled.push(options);
  carousel.getBoundingClientRect = () => ({ left: 0, right: 480, width: 480 });
  [...row.querySelectorAll('.haui-device-card')].forEach((card, index) => {
    card.getBoundingClientRect = () => ({ left: index * 320, right: index * 320 + 320, width: 320 });
  });
  editor.renderRoot = row;

  // Nothing is selected: the row stays at its first card.
  editor._watchCarousel();
  assert.deepEqual(scrolled, []);

  // The device screen is shown instead: Fleet's row is gone.
  editor.renderRoot = { querySelector: () => null };
  editor._watchCarousel();
  assert.deepEqual(scrolled, []);

  // Back on Fleet the selection is kept, and its card comes back to the middle in one jump.
  editor.renderRoot = row;
  editor._fleetSelection = 'office';
  editor._watchCarousel();
  assert.deepEqual(scrolled, [{ left: 640 + 160 - 240, behavior: 'auto' }]);

  // A row that stays on screen is measured, never scrolled again.
  editor._watchCarousel();
  assert.equal(scrolled.length, 1);
});

test('a selected device scopes Fleet\'s latest events to itself and names it under the title', () => {
  const deviceFor = (name, label) => ({
    name, device: { friendlyName: label, config: {}, panels: [] }, status: { connected: true, logs: [] },
    updates: false,
  });
  const base = {
    devices: [deviceFor('kitchen', 'Kitchen'), deviceFor('office', 'Office')],
    events: [
      { device: 'kitchen', deviceName: 'Kitchen', line: eventLine('WARNING', 'kitchen says hello') },
      { device: 'kitchen', deviceName: 'Kitchen', line: eventLine('INFO', 'kitchen started') },
      { device: 'office', deviceName: 'Office', line: eventLine('ERROR', 'office says hello') },
    ],
    version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
  };
  const timeline = (data) => render(renderFleetView(data)).querySelector('.haui-event-list').textContent;

  const all = timeline(base);
  assert.match(all, /kitchen says hello/);
  assert.match(all, /office says hello/);
  // Info lines are the Logs sidebar's; the timeline carries the problems of the last day.
  assert.doesNotMatch(all, /kitchen started/);

  const scoped = timeline({ ...base, selectedDevice: 'office' });
  assert.match(scoped, /office says hello/);
  assert.doesNotMatch(scoped, /kitchen says hello/);

  const scopedRoot = render(renderFleetView({ ...base, selectedDevice: 'office' }));
  assert.equal(scopedRoot.querySelector('.haui-event-list > header h2').textContent, 'Latest events');
  // The device opens the header's second line, where a long name truncates instead of wrapping.
  assert.equal(scopedRoot.querySelector('.haui-event-list > header .haui-event-scope').textContent, 'Office');
  assert.equal(scopedRoot.querySelector('.haui-event-list > header p').textContent, 'Last 24 hours');
  const everyoneRoot = render(renderFleetView(base));
  assert.equal(everyoneRoot.querySelector('.haui-event-list > header .haui-event-scope'), null);
  assert.equal(everyoneRoot.querySelector('.haui-event-list > header p').textContent, 'Last 24 hours');

  // The device, not its label, decides: two devices named alike never share lines.
  const mislabelled = timeline({
    ...base,
    selectedDevice: 'office',
    events: base.events.map((event) => ({ ...event, deviceName: 'Office' })),
  });
  assert.match(mislabelled, /office says hello/);
  assert.doesNotMatch(mislabelled, /kitchen says hello/);
});

test('Logs opens on the device Fleet selected, and on every device without one', async () => {
  const editor = makeHost({
    device_order: ['kitchen', 'office'],
    devices: { kitchen: { config: {}, panels: [] }, office: { config: {}, panels: [] } },
  }, (method, path) => { throw new Error(`unexpected request ${method} ${path}`); });
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor.renderRoot = { querySelector: () => null, activeElement: null };
  editor._fleetSelection = null;
  const now = new Date().toISOString();
  editor.api.status.getAll = async () => ({
    kitchen: { connected: true, logs: [`[${now}] INFO kitchen says hello`, `[${now}] ERROR kitchen failed`] },
    office: { connected: true, logs: [`[${now}] WARNING office says hello`] },
  });
  editor.api.updates.rollout = async () => null;
  editor.store.actions.startAllStatusPolling();
  await flush(3);

  try {
    const fleet = () => render(editor._renderFleetScreen());
    const timeline = (root) => root.querySelector('.haui-event-list').textContent;
    const overlays = () => editor.store.getState().ui.overlays.map(({ kind, subject }) => [kind, subject]);

    const everyone = fleet();
    assert.match(timeline(everyone), /kitchen failed/);
    assert.match(timeline(everyone), /office says hello/);
    // Fleet lists the problems; the info line is only in the sidebar's full log.
    assert.doesNotMatch(timeline(everyone), /kitchen says hello/);
    everyone.querySelector('.haui-event-list .haui-event-logs').click();
    assert.deepEqual(overlays(), [['logs', null]]);
    editor.store.actions.closeOverlay('logs', 'logs');

    editor._fleetSelection = 'office';
    const selected = fleet();
    assert.match(timeline(selected), /office says hello/);
    assert.doesNotMatch(timeline(selected), /kitchen failed/);
    selected.querySelector('.haui-event-list .haui-event-logs').click();
    assert.deepEqual(overlays(), [['logs', 'office']]);
  } finally {
    // The poller's interval would keep the test process alive.
    editor.store.actions.stopAllStatusPolling();
  }
});

test('Fleet lists the newest events of every device first', () => {
  const start = Date.now() - 60 * 60 * 1000;
  const line = (minute, message) => `[${new Date(start + minute * 60_000).toISOString()}] WARNING ${message}`;
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
    'kitchen 1', 'kitchen 0',
  ]);
});

test('Fleet shows all distinct problems from the last 24 hours and omits info, older or undated logs', () => {
  const events = Array.from({ length: 12 }, (_, index) => ({
    deviceName: 'Kitchen',
    line: eventLine(index % 2 ? 'WARNING' : 'ERROR', `event ${index}`, index * 60_000),
  }));
  events.push(
    { deviceName: 'Kitchen', line: eventLine('INFO', 'just started', 5_000) },
    { deviceName: 'Kitchen', line: eventLine('DEBUG', 'heartbeat', 6_000) },
    { deviceName: 'Kitchen', line: eventLine('ERROR', 'older than a day', 24 * 60 * 60 * 1000 + 1) },
    { deviceName: 'Kitchen', line: eventLine('ERROR', 'future event', -60_000) },
    { deviceName: 'Kitchen', line: 'undated event' },
  );
  const root = render(renderFleetView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen', config: {}, panels: [] }, status: { connected: true } }],
    events, version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
  }));
  const list = root.querySelector('.haui-event-list ol');

  assert.ok(list);
  assert.equal(list.getAttribute('tabindex'), '0');
  assert.equal(list.querySelectorAll(':scope > li').length, 12);
  assert.match(root.querySelector('.haui-event-list').textContent, /Last 24 hours/);
  assert.match(list.textContent, /event 0/);
  assert.doesNotMatch(list.textContent, /older than a day|future event|undated event/);
  // Info and debug lines are inside the window but belong to the Logs sidebar.
  assert.doesNotMatch(list.textContent, /just started|heartbeat/);
});

test('a reset starts Fleet\'s latest events at its own moment instead of the last 24 hours', () => {
  const now = Date.now();
  const entry = (level, message, ageMs) => ({
    deviceName: 'Kitchen', line: eventLine(level, message, ageMs),
  });
  const root = render(renderFleetView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen', config: {}, panels: [] }, status: { connected: true } }],
    events: [
      entry('ERROR', 'before the reset', 60_000),
      entry('WARNING', 'after the reset', 0),
      { deviceName: 'Kitchen', line: eventLine('WARNING', 'after the reset', 0) },
    ],
    version: '0.5.0', onOpenDevice() {}, onReorderDevices() {},
    eventsSince: now - 30_000, onResetEvents() {}, onShowAllEvents() {},
  }));
  const card = root.querySelector('.haui-event-list');
  assert.match(card.textContent, /Since /);
  assert.match(card.textContent, /after the reset/);
  assert.doesNotMatch(card.textContent, /before the reset/);
  // The repeats are still counted from the reset on.
  assert.match(card.textContent, /×2/);
});

test('Reset on Fleet starts the latest events at the moment it was pressed, and 24 hours bring them back', async () => {
  const editor = makeHost({
    device_order: ['kitchen'],
    devices: { kitchen: { config: {}, panels: [] } },
  }, (method, path) => { throw new Error(`unexpected request ${method} ${path}`); });
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor.renderRoot = { querySelector: () => null, activeElement: null };
  editor._fleetSelection = null;
  editor._fleetEventsSince = null;
  const logged = new Date(Date.now() - 60_000).toISOString();
  editor.api.status.getAll = async () => ({
    kitchen: { connected: true, logs: [`[${logged}] ERROR kitchen failed`] },
  });
  editor.api.updates.rollout = async () => null;
  editor.store.actions.startAllStatusPolling();
  await flush(3);

  try {
    const fleet = () => render(editor._renderFleetScreen());
    const timeline = (root) => root.querySelector('.haui-event-list').textContent;

    const before = fleet();
    assert.match(timeline(before), /kitchen failed/);
    assert.match(timeline(before), /Last 24 hours/);

    before.querySelector('.haui-event-list .haui-event-reset').click();
    assert.ok(Number.isFinite(editor._fleetEventsSince));
    const after = fleet();
    // The line was written before the reset, so it is no longer in the window.
    assert.doesNotMatch(timeline(after), /kitchen failed/);
    assert.match(timeline(after), /No events since the reset/);

    after.querySelector('.haui-event-list .haui-event-window').click();
    assert.equal(editor._fleetEventsSince, null);
    assert.match(timeline(fleet()), /kitchen failed/);
  } finally {
    // The poller's interval would keep the test process alive.
    editor.store.actions.stopAllStatusPolling();
  }
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

test('a stopped rollout names the failure, offers no cancel and is dismissed', () => {
  let dismissed = 0;
  const root = render(rolloutView({
    id: 1, state: 'stopped', devices: [
      { name: 'kitchen', kind: 'firmware', state: 'failed', error: 'the panel did not reboot' },
      { name: 'office', kind: 'tft', state: 'not_started', error: null },
    ],
  }, { onDismissRollout: () => { dismissed += 1; } }));
  const card = root.querySelector('.haui-rollout');

  assert.match(card.textContent, /the panel did not reboot/);
  assert.match(card.textContent, /Not started/);
  assert.equal([...card.querySelectorAll('button')].filter((button) => /Cancel/.test(button.textContent + (button.getAttribute('aria-label') || ''))).length, 0);
  [...card.querySelectorAll('button')].find((button) => /Dismiss/.test(button.textContent)).click();
  assert.equal(dismissed, 1);
});

test('the inventory table is named by its heading and every column has a name', () => {
  const root = render(rolloutView(null, { onSelectDevice() {} }));
  // The screen's own heading leads the h2 sections, as the device screen's h1 does there.
  assert.equal(root.querySelectorAll('h1').length, 1);
  const table = root.querySelector('[role="table"]');
  assert.equal(table.getAttribute('aria-labelledby'), 'haui-inventory-heading');
  assert.match(root.querySelector(`#${table.getAttribute('aria-describedby')}`).textContent, /Enter or Space/);
  const heads = [...table.querySelectorAll('[role="columnheader"]')].map((head) => head.textContent.trim());
  assert.ok(heads.every(Boolean), `unnamed column: ${heads}`);
  assert.equal(root.querySelector('.haui-fleet-carousel').getAttribute('role'), 'list');
  assert.ok([...root.querySelectorAll('.haui-device-card')].every((card) => card.getAttribute('role') === 'listitem'
    && card.getAttribute('aria-label')));
});

test('a failed status refresh and a rollout\'s state are announced politely', () => {
  const root = render(rolloutView({
    id: 1, state: 'done', devices: [{ name: 'kitchen', kind: 'firmware', state: 'done', error: null }],
  }, { statusError: 'Connection lost' }));
  assert.equal(root.querySelector('.haui-rollout-summary').getAttribute('role'), 'status');
  const refresh = [...root.querySelectorAll('[role="status"]')].find((node) => /could not be refreshed/.test(node.textContent));
  assert.ok(refresh, 'the failed refresh is a polite status, not an alert');
});

test('no rollout card without a rollout', () => {
  const root = render(rolloutView({ id: 0, state: 'idle', devices: [] }));

  assert.equal(root.querySelector('.haui-rollout'), null);
});
