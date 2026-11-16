import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';
import { byRole } from './support/queries.mjs';

function templateText(template) {
  return render(template).innerHTML;
}

test('a device card is minimal; the inventory row keeps overflow actions without a settings shortcut', async () => {
  const { deviceCard } = await import('../../custom_components/nspanel_haui/frontend/ui/device-card.js');
  const card = templateText(deviceCard({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} },
    status: { connected: true, current_page: 'grid' }, disabled: true, onOpen() {},
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
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status, onOpen() {}, onMenu() {},
  }));
  const online = row({ connected: true, device_info: { rssi: -50 } });
  assert.match(online, /haui-conn-status haui-conn-status-icon online/);
  assert.match(online, /Connected · -50 dBm/);
  assert.match(online, /mdi:wifi-strength-4/);
  assert.ok(online.indexOf('mdi:wifi-strength-4') < online.indexOf('Kitchen'));
  // A panel the hub is not connected to still reports its Wi-Fi reading.
  assert.match(row({ connected: false, device_info: { rssi: -50 } }), /Disconnected · -50 dBm/);
  assert.match(row({ connected: false, device_info: { rssi: -50 } }), /mdi:wifi-strength-4/);
  assert.match(row({ connected: false, device_info: {} }), /mdi:wifi-off/);
  assert.match(row(null), /mdi:wifi-strength-off-outline/);
  assert.doesNotMatch(online, /haui-status-dot/);
  assert.match(online, /Actions for Kitchen/);
  assert.doesNotMatch(online, /Settings for Kitchen/);
});

test('the connection icon of a device row is coloured by the Wi-Fi strength', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const row = (status) => templateText(deviceRow({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status, onOpen() {},
  }));
  assert.match(row({ connected: true, device_info: { rssi: -50 } }), /haui-wifi-excellent/);
  assert.match(row({ connected: true, device_info: { rssi: -65 } }), /haui-wifi-fair/);
  assert.match(row({ connected: true, device_info: { rssi: -80 } }), /haui-wifi-weak/);
  assert.match(row({ connected: false, device_info: { rssi: -80 } }), /haui-wifi-weak/);
  assert.doesNotMatch(row({ connected: false, device_info: {} }), /haui-wifi-weak/);
});

test('the inventory marks a YAML and HAUI version mismatch', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const row = (integration_version_mismatch) => templateText(deviceRow({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} },
    status: {
      connected: true, integration_version_mismatch,
      integration_version: '0.4.7',
      device_info: { yaml_version: '0.5.0-dev62', tft_version: '0.4.5' },
    },
    onOpen() {},
  }));

  const mismatch = row(true);
  assert.ok(mismatch.indexOf('0.5.0-dev62') < mismatch.indexOf('Mismatch'));
  assert.match(mismatch, /0\.5\.0-dev62/);
  assert.match(mismatch, /title="Firmware version does not match the integration"/);
  assert.match(mismatch, /Mismatch/);
  assert.doesNotMatch(row(false), /Mismatch/);
});

test('the inventory firmware column shows the device firmware version, not the integration version', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const row = templateText(deviceRow({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} },
    status: {
      connected: true,
      integration_version: '0.4.7',
      device_info: { yaml_version: '0.5.0-dev62', tft_version: '0.4.5' },
    },
    onOpen() {},
  }));
  assert.match(row, /0\.5\.0-dev62/);
  assert.match(row, /0\.4\.5/);
  assert.doesNotMatch(row, /0\.4\.7/);
});

test('a click on an inventory row outside its controls, Enter or Space selects its device', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const selected = [];
  const opened = [];
  const root = render(deviceRow({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} },
    status: { connected: true, device_info: { ip: '192.0.2.10' } },
    onOpen: () => opened.push('kitchen'), onMenu() {}, onSelect: () => selected.push('kitchen'),
  }));
  const row = root.querySelector('[role="row"]');
  row.querySelector('.haui-device-row-ip').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  assert.deepEqual(selected, ['kitchen']);
  // The name opens the device and the menu button keeps its own click; neither selects.
  row.querySelector('.haui-device-row-name').click();
  row.querySelector('.haui-row-action').click();
  assert.deepEqual(selected, ['kitchen']);
  assert.deepEqual(opened, ['kitchen']);
  row.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  row.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
  row.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
  assert.deepEqual(selected, ['kitchen', 'kitchen', 'kitchen']);
  assert.equal(row.getAttribute('tabindex'), '0');
  assert.equal(row.hasAttribute('aria-current'), false);
});

test('a selected inventory row and device card are marked as current', async () => {
  const { deviceRow } = await import('../../custom_components/nspanel_haui/frontend/ui/device-row.js');
  const { deviceCard } = await import('../../custom_components/nspanel_haui/frontend/ui/device-card.js');
  const device = { friendlyName: 'Kitchen', config: {} };
  const row = render(deviceRow({ name: 'nspanel-kitchen', device, status: null, onOpen() {}, onSelect() {}, selected: true }))
    .querySelector('[role="row"]');
  assert.equal(row.getAttribute('aria-current'), 'true');
  const card = render(deviceCard({ name: 'nspanel-kitchen', device, status: null, onOpen() {}, onSelect() {}, selected: true }))
    .querySelector('article');
  assert.equal(card.getAttribute('aria-current'), 'true');
  const plainCard = render(deviceCard({ name: 'nspanel-kitchen', device, status: null, onOpen() {}, onSelect() {} }))
    .querySelector('article');
  assert.equal(plainCard.hasAttribute('aria-current'), false);
  const plainRow = render(deviceRow({ name: 'nspanel-kitchen', device, status: null, onOpen() {} }))
    .querySelector('[role="row"]');
  assert.equal(plainRow.hasAttribute('tabindex'), false);
});

test('the strip under a device card toggles its selection; the cover opens the device', async () => {
  const { deviceCard } = await import('../../custom_components/nspanel_haui/frontend/ui/device-card.js');
  const calls = [];
  const card = (selected) => render(deviceCard({
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status: { connected: true }, selected,
    onOpen: () => calls.push('open'), onSelect: () => calls.push('select'),
  }));
  const root = card(false);
  const strip = byRole(root, 'button', { name: 'Kitchen' });
  assert.equal(strip.getAttribute('aria-pressed'), 'false');
  strip.click();
  byRole(root, 'button', { name: 'Open device Kitchen' }).click();
  assert.deepEqual(calls, ['select', 'open']);
  assert.equal(byRole(card(true), 'button', { name: 'Kitchen' }).getAttribute('aria-pressed'), 'true');
  // Without a selection callback the strip is plain text and only the cover is a button.
  const plain = render(deviceCard({ name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status: null, onOpen() {} }));
  assert.deepEqual([...plain.querySelectorAll('button')].map((button) => button.getAttribute('aria-label')), ['Open device Kitchen']);
});
