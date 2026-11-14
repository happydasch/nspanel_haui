import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { renderDeviceView, previewControls } from '../../custom_components/nspanel_haui/frontend/views/device.js';
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

function previewModel(extra = {}) {
  return {
    mode: 'simulated', idle: false, showEntities: false,
    ready: true, canInteract: true, ...extra,
  };
}

function deviceView(preview, callbacks = {}) {
  return renderDeviceView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { connected: true } }],
    selectedName: 'kitchen', panelCount: 2, panelView: 'preview',
    workspace: html`<p>Stage</p>`, sideContent: html`<p>Details</p>`,
    preview,
    onSelectDevice() {}, onSwitchView() {},
    ...callbacks,
  });
}

/** First template that renders a control carrying `marker` and `label`. */
/** First template that renders a control carrying `marker` and `label`. */
function controlWith(view, marker, label) {
  return templatesMatching(view, marker).find((entry) => templateText(entry).includes(label));
}

const click = (control) => control.values.find((value) => typeof value === 'function')();

function controls(preview, callbacks = {}) {
  return previewControls({
    preview,
    onMode: () => {},
    onIdle: () => {},
    ...callbacks,
  });
}

test('Backup import and export are on the Preview side stack below Diagnostics', () => {
  const calls = [];
  const view = deviceDetails({
    name: 'kitchen', status: { connected: true, device_info: {} },
    detailsExpanded: false, diagnosticsExpanded: false, yamlExpanded: true,
    onLogs() {}, onYamlImport: () => calls.push('import'), onYamlExport: () => calls.push('export'),
    onToggleYaml() {},
  });
  const text = templateText(view);
  assert.ok(text.indexOf('Connection & device') < text.indexOf('Diagnostics'));
  assert.ok(text.indexOf('Diagnostics') < text.indexOf('Backup'));
  assert.match(text, /mdi:backup-restore/);
  assert.match(text, /haui-backup-status/);
  assert.equal(templatesMatching(view, 'haui-surface-body').length, 1);
  for (const label of ['Import', 'Export']) {
    click(templatesMatching(view, '<button').filter((entry) => templateText(entry).includes(label)).at(-1));
  }
  assert.deepEqual(calls, ['import', 'export']);
  assert.equal(templatesMatching(view, 'haui-yaml-actions').length, 1);
});

test('the device options are three buttons whose editors live in the sidebar', () => {
  const opened = [];
  const row = panelManager({
    panels: [{ key: 'lights', title: 'Lights' }], config: {
      theme_id: 'dark', schedule: [{ start: '22:00', end: '07:00' }],
      gestures: [{ swipes: ['swipe_left'], action: 'lights' }],
    },
    builtinThemes: { dark: { colors: { background: 0, header_background: 0, component_active: 0, entity_on: 0 } } },
    onOpen: (key) => opened.push(key),
  });
  const rowText = templateText(row);
  assert.match(rowText, /haui-device-option-controls/);
  assert.doesNotMatch(rowText, /panel-schedule_add|panel-gesture_add|haui-device-theme/);
  const buttons = templatesMatching(row, 'class=')
    .filter((entry) => entry.values.includes('haui-button haui-button-outline haui-device-option'));
  assert.equal(buttons.length, 3);
  for (const label of ['Theme', 'Schedule', 'Gestures']) {
    click(buttons.find((entry) => templateText(entry).includes(label)));
  }
  assert.deepEqual(opened, ['theme', 'schedule', 'gestures']);

  // Each editor is its own sidebar, and carries nothing of the other.
  const schedulePanel = templateText(deviceOptionPanel('schedule', { config: { schedule: [] } }));
  assert.match(schedulePanel, /panel-schedule_add/);
  assert.doesNotMatch(schedulePanel, /panel-gesture_add/);
  const gesturePanel = templateText(deviceOptionPanel('gestures', { config: { gestures: [] } }));
  assert.match(gesturePanel, /panel-gesture_add/);
  assert.doesNotMatch(gesturePanel, /panel-schedule_add/);
  // The theme has no editor panel here: its button opens the shared theme sidebar.
  assert.throws(() => deviceOptionPanel('theme', { config: {} }), /Unknown device option: theme/);
});

test('the Device lead card places management controls below its primary action', () => {
  const view = deviceActions({
    status: { update: {} }, onSettings() {}, onUpdates() {}, onAdd() {},
    management: html`<div class="haui-device-option-controls">Theme</div>`,
  });
  const text = templateText(view);
  assert.ok(text.indexOf('Add panel') < text.indexOf('haui-device-option-controls'));
  assert.match(text, /haui-device-option-controls/);
});

test('the Panels view keeps its blue lead card and the panel card in the side column', () => {
  const view = renderDeviceView({
    devices: [], selectedName: 'panel', panelCount: 1, panelView: 'panels',
    workspace: html`<p>Panels</p>`, leadContent: html`<p>Add panel</p>`,
    sideContent: html`<p>Selected panel</p>`, sideLabel: 'Panel details',
    onSelectDevice() {}, onSwitchView() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-device-layout/);
  assert.doesNotMatch(text, /is-panels/);
  // The lead card and the panel card share the side column, before the panel list.
  assert.match(text, /haui-device-side/);
  assert.match(text, /haui-device-lead/);
  assert.match(text, /haui-device-side-stack/);
  assert.match(text, /Panel details/);
  assert.ok(text.indexOf('Add panel') < text.indexOf('Selected panel'));
  assert.ok(text.indexOf('Selected panel') < text.indexOf('haui-device-workspace'));
  // A view that passes no panel card still shows the list on its own.
  const withoutSide = templateText(renderDeviceView({
    devices: [], selectedName: 'panel', panelCount: 1, panelView: 'panels',
    workspace: html`<p>Panels</p>`, leadContent: html`<p>Add panel</p>`,
    onSelectDevice() {}, onSwitchView() {},
  }));
  assert.match(withoutSide, /haui-device-side-stack/);
  assert.doesNotMatch(withoutSide, /Selected panel/);
});

test('the Panels lead card counts the panels, adds one and opens the settings, and never folds', () => {
  const added = [];
  const settings = [];
  const view = panelActions({
    panels: [{ key: 'light' }, { key: 'clock', show_in_navigation: false }],
    onAdd: () => added.push(true),
    onSettings: () => settings.push(true),
  });
  const text = templateText(view);
  assert.match(text, /haui-action-card/);
  assert.match(text, /haui-action-card-inner/);
  assert.match(text, /2 panels · 1 in navigation/);
  assert.doesNotMatch(text, /Edit a panel from the list/);
  assert.equal(templatesMatching(view, 'haui-expand-toggle').length, 0);
  click(controlWith(view, '<button', 'Add panel'));
  assert.deepEqual(added, [true]);
  click(controlWith(view, '<button', 'Settings'));
  assert.deepEqual(settings, [true]);
});

test('the Preview lead card leads with adding a panel, or with an offered update', () => {
  const calls = [];
  const callbacks = {
    onSettings: () => calls.push('settings'), onUpdates: () => calls.push('update'),
    onAdd: () => calls.push('add'),
  };
  const idle = deviceActions({ status: { connected: true, update: {} }, ...callbacks });
  assert.match(templateText(idle), /Manage this device/);
  const primary = (view) => templatesMatching(view, '<button')
    .find((entry) => entry.values.some((value) => String(value).includes('haui-button-primary')));
  assert.match(templateText(primary(idle)), /Add panel/);
  assert.match(templateText(idle), /haui-action-card-actions is-stacked/);
  assert.doesNotMatch(templateText(idle), /Theme/);
  // The settings are the cog beside the title; updates belong to the Connection & device card.
  assert.equal(templatesMatching(idle, 'haui-action-card-tool').length, 1);
  assert.doesNotMatch(templateText(idle), /Updates/);
  click(controlWith(idle, '<button', 'Settings'));
  click(controlWith(idle, '<button', 'Add panel'));
  assert.deepEqual(calls, ['settings', 'add']);

  const firmware = deviceActions({
    status: { update: { firmware_update_available: true, firmware_update_version: '0.6.0' } }, ...callbacks,
  });
  assert.match(templateText(firmware), /Update available/);
  assert.match(templateText(firmware), /Firmware 0\.6\.0 is ready to install\./);
  assert.match(templateText(primary(firmware)), /Install update/);
  assert.doesNotMatch(templateText(firmware), /Updates/);

  const display = templateText(deviceActions({ status: { update: { tft_update_available: true } }, ...callbacks }));
  assert.match(display, /A display update is ready to install\./);
});
