import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

function templateText(template) {
  return render(template).innerHTML;
}

test('a device card is minimal; the inventory row keeps overflow actions without a settings shortcut', async () => {
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
    name: 'nspanel-kitchen', device: { friendlyName: 'Kitchen', config: {} }, status, onOpen() {}, onMenu() {},
  }));
  const online = row({ connected: true, device_info: { rssi: -50 } });
  assert.match(online, /haui-conn-status haui-conn-status-icon online/);
  assert.match(online, /Connected · -50 dBm/);
  assert.match(online, /wifi-strength-4/);
  assert.ok(online.indexOf('wifi-strength-4') < online.indexOf('Kitchen'));
  assert.match(row({ connected: false, device_info: { rssi: -50 } }), /wifi-off/);
  assert.match(row(null), /wifi-strength-off-outline/);
  assert.doesNotMatch(online, /haui-status-dot/);
  assert.match(online, /Actions for Kitchen/);
  assert.doesNotMatch(online, /Settings for Kitchen/);
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
  assert.match(mismatch, /haui-device-row-version has-mismatch/);
  assert.ok(mismatch.indexOf('0.5.0-dev62') < mismatch.indexOf('haui-device-row-mismatch'));
  assert.match(mismatch, /0\.5\.0-dev62/);
  assert.match(mismatch, /haui-badge-danger haui-device-row-mismatch/);
  assert.match(mismatch, /Mismatch/);
  assert.doesNotMatch(row(false), /haui-device-row-mismatch/);
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
