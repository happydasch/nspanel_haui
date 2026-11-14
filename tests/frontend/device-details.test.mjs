import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { renderDeviceView, previewControls } from '../../custom_components/nspanel_haui/frontend/views/device.js';
import { render } from './support/render.mjs';
import { deviceDetails } from '../../custom_components/nspanel_haui/frontend/ui/device-details.js';
import { panelActions, panelManager, deviceOptionPanel } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
import { idlePanelConfig, idlePanelKeys } from '../../custom_components/nspanel_haui/frontend/ui/panel-pills.js';
import { deviceActions } from '../../custom_components/nspanel_haui/frontend/ui/device-actions.js';
import { panelCatalog } from '../../custom_components/nspanel_haui/frontend/views/panel-catalog.js';
import { previewStage } from '../../custom_components/nspanel_haui/frontend/ui/preview-stage.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';

function templateText(template) {
  return `${template?.strings?.join(' ') || ''} ${template?.values?.map((value) => {
    if (Array.isArray(value)) return value.map((entry) => entry?.strings ? templateText(entry) : String(entry ?? '')).join(' ');
    return value?.strings ? templateText(value) : String(value ?? '');
  }).join(' ') || ''}`;
}

function templatesMatching(template, marker, found = []) {
  if (!template?.strings) return found;
  if (template.strings.join('').includes(marker)) found.push(template);
  for (const value of template.values) {
    if (Array.isArray(value)) value.forEach((entry) => templatesMatching(entry, marker, found));
    else templatesMatching(value, marker, found);
  }
  return found;
}

/** The `placeholder=` value bound to the input with `id`. */
function placeholderFor(template, id) {
  if (!template?.strings) return undefined;
  const idBound = template.values.includes(id) || template.strings.some((part) => part.includes(`id="${id}"`));
  const index = template.strings.findIndex((part) => part.includes('placeholder='));
  if (idBound && index >= 0) return template.values[index];
  for (const value of template.values) {
    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      const found = placeholderFor(entry, id);
      if (found !== undefined) return found;
    }
  }
  return undefined;
}

function eventBinding(template, id, eventName) {  if (!template?.strings) return undefined;
  const idBound = template.values.includes(id) || template.strings.some((part) => part.includes(`id="${id}"`));
  const eventIndex = template.strings.findIndex((part) => part.trimEnd().endsWith(`${eventName}=`));
  if (idBound && eventIndex >= 0) return template.values[eventIndex];
  for (const value of template.values) {
    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      const found = eventBinding(entry, id, eventName);
      if (found !== undefined) return found;
    }
  }
  return undefined;
}

test('Device details only show facts reported by the device status', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: {
      connected: true, current_page: 'light', integration_version: '0.5.0',
      device_info: { ip: '192.0.2.11', tft_version: '53.3.1', rssi: -61, yaml_version: '0.5.0' },
    },
    onSettings() {}, onUpdates() {}, onLogs() {},
  });
  const text = templateText(view);
  // Only Connection & device has collapsed content; Diagnostics keeps its status in the heading.
  assert.equal(templatesMatching(view, 'haui-surface-body').length, 1);
  assert.match(text, /Connection & device/);
  assert.match(text, /Diagnostics/);
  assert.match(text, /Online/);
  assert.doesNotMatch(text, /YAML configuration/);
  assert.match(text, /192\.0\.2\.11/);
  assert.match(text, /-61 dBm/);
  // The firmware and display versions are in Diagnostics and the Updates sidebar, not in this card.
  assert.doesNotMatch(text, /53\.3\.1/);
  assert.doesNotMatch(text, /192\.168\./);
  assert.doesNotMatch(text, /haui-details-stale/);
});

test('The Current page tile opens the page in the simulated preview when it can', () => {
  const status = { connected: true, current_page: 'sleep (weather)', current_panel: 'sleep', device_info: {} };
  const opened = [];
  const view = deviceDetails({
    name: 'kitchen', status, onUpdates() {}, onLogs() {}, onOpenPage: () => opened.push('page'),
  });
  const [tile] = templatesMatching(view, 'aria-describedby')
    .filter((template) => template.values.includes('haui-tile-card-page'));
  assert.doesNotMatch(tile.strings.join(''), /aria-expanded/);
  tile.values.find((value) => typeof value === 'function')();
  assert.deepEqual(opened, ['page']);
  assert.match(templateText(view), /Click to show this page in the simulated preview/);

  // Live, or no panel to open: the tile only opens its card.
  const plain = deviceDetails({ name: 'kitchen', status, onUpdates() {}, onLogs() {} });
  const [plainTile] = templatesMatching(plain, 'aria-describedby')
    .filter((template) => template.values.includes('haui-tile-card-page'));
  assert.match(plainTile.strings.join(''), /aria-expanded/);
  assert.doesNotMatch(templateText(plain), /Click to show this page/);
});

test('A collapsed Connection & device card shows only its heading', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, integration_version: '0.5.0', device_info: { ip: '192.0.2.11', yaml_version: '0.5.0' } },
    onLogs() {},
    detailsExpanded: false,
  });
  const text = templateText(view);
  // Updates sits below the versions, so it folds away with them.
  assert.doesNotMatch(text, /haui-button-/);
  assert.match(text, /Show more/);
  assert.doesNotMatch(text, /Current page/);
  assert.doesNotMatch(text, /More details/);
});

test('The expanded Connection & device card opens the updates', () => {
  const opened = [];
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, integration_version: '0.5.0', device_info: { tft_version: '0.4.5' } },
    onLogs() {}, onUpdates: () => opened.push(true),
  });
  const root = render(view);
  const updates = [...root.querySelectorAll('button')].find((button) => button.textContent.includes('Updates'));
  assert.ok(updates);
  updates.click();
  assert.deepEqual(opened, [true]);
});

test('Device details mark reported values as stale while the device is offline', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: false, device_info: { ip: '192.0.2.11' } },
    onSettings() {}, onUpdates() {}, onLogs() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-details-stale/);
  assert.match(text, /Disconnected/);
});

test('An offline device says when it was last seen, never the raw connection state', () => {
  const since = new Date(Date.now() - 5 * 60_000).toISOString();
  const offline = templateText(deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: false, connection_state: 'disconnected', device_info: { disconnected_since: since } },
    onSettings() {}, onUpdates() {}, onLogs() {},
  }));
  assert.match(offline, /Last seen 5 minutes ago/);

  const unknown = templateText(deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: false, connection_state: 'disconnected', device_info: {} },
    onSettings() {}, onUpdates() {}, onLogs() {},
  }));
  assert.doesNotMatch(unknown, /Last seen/);
  assert.doesNotMatch(unknown, /Disconnected · disconnected/);
});

test('Device details carry the diagnostics sections and their actions', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: {
      connected: true,
      integration_version: '0.5.0',
      device_info: { ip: '192.0.2.11', ssid: 'HomeNet', rssi: -54, connection_uptime: 125 },
      active_listeners: [{ item_id: 'light.kitchen', attribute: 'state', callback_name: 'on_state' }],
      active_listener_count: 1,
      active_timers: [{ callback_name: 'tick', type: 'repeat', interval: 30 }],
      active_timer_count: 1,
    },
    onSettings() {}, onUpdates() {}, onLogs() {},
    onCopyReport() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-diagnostics-card/);
  assert.match(text, /All good/);
  const diagnosticsCard = templatesMatching(view, '<section class=')
    .find((entry) => templateText(entry).includes('haui-diagnostics-card'));
  assert.ok(diagnosticsCard);
  const diagnosticsText = templateText(diagnosticsCard);
  assert.match(diagnosticsText, /Online for 2m/);
  assert.doesNotMatch(diagnosticsText, /Wi-Fi|HomeNet|-54 dBm/);
  assert.equal(templatesMatching(diagnosticsCard, 'haui-surface-body').length, 0);
  // Collapsed, the card has no buttons: the report is in the expanded Hub details.
  assert.doesNotMatch(text, /Logs/);
  assert.doesNotMatch(text, /Copy report/);
  // Acting on the panel belongs to the live preview's tools.
  assert.doesNotMatch(text, /Reset interaction/);
  assert.doesNotMatch(text, /Redraw display/);

  const expanded = templateText(deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: {
      connected: true,
      integration_version: '0.5.0',
      device_info: { ip: '192.0.2.11', ssid: 'HomeNet', rssi: -54, connection_uptime: 125 },
      active_listeners: [{ item_id: 'light.kitchen', attribute: 'state', callback_name: 'on_state' }],
      active_listener_count: 1,
      active_timers: [{ callback_name: 'tick', type: 'repeat', interval: 30 }],
      active_timer_count: 1,
    },
    onSettings() {}, onUpdates() {}, onLogs() {},
    onCopyReport() {},
    diagnosticsExpanded: true,
  }));
  assert.match(expanded, /haui-diag-tiles/);
  assert.match(expanded, /HomeNet/);
  assert.match(expanded, /Hub log/);
  assert.match(expanded, /Hub details/);
  assert.match(expanded, /Copy report/);
  assert.match(expanded, /light\.kitchen/);
  // Timers are developer detail: the card counts them, the report lists them.
  assert.doesNotMatch(expanded, /tick/);
});
