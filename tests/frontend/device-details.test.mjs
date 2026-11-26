import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { renderDeviceView, previewControls } from '../../custom_components/nspanel_haui/frontend/views/device.js';
import { render } from './support/render.mjs';
import { deviceDetails } from '../../custom_components/nspanel_haui/frontend/ui/device-details.js';
import { panelActions } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
import { deviceActions } from '../../custom_components/nspanel_haui/frontend/ui/device-actions.js';
import { panelCatalog } from '../../custom_components/nspanel_haui/frontend/views/panel-catalog.js';
import { previewStage } from '../../custom_components/nspanel_haui/frontend/ui/preview-stage.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';
import '../../custom_components/nspanel_haui/frontend/app/shell.js';

test('the Diagnostics status opens a popover with the current findings', () => {
  const root = render(deviceDetails({
    name: 'kitchen',
    status: {
      connected: true,
      integration_version: '0.5.0',
      integration_version_mismatch: true,
      device_info: { rssi: -85 },
    },
    onLogs() {},
    onUpdates() {},
  }));
  const trigger = root.querySelector('.haui-diagnostics-card .haui-diag-status');
  const popover = root.querySelector('#haui-diag-status-card');
  assert.ok(trigger);
  assert.ok(popover);
  assert.equal(trigger.getAttribute('aria-expanded'), 'false');
  assert.match(trigger.getAttribute('aria-label'), /Diagnostics: 2 issues/);
  assert.match(popover.textContent, /Firmware version does not match the integration/);
  assert.match(popover.textContent, /Weak Wi-Fi signal/);

  trigger.click();
  assert.equal(trigger.getAttribute('aria-expanded'), 'true');
  trigger.dispatchEvent(new Event('blur'));
  assert.equal(trigger.getAttribute('aria-expanded'), 'false');
});

test('the device side areas close the other card when one opens', () => {
  const editor = Object.assign(document.createElement('nspanel-haui-editor'), {
    _detailsExpanded: true,
    _diagnosticsExpanded: false,
  });
  const root = document.createElement('div');
  const renderSideAreas = () => render(deviceDetails({
    name: 'kitchen',
    status: { connected: true, integration_version: '0.5.0', device_info: {} },
    onLogs() {},
    onUpdates() {},
    detailsExpanded: editor._detailsExpanded,
    onToggleDetails: () => editor._toggleDetails(),
    diagnosticsExpanded: editor._diagnosticsExpanded,
    onToggleDiagnostics: () => editor._toggleDiagnostics(),
  }), root);
  const expandedAreas = () => [...root.querySelectorAll('section.haui-surface')]
    .map((section) => section.querySelector('.haui-expand-toggle')?.getAttribute('aria-expanded') === 'true');

  renderSideAreas();
  assert.deepEqual(expandedAreas(), [true, false]);

  root.querySelector('.haui-diagnostics-card .haui-expand-toggle').click();
  renderSideAreas();
  assert.deepEqual(expandedAreas(), [false, true]);

  root.querySelector('.haui-device-details .haui-expand-toggle').click();
  renderSideAreas();
  assert.deepEqual(expandedAreas(), [true, false]);
});

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
  // Only the Connection card has collapsed content; Diagnostics keeps its status in the heading.
  assert.equal(templatesMatching(view, 'haui-surface-body').length, 1);
  assert.match(text, /Connection/);
  assert.doesNotMatch(text, /Connection & device/);
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

test('A collapsed Connection card shows only its heading', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, integration_version: '0.5.0', device_info: { ip: '192.0.2.11', yaml_version: '0.5.0' } },
    onLogs() {},
    onUpdates() {}, updatesDetail: 'Stable · Manual',
    onEditTheme() {}, themeDetail: 'Dark',
    detailsExpanded: false,
  });
  const root = render(view);
  const text = templateText(view);
  assert.match(text, /Show more/);
  assert.doesNotMatch(text, /Current page/);
  assert.doesNotMatch(text, /More details/);
  // Folding the card is about its facts: the two actions keep their own buttons below it.
  assert.equal(root.querySelector('.haui-device-details').contains(root.querySelector('.haui-details-actions')), false);
  assert.match(root.querySelector('.haui-details-actions button').textContent, /Themes/);
});

test('The side stack opens Themes, Logs, Updates and Backups below its cards', () => {
  const opened = [];
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, integration_version: '0.5.0', device_info: { tft_version: '0.4.5' } },
    onLogs: () => opened.push('logs'),
    onBackups: () => opened.push('backups'),
    onUpdates: () => opened.push('updates'), updatesDetail: 'Stable · Manual',
    onEditTheme: () => opened.push('theme'), themeDetail: 'Dark',
  });
  const root = render(view);
  const actions = root.querySelector('.haui-details-actions');
  const [themes, logs, updates, backups] = [...actions.querySelectorAll('button')];

  // Plain content at the end of the stack: no card or heading of its own, after the Connection and
  // Diagnostics cards.
  const sideStack = [...root.children];
  assert.equal(sideStack.at(-1), actions);
  assert.equal(sideStack[0].classList.contains('haui-device-details'), true);
  assert.equal(sideStack[1].classList.contains('haui-diagnostics-card'), true);
  assert.equal(sideStack.length, 3);

  // Themes and Updates follow, each naming what its sidebar holds on their trailing edge; Logs sits
  // between them, opening the log lines on this device; Backups closes the column, as the device's
  // own export and import.
  assert.match(themes.textContent, /Themes/);
  assert.match(themes.textContent, /Dark/);
  assert.match(logs.textContent, /Logs/);
  assert.match(updates.textContent, /Updates/);
  assert.match(updates.textContent, /Stable · Manual/);
  assert.match(backups.textContent, /Backups/);
  // The YAML buttons are not in the side stack any more: the Backups sidebar carries them.
  assert.equal(actions.querySelector('.haui-yaml-actions'), null);

  themes.click();
  logs.click();
  updates.click();
  backups.click();
  assert.deepEqual(opened, ['theme', 'logs', 'updates', 'backups']);
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

test('Device details say a failed status refresh and mark the facts as the last ones read', () => {
  const root = render(deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, device_info: { ip: '192.0.2.11' } },
    statusError: 'Connection lost',
    onSettings() {}, onUpdates() {}, onLogs() {},
  }));
  assert.match(root.querySelector('.haui-device-details [role="status"]').textContent,
    /could not be refreshed: Connection lost/);
  assert.equal(root.querySelector('.haui-diag-tiles').dataset.stale, 'true');
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
  // Collapsed, the card has no buttons: the report is in the expanded Integration details.
  assert.doesNotMatch(diagnosticsText, /Logs/);
  assert.doesNotMatch(diagnosticsText, /Copy report/);
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
  assert.match(expanded, /Integration log/);
  assert.match(expanded, /Integration details/);
  assert.match(expanded, /Copy report/);
  assert.match(expanded, /light\.kitchen/);
  // Timers are developer detail: the card counts them, the report lists them.
  assert.doesNotMatch(expanded, /tick/);
});
