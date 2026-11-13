import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';
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

test('Device workspace exposes its title, the way back, the panels view and the side stack', () => {
  const back = [];
  const switched = [];
  const view = renderDeviceView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { connected: true } }],
    selectedName: 'kitchen', title: 'Kitchen', onBack: () => back.push(true),
    panelCount: 4, panelView: 'panels',
    workspace: html`<p>Panel groups</p>`, sideContent: html`<p>Panel manager</p>`,
    onSelectDevice() {}, onSwitchView: (panelView) => switched.push(panelView),
  });
  const text = templateText(view);
  assert.match(text, /<h1>/);
  assert.match(text, /Kitchen/);
  assert.match(text, /haui-back-button/);
  const toggleIndex = view.values.findIndex(
    (entry) => entry?.strings?.[0].startsWith('<div class="haui-segmented"'),
  );
  const markupBeforeToggle = view.strings.slice(0, toggleIndex + 1).join('');
  assert.ok(
    markupBeforeToggle.lastIndexOf('haui-workspace-header')
      > markupBeforeToggle.lastIndexOf('haui-device-head'),
  );
  const toggleOptions = templatesMatching(view, 'aria-pressed=');
  assert.equal(toggleOptions.length, 2);
  const deviceOption = toggleOptions.find((option) => templateText(option).includes('Device'));
  const panelsOption = toggleOptions.find((option) => templateText(option).includes('Panels'));
  assert.match(templateText(deviceOption), /mdi:monitor/);
  assert.match(templateText(panelsOption), /mdi:view-dashboard-outline/);
  const root = render(view);
  const deviceButton = [...root.querySelectorAll('button[aria-pressed]')]
    .find((button) => button.textContent.includes('Device'));
  assert.ok(deviceButton);
  deviceButton.click();
  assert.deepEqual(switched, ['preview']);
  root.querySelector('button[aria-label="Show all devices"]').click();
  assert.deepEqual(back, [true]);
  // One device needs no rail to switch between devices.
  assert.doesNotMatch(text, /haui-device-rail/);
  assert.match(text, /Panel groups/);
  assert.match(text, /Panel manager/);
  assert.match(text, /Workspace view/);
  assert.match(text, /Device/);
  assert.match(text, /Panels/);
  assert.doesNotMatch(text, /Preview/);
});

test('the modal sidebar opens over the page and keeps the side stack in place', () => {
  const view = renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 1, panelView: 'panels',
    workspace: html`<p>Workspace</p>`, sideContent: html`<p>Side cards</p>`,
    sidebarContent: html`<section>Editor</section>`,
    sidebarOpen: true, onCloseSide() {}, onSelectDevice() {}, onSwitchView() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-sidebar-scrim/);
  assert.match(text, /Editor sidebar/);
  assert.match(text, /haui-sidebar-strip/);
  assert.match(text, /haui-sidebar-body/);
  assert.match(text, /Close sidebar/);
  // The side stack is not replaced by the sidebar: both are rendered.
  assert.match(text, /Side cards/);
  assert.match(text, /Editor/);
  const [sidebar] = templatesMatching(view, 'haui-modal-sidebar');
  assert.match(sidebar.strings.join(''), /role="dialog" aria-modal="true"/);

  const closed = templateText(renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 1, panelView: 'panels',
    workspace: html`<p>Workspace</p>`, sideContent: html`<p>Side cards</p>`,
    onSelectDevice() {}, onSwitchView() {},
  }));
  assert.match(closed, /Side cards/);
  assert.doesNotMatch(closed, /haui-modal-sidebar/);
});

test('the lead card heads the side column, which comes first in the layout', () => {
  const view = renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 1, panelView: 'preview',
    workspace: html`<p>Workspace</p>`, leadContent: html`<p>Lead card</p>`, sideContent: html`<p>Side cards</p>`,
    onSelectDevice() {}, onSwitchView() {},
  });
  const text = templateText(view);
  assert.match(text, /haui-device-lead/);
  assert.ok(text.indexOf('haui-device-side"') < text.indexOf('Lead card'));
  assert.ok(text.indexOf('Lead card') < text.indexOf('Side cards'));
  assert.ok(text.indexOf('Side cards') < text.indexOf('haui-device-workspace'));

  const withoutLead = templateText(renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 1, panelView: 'preview',
    workspace: html`<p>Workspace</p>`, sideContent: html`<p>Side cards</p>`,
    onSelectDevice() {}, onSwitchView() {},
  }));
  assert.doesNotMatch(withoutLead, /haui-device-lead/);
});

test('clicking a Device details section heading folds it, except on its controls', () => {
  const toggled = [];
  const device = deviceDetails({
    name: 'kitchen', status: { connected: true, device_info: {} },
    onLogs() {}, onToggleDetails: () => toggled.push('details'),
    yamlExpanded: false, onToggleYaml: () => toggled.push('yaml'),
    onYamlImport() {}, onYamlExport() {},
    onToggleDiagnostics: () => toggled.push('diagnostics'),
  });
  const headings = templatesMatching(device, 'haui-surface-heading-copy').filter((entry) =>
    entry.values.some((value) => typeof value === 'string' && value.includes('haui-surface-heading-toggle')));
  const handlers = headings.map((entry) => entry.values.find((value) => typeof value === 'function'));
  assert.equal(handlers.length, 3);
  // A click on the chevron or another heading control is that control's own.
  handlers.forEach((handler) => handler({ target: { closest: () => ({}) } }));
  assert.deepEqual(toggled, []);
  handlers.forEach((handler) => handler({ target: { closest: () => null } }));
  assert.deepEqual(toggled, ['details', 'diagnostics', 'yaml']);
});

test('the Panels view has a search field; the Device view does not', () => {
  const queries = [];
  const view = (panelView) => renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 2, panelView,
    workspace: html`<p>Rows</p>`, sideContent: html`<p>Side</p>`,
    panelSearch: { query: 'cl', onQuery: (value) => queries.push(value) },
    onSelectDevice() {}, onSwitchView() {},
  });
  const [search] = templatesMatching(view('panels'), 'haui-panel-search');
  assert.ok(search);
  search.values.find((value) => typeof value === 'function')({ currentTarget: { value: 'clock' } });
  assert.deepEqual(queries, ['clock']);
  assert.equal(templatesMatching(view('preview'), 'haui-panel-search').length, 0);
});

test('the expanded Connection & device card shows its facts as four tiles', () => {
  const view = deviceDetails({
    name: 'kitchen',
    status: {
      connected: false, current_page: 'grid', integration_version: '0.5.0',
      device_info: { ip: '192.0.2.11', rssi: -61, tft_version: '53.3.1', yaml_version: '0.5.0' },
    },
    onSettings() {}, onFirmware() {}, onLogs() {},
  });
  const [facts] = templatesMatching(view, 'data-stale=');
  assert.ok(facts);
  assert.equal(facts.values[1], 'true');
  assert.equal(facts.values[2].length, 4);
  const shown = facts.values[2].map(templateText).join(' ');
  // The connection readings lead: offline, the uptime tile reads Status: Offline.
  assert.match(shown, /Status[\s\S]*Offline[\s\S]*Wi-Fi[\s\S]*-61 dBm[\s\S]*Current page/);
  for (const label of ['Current page', 'IP address']) assert.match(shown, new RegExp(label));
  // A tile shows its label and value only; the other facts are in the card a hover or tap opens.
  assert.doesNotMatch(shown, /haui-diag-tile-detail/);
  for (const label of ['Last panel update', 'SSID', 'Wi-Fi signal']) assert.match(shown, new RegExp(label));
  // A status poll re-renders the tiles; the open state is not a binding it could reset.
  const [page] = templatesMatching(facts.values[2][2], 'aria-expanded="false"');
  assert.ok(page);
  const attributes = { 'aria-expanded': 'false' };
  const trigger = {
    getAttribute: (name) => attributes[name],
    setAttribute: (name, value) => { attributes[name] = value; },
    focus: () => { attributes.focused = 'true'; },
  };
  const [toggle] = page.values.filter((value) => typeof value === 'function');
  toggle({ currentTarget: trigger });
  assert.deepEqual(attributes, { 'aria-expanded': 'true', focused: 'true' });
  toggle({ currentTarget: trigger });
  assert.equal(attributes['aria-expanded'], 'false');
  // Nothing is folded away inside the card any more.
  assert.doesNotMatch(templateText(view), /More details/);
  // There is no connection banner: the state is an icon in the heading, whose card
  // carries the connection facts and the stale note.
  assert.doesNotMatch(templateText(view), /haui-connection-hero/);
  const [status] = templatesMatching(view, 'haui-conn-status-button');
  assert.equal(status.values[0], 'haui-conn-status offline');
  const card = templateText(status);
  for (const label of ['Disconnected', 'Wi-Fi signal', 'SSID', 'Last connected']) assert.match(card, new RegExp(label));
  assert.match(card, /-61 dBm/);
  assert.match(card, /haui-details-stale/);
  assert.match(card, /mdi:wifi-off/);
});

test('the connection icon shows the Wi-Fi strength while connected', () => {
  const view = deviceDetails({
    name: 'kitchen',
    status: { connected: true, device_info: { ip: '192.0.2.11', rssi: -50, ssid: 'HomeNet', connection_uptime: 660 } },
    onSettings() {}, onFirmware() {}, onLogs() {},
  });
  const [status] = templatesMatching(view, 'haui-conn-status-button');
  assert.equal(status.values[0], 'haui-conn-status online');
  const card = templateText(status);
  assert.match(card, /mdi:wifi-strength-4/);
  assert.match(card, /HomeNet/);
  assert.match(card, /Online for/);
  assert.doesNotMatch(card, /haui-details-stale/);
  // A status poll re-renders the card; the open state is not a binding it could reset.
  assert.match(status.strings.join(''), /aria-expanded="false"/);
});

test('the device rail renders chips and a dropdown, and the collapsed flag picks one', async () => {
  const { deviceRail, railOverflows } = await import('../../custom_components/nspanel_haui/frontend/ui/device-rail.js');
  const devices = [
    { name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { connected: true } },
    { name: 'hall', device: { friendlyName: 'Hallway' }, status: { connected: false } },
  ];
  const picked = [];
  const rail = (collapsed) => deviceRail({ devices, selected: 'hall', collapsed, onSelect: (name) => picked.push(name) });

  const open = rail(false);
  assert.ok(!open.values[0].includes('is-collapsed'));
  const collapsed = rail(true);
  assert.ok(collapsed.values[0].includes('is-collapsed'));
  const text = templateText(collapsed);
  assert.match(text, /haui-device-rail-item/);
  assert.match(text, /<select/);
  // The dropdown marks the routed device and reports a choice like a chip does.
  const options = templatesMatching(collapsed, '<option value=').filter((entry) => entry.strings[0].startsWith('<option'));
  assert.deepEqual(options.map((option) => [option.values[0], option.values[1]]), [['kitchen', false], ['hall', true]]);
  const change = collapsed.values.find((value) => typeof value === 'function');
  change({ currentTarget: { value: 'kitchen' } });
  assert.deepEqual(picked, ['kitchen']);

  // The shell collapses the rail when the chips need more width than they get.
  const root = (scrollWidth, clientWidth) => ({ querySelector: () => ({ scrollWidth, clientWidth }) });
  assert.equal(railOverflows(root(640, 420)), true);
  assert.equal(railOverflows(root(420, 420)), false);
  assert.equal(railOverflows({ querySelector: () => null }), null);
});
