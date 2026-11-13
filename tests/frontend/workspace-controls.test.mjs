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

test('the workspace header offers the preview mode and idle controls', () => {
  const calls = [];
  const header = renderDeviceView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { connected: true } }],
    selectedName: 'kitchen', panelCount: 2, panelView: 'preview',
    workspace: html`<p>Stage</p>`, sideContent: html`<p>Details</p>`,
    preview: previewModel(),
    onSelectDevice() {}, onSwitchView() {},
    onMode: (mode) => calls.push(['mode', mode]),
    onIdle: () => calls.push(['idle']),
  });
  const text = templateText(header);
  // One Live toggle instead of a Simulated/Live switch.
  assert.doesNotMatch(text, /Simulated/);
  assert.match(text, /Live/);
  assert.match(text, /Idle/);
  assert.match(text, /haui-preview-controls/);
  // The tools are the Diagnostics card's.
  assert.doesNotMatch(text, /Tools|Show entities|Reset sandbox/);

  const view = controls(previewModel(), {
    onMode: (mode) => calls.push(['mode', mode]),
    onIdle: () => calls.push(['idle']),
  });
  click(controlWith(view, 'aria-pressed=', 'Live'));
  templatesMatching(view, 'aria-label=')
    .find((entry) => templateText(entry).includes('Idle'))
    .values.filter((value) => typeof value === 'function').at(-1)();
  assert.deepEqual(calls, [['mode', 'live'], ['idle']]);
});

test('the expanded Diagnostics card has the mode-specific preview tools', () => {
  const calls = [];
  const card = (extra = {}, expanded = true) => deviceDetails({
    name: 'kitchen', status: { connected: true, device_info: {} }, onLogs() {},
    diagnosticsExpanded: expanded,
    previewTools: {
      live: false, ready: true, canInteract: true, sandboxChanged: true,
      onReset: () => calls.push(['reset']),
      onRedraw: () => calls.push(['redraw']),
      ...extra,
    },
  });
  const tools = (view) => templatesMatching(view, 'data-overlay-anchor=')
    .filter((entry) => /Reset sandbox|Reset interaction|Redraw display/.test(templateText(entry)));
  const disabled = (view) => tools(view).map((entry) => entry.values.find((value) => typeof value === 'boolean'));

  const simulated = card();
  assert.match(templateText(simulated), /haui-diag-tools/);
  assert.doesNotMatch(templateText(simulated), /Redraw display/);
  assert.deepEqual(disabled(simulated), [false]);
  tools(simulated).forEach(click);
  assert.deepEqual(calls, [['reset']]);
  // The sandbox reset waits for the preview to start.
  assert.deepEqual(disabled(card({ ready: false })), [true]);
  // Without a simulated state there is nothing to reset: no button, no empty group.
  assert.doesNotMatch(templateText(card({ sandboxChanged: false })), /haui-diag-tools|Reset sandbox/);

  calls.length = 0;
  const live = card({ live: true, sandboxChanged: false });
  assert.match(templateText(live), /Reset interaction[\s\S]*Redraw display/);
  tools(live).forEach(click);
  assert.deepEqual(calls, [['reset'], ['redraw']]);
  // Live actions wait for the connected panel.
  assert.deepEqual(disabled(card({ live: true, canInteract: false })), [true, true]);

  // Collapsed, the card shows its status line only.
  assert.doesNotMatch(templateText(card({}, false)), /haui-diag-tools/);
});

test('the Panels view hides the preview controls', () => {
  const view = renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 2, panelView: 'panels',
    workspace: html`<p>Groups</p>`, sideContent: html`<p>Manager</p>`,
    preview: previewModel(), onSelectDevice() {}, onSwitchView() {},
  });
  const text = templateText(view);
  assert.match(text, /Groups/);
  assert.doesNotMatch(text, /haui-preview-controls/);
});

test('the Panels option manager omits Home and Idle assignments', () => {
  const view = panelManager({
    panels: [{ key: 'light', title: 'Light' }, { key: 'clock', title: 'Clock' }],
    config: { home_panel: 'clock', idle_panel: '' },
  });
  const text = templateText(view);
  assert.match(text, /haui-device-option-controls/);
  assert.doesNotMatch(text, /haui-home-panel|haui-idle-panels|Home panel|Idle panels/);
});

test('the Live button toggles the mode and stays usable while the session is not ready', () => {
  const modes = [];
  const liveButton = (preview) => templatesMatching(controls(previewModel(preview), {
    onMode: (mode) => modes.push(mode),
  }), 'aria-pressed=').find((entry) => templateText(entry).includes('is-live'));
  const off = liveButton({ mode: 'simulated' });
  assert.ok(off.values.includes('false'));
  click(off);
  // A Live session that failed to start is never ready: the way back must stay open.
  const failed = liveButton({ mode: 'live', ready: false, canInteract: false });
  assert.ok(failed.values.includes('true'));
  assert.ok(!failed.values.includes(true), 'not disabled');
  click(failed);
  assert.deepEqual(modes, ['live', 'simulated']);
});
