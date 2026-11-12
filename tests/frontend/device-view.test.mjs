import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { renderDeviceView, previewControls } from '../../custom_components/nspanel_haui/frontend/views/device.js';
import { deviceDetails } from '../../custom_components/nspanel_haui/frontend/ui/device-details.js';
import { panelActions, panelManager } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
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

test('panel catalog filters real panel descriptors and transitions with the chosen type', () => {
  const selected = [];
  const catalog = panelCatalog({
    panelTypes: [
      { type_key: 'clock', label: 'Clock', description: 'Large clock face', icon: 'mdi:clock', category: { key: 'backgrounds', label: 'Backgrounds', icon: 'mdi:wallpaper' } },
      { type_key: 'cover', label: 'Cover', description: 'Control a cover', icon: 'mdi:window-shutter', category: { key: 'entities', label: 'Entities', icon: 'mdi:lightbulb-on-outline' } },
    ],
    query: 'cover', onQuery() {}, onSelect: (type) => selected.push(type),
  });
  const text = templateText(catalog);
  assert.match(text, /Cover/);
  assert.doesNotMatch(text, /Clock/);
  const option = templatesMatching(catalog, 'haui-panel-catalog-option')[0];
  const click = option.values.find((value) => typeof value === 'function');
  click();
  assert.deepEqual(selected, ['cover']);
});

test('panel catalog previews a new panel of each type, with the same panel object on every render', () => {
  const asked = [];
  const options = {
    panelTypes: [
      { type_key: 'grid', label: 'Grid', icon: 'mdi:grid', category: { key: 'grouping', label: 'Grouping', icon: 'mdi:view-grid-plus-outline' } },
      { type_key: 'clock', label: 'Clock', category: { key: 'backgrounds', label: 'Backgrounds', icon: 'mdi:wallpaper' } },
    ],
    onQuery() {}, onSelect() {},
    preview: (panel) => { asked.push(panel); return `render:${panel.type}`; },
    portrait: true,
  };
  const text = templateText(panelCatalog(options));
  assert.match(text, /haui-panel-catalog-preview portrait/);
  assert.match(text, /render:grid/);
  assert.match(text, /render:clock/);
  // The preview takes the place of the type icon.
  assert.doesNotMatch(text, /mdi:grid/);
  assert.deepEqual(asked, [{ type: 'grid', key: '' }, { type: 'clock', key: '' }]);
  panelCatalog(options);
  assert.equal(asked[2], asked[0]);

  assert.doesNotMatch(templateText(panelCatalog({ ...options, preview: null })), /haui-panel-catalog-preview/);
});

test('panel catalog exposes an empty state when search finds no descriptor', () => {
  const catalog = panelCatalog({ panelTypes: [], query: 'missing', onQuery() {}, onSelect() {} });
  assert.match(templateText(catalog), /No panel types match this search/);
});

test('the panel catalog puts grouping first and opens it by default', () => {
  const category = (key, label, icon) => ({ key, label, icon });
  const panelTypes = [
    { type_key: 'clock', label: 'Clock', category: category('backgrounds', 'Backgrounds', 'mdi:wallpaper') },
    { type_key: 'weather', label: 'Weather', category: category('backgrounds', 'Backgrounds', 'mdi:wallpaper') },
    { type_key: 'light', label: 'Light', category: category('entities', 'Entities', 'mdi:lightbulb-on-outline') },
    { type_key: 'grid', label: 'Grid', category: category('grouping', 'Grouping', 'mdi:view-grid-plus-outline') },
    { type_key: 'timer', label: 'Timer', category: category('tools', 'Tools', 'mdi:tools') },
  ];
  const options = { panelTypes, onQuery() {}, onSelect() {} };
  const sections = (query) => templatesMatching(panelCatalog({ ...options, query }), 'haui-panel-catalog-section')
    .filter((entry) => entry.strings[0].startsWith('<details class="haui-panel-catalog-section"'));
  const catalog = sections('');
  // Grouping leads the category sections and starts open; other categories follow the hub's order.
  assert.deepEqual(catalog.map((entry) => [entry.values[0], entry.values[1]]), [
    ['grouping', true], ['backgrounds', false], ['entities', false], ['tools', false],
  ]);
  assert.deepEqual(catalog.map((entry) => templateText(entry).match(/mdi:[a-z-]+ \w+/)[0]), [
    'mdi:view-grid-plus-outline Grouping', 'mdi:wallpaper Backgrounds',
    'mdi:lightbulb-on-outline Entities', 'mdi:tools Tools',
  ]);
  assert.match(templateText(catalog[1]), /Backgrounds 2[\s\S]*Clock[\s\S]*Weather/);
  assert.doesNotMatch(templateText(catalog[1]), /Light/);
  // The heading row is the toggle: the category icon, the name, the count, then
  // the same chevron the cards end with (turned down while the section is open).
  assert.deepEqual(catalog[0].values.slice(0, 5), [
    'grouping', true, 'mdi:view-grid-plus-outline', 'Grouping', 1,
  ]);
  assert.match(catalog[0].strings.join(''), /haui-panel-catalog-chevron" icon="mdi:chevron-right"/);
  // A search opens what it looks into; the search also finds a type by its category name.
  assert.ok(sections('grouping').every((entry) => entry.values[1] === true));
  const found = panelCatalog({ ...options, query: 'grouping' });
  assert.match(templateText(found), /Grid/);
  assert.doesNotMatch(templateText(found), /Clock/);
});

test('the popup overrides and the copies are collapsible sections too, below the categories', () => {
  const source = { type: 'grid', key: 'grid_0', title: 'Lights' };
  const options = {
    panelTypes: [{ type_key: 'clock', label: 'Clock', category: { key: 'backgrounds', label: 'Backgrounds', icon: 'mdi:wallpaper' } }],
    onQuery() {}, onSelect() {}, onSelectPopup() {}, onSelectTemplate() {},
    popups: [{ key: 'popup_cover', type: 'popup_cover', label: 'Cover', editable: true }],
    templates: [{ id: 'kitchen:grid_0', device: 'kitchen', deviceLabel: 'Kitchen', label: 'Lights', detail: 'Grid', panel: source }],
  };
  const catalog = panelCatalog(options);
  const sections = templatesMatching(catalog, 'haui-panel-catalog-section')
    .filter((entry) => entry.strings[0].startsWith('<details class="haui-panel-catalog-section"'));
  assert.deepEqual(sections.map((entry) => entry.values[0]), ['backgrounds', 'popups', 'copies']);
  assert.deepEqual(sections.map((entry) => entry.values[1]), [false, false, false]);
  assert.match(templateText(sections[1]), /Extend a popup 1[\s\S]*popup_cover/);
  assert.match(templateText(sections[2]), /Copy an existing panel 1[\s\S]*Kitchen[\s\S]*Lights/);
  // The device groups stay collapsed inside their section until a search looks into them.
  const [device] = templatesMatching(sections[2], 'haui-panel-catalog-group')
    .filter((entry) => entry.strings[0].startsWith('<details class="haui-panel-catalog-group"'));
  assert.equal(device.values[0], 'kitchen');
  assert.equal(device.values[1], false);
  const searched = panelCatalog({ ...options, query: 'lights' });
  assert.ok(templatesMatching(searched, 'haui-panel-catalog-section')
    .filter((entry) => entry.strings[0].startsWith('<details class="haui-panel-catalog-section"'))
    .every((entry) => entry.values[1] === true));
});

test('Device workspace exposes its title, the way back, the panels view and the side stack', () => {
  const back = [];
  const view = renderDeviceView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { connected: true } }],
    selectedName: 'kitchen', title: 'Kitchen', onBack: () => back.push(true),
    panelCount: 4, panelView: 'panels',
    workspace: html`<p>Panel groups</p>`, sideContent: html`<p>Panel manager</p>`,
    onSelectDevice() {}, onSwitchView() {},
  });
  const text = templateText(view);
  assert.match(text, /<h1>/);
  assert.match(text, /Kitchen/);
  assert.match(text, /haui-back-button/);
  click(templatesMatching(view, 'aria-label=')
    .filter((entry) => templateText(entry).includes('Show all devices')).at(-1));
  assert.deepEqual(back, [true]);
  // One device needs no rail to switch between devices.
  assert.doesNotMatch(text, /haui-device-rail/);
  assert.match(text, /Panel groups/);
  assert.match(text, /Panel manager/);
  assert.match(text, /Workspace view/);
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
    devices: [], selectedName: 'kitchen', panelCount: 1, panelView: 'panels',
    workspace: html`<p>Workspace</p>`, leadContent: html`<p>Lead card</p>`, sideContent: html`<p>Side cards</p>`,
    onSelectDevice() {}, onSwitchView() {},
  });
  const [layout] = templatesMatching(view, 'haui-device-layout');
  const text = templateText(layout);
  assert.match(text, /haui-device-lead/);
  assert.ok(text.indexOf('haui-device-side"') < text.indexOf('Lead card'));
  assert.ok(text.indexOf('Lead card') < text.indexOf('Side cards'));
  assert.ok(text.indexOf('Side cards') < text.indexOf('haui-device-workspace'));

  const withoutLead = templateText(renderDeviceView({
    devices: [], selectedName: 'kitchen', panelCount: 1, panelView: 'panels',
    workspace: html`<p>Workspace</p>`, sideContent: html`<p>Side cards</p>`,
    onSelectDevice() {}, onSwitchView() {},
  }));
  assert.doesNotMatch(withoutLead, /haui-device-lead/);
});

test('Device details only show facts reported by the device status', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: {
      connected: true, current_page: 'light', haui_version: '0.5.0',
      device_info: { ip: '192.0.2.11', tft_version: '53.3.1', rssi: -61, yaml_version: '0.5.0' },
    },
    onSettings() {}, onFirmware() {}, onLogs() {},
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
  assert.doesNotMatch(text, /YAML version/);
  assert.doesNotMatch(text, /192\.168\./);
  assert.doesNotMatch(text, /haui-details-stale/);
});

test('The Current page tile opens the page in the simulated preview when it can', () => {
  const status = { connected: true, current_page: 'sleep (weather)', current_panel: 'sleep', device_info: {} };
  const opened = [];
  const view = deviceDetails({
    name: 'kitchen', status, onFirmware() {}, onLogs() {}, onOpenPage: () => opened.push('page'),
  });
  const [tile] = templatesMatching(view, 'aria-describedby')
    .filter((template) => template.values.includes('haui-tile-card-page'));
  assert.doesNotMatch(tile.strings.join(''), /aria-expanded/);
  tile.values.find((value) => typeof value === 'function')();
  assert.deepEqual(opened, ['page']);
  assert.match(templateText(view), /Click to show this page in the simulated preview/);

  // Live, or no panel to open: the tile only opens its card.
  const plain = deviceDetails({ name: 'kitchen', status, onFirmware() {}, onLogs() {} });
  const [plainTile] = templatesMatching(plain, 'aria-describedby')
    .filter((template) => template.values.includes('haui-tile-card-page'));
  assert.match(plainTile.strings.join(''), /aria-expanded/);
  assert.doesNotMatch(templateText(plain), /Click to show this page/);
});

test('A collapsed Connection & device card shows only its heading', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, haui_version: '0.5.0', device_info: { ip: '192.0.2.11', yaml_version: '0.5.0' } },
    onLogs() {},
    detailsExpanded: false,
  });
  const text = templateText(view);
  // Updates sits below the versions, so it folds away with them.
  assert.doesNotMatch(text, /haui-button-/);
  assert.match(text, /Show more/);
  assert.doesNotMatch(text, /Current page/);
  assert.doesNotMatch(text, /YAML version/);
  assert.doesNotMatch(text, /More details/);
});

test('The expanded Connection & device card opens the updates', () => {
  const opened = [];
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: true, haui_version: '0.5.0', device_info: { tft_version: '0.4.5' } },
    onLogs() {}, onFirmware: () => opened.push(true),
  });
  click(controlWith(view, '<button', 'Updates'));
  assert.deepEqual(opened, [true]);
});

test('Device details mark reported values as stale while the device is offline', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: false, device_info: { ip: '192.0.2.11' } },
    onSettings() {}, onFirmware() {}, onLogs() {},
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
    onSettings() {}, onFirmware() {}, onLogs() {},
  }));
  assert.match(offline, /Last seen 5 minutes ago/);

  const unknown = templateText(deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: { connected: false, connection_state: 'disconnected', device_info: {} },
    onSettings() {}, onFirmware() {}, onLogs() {},
  }));
  assert.doesNotMatch(unknown, /Last seen/);
  assert.doesNotMatch(unknown, /Disconnected · disconnected/);
});

test('Device details carry the diagnostics sections and their actions', () => {
  const view = deviceDetails({
    name: 'kitchen', device: { friendlyName: 'Kitchen' },
    status: {
      connected: true,
      haui_version: '0.5.0',
      device_info: { ip: '192.0.2.11', ssid: 'HomeNet', rssi: -54, connection_uptime: 125 },
      active_listeners: [{ item_id: 'light.kitchen', attribute: 'state', callback_name: 'on_state' }],
      active_listener_count: 1,
      active_timers: [{ callback_name: 'tick', type: 'repeat', interval: 30 }],
      active_timer_count: 1,
    },
    onSettings() {}, onFirmware() {}, onLogs() {},
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
      haui_version: '0.5.0',
      device_info: { ip: '192.0.2.11', ssid: 'HomeNet', rssi: -54, connection_uptime: 125 },
      active_listeners: [{ item_id: 'light.kitchen', attribute: 'state', callback_name: 'on_state' }],
      active_listener_count: 1,
      active_timers: [{ callback_name: 'tick', type: 'repeat', interval: 30 }],
      active_timer_count: 1,
    },
    onSettings() {}, onFirmware() {}, onLogs() {},
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

test('Panel manager routes home and idle changes through their configuration keys', () => {
  const calls = [];
  const view = panelManager({
    panels: [
      { key: 'light', type: 'light', show_in_navigation: true },
      { key: 'kitchen', type: 'grid', show_in_navigation: true },
    ],
    config: { home_panel: 'light', idle_panel: '' }, saving: false,
    onSetRole: (field, value) => calls.push([field, value]), expanded: ['roles'],
  });
  const text = templateText(view);
  assert.equal(templatesMatching(view, 'haui-surface-body').length, 1);
  assert.match(text, /Home & idle panels/);
  assert.match(text, /Choose what opens when you go home/);
  assert.doesNotMatch(text, /YAML configuration/);
  const roleHeadings = templatesMatching(view, 'haui-role-heading').map(templateText);
  assert.ok(roleHeadings.some((heading) => heading.includes('Home panel')));
  assert.ok(roleHeadings.some((heading) => heading.includes('Idle panels')));
  assert.equal(templatesMatching(view, 'haui-role-content').length, 2);
  assert.match(text, /Home panel/);
  assert.match(text, /Idle panels/);
  assert.match(text, /Nothing opens automatically until you add a panel/);

  const selects = templatesMatching(view, '<select')
    .filter((select) => select.values.includes('haui-home-panel') || select.values.includes('haui-idle-panels'));
  assert.equal(selects.length, 2);
  const homeSelect = selects.find((select) => select.values.includes('haui-home-panel'));
  assert.match(templateText(homeSelect), /Set panel/);
  const idleSelect = selects.find((select) => select.values.includes('haui-idle-panels'));
  homeSelect.values.find((value) => typeof value === 'function')({ currentTarget: { value: 'kitchen' } });
  idleSelect.values.find((value) => typeof value === 'function')({ currentTarget: { value: 'kitchen' } });
  assert.deepEqual(calls, [['home_panel', 'kitchen'], ['idle_panels', 'kitchen']]);
});

test('Panel manager keeps the ordered idle list, including stale keys, and saves additions/removals', () => {
  const calls = [];
  const panels = [
    { key: 'clock', title: 'Clock' }, { key: 'weather', title: 'Weather' },
    { key: 'photo', title: 'Photo' }, { key: 'light', title: 'Light' },
  ];
  const view = panelManager({
    panels,
    config: { home_panel: 'light', idle_panel: 'clock', idle_panel_extra: 'weather, gone, clock' },
    onSetRole: (field, value) => calls.push([field, value]), expanded: ['roles'],
  });
  const field = templatesMatching(view, 'haui-role-extra')[0];
  assert.equal(templatesMatching(field, 'haui-role-hint').length, 0);
  const countBadge = templatesMatching(field, 'haui-role-icon-count')[0];
  assert.ok(countBadge, 'the idle count is attached to its icon');
  assert.equal(countBadge.values.at(-1), 3);
  assert.doesNotMatch(templateText(field), /haui-badge/);
  const items = templatesMatching(field, 'class="haui-pill"');
  assert.deepEqual(items.map((item) => templateText(item).match(/\d+ (?:Clock|Weather|gone)/)?.[0]), [
    '1 Clock', '2 Weather', '3 gone',
  ]);

  const add = templatesMatching(field, '<select')[0];
  const offered = templatesMatching(add, '<option value=')
    .filter((option) => option !== add).map((option) => option.values[0]);
  assert.deepEqual(offered, ['photo', 'light'], 'the idle and listed panels are not offered again');
  const target = { value: 'photo' };
  add.values.find((value) => typeof value === 'function')({ currentTarget: target });
  assert.equal(target.value, '', 'the select returns to its placeholder');

  const removeFirst = items[0];
  const removeIndex = removeFirst.strings.findIndex((part) => part.trimEnd().endsWith('@click='));
  removeFirst.values[removeIndex]();
  assert.deepEqual(calls, [
    ['idle_panels', 'clock, weather, gone, photo'],
    ['idle_panels', 'weather, gone'],
  ]);
});

test('idle panels can be reordered by dragging their accessible sort handle', () => {
  const calls = [];
  const view = panelManager({
    panels: [
      { key: 'clock', title: 'Clock' },
      { key: 'weather', title: 'Weather' },
      { key: 'photo', title: 'Photo' },
    ],
    config: { home_panel: 'clock', idle_panel: 'clock', idle_panel_extra: 'weather, photo' },
    onSetRole: (field, value) => calls.push([field, value]), expanded: ['roles'],
  });
  const idle = templatesMatching(view, 'haui-role-extra')[0];
  const pills = templatesMatching(idle, 'class="haui-pill"');
  const handle = templatesMatching(pills[1], 'draggable="true"')[0];
  assert.match(templateText(handle), /Drag to reorder Weather/);
  const startIndex = handle.strings.findIndex((part) => part.trimEnd().endsWith('@dragstart='));
  const startDrag = handle.values[startIndex];
  const sourceRow = { classList: { add() {}, remove() {} } };
  startDrag({
    currentTarget: { closest: () => sourceRow },
    dataTransfer: { setData() {}, setDragImage() {}, effectAllowed: '' },
  });
  const dropIndex = pills[0].strings.findIndex((part) => part.trimEnd().endsWith('@drop='));
  const drop = pills[0].values[dropIndex];
  const targetRow = {
    classList: { remove() {} },
    getBoundingClientRect: () => ({ top: 0, height: 20 }),
  };
  drop({ currentTarget: targetRow, clientY: 1, preventDefault() {} });
  assert.deepEqual(calls, [['idle_panels', 'weather, clock, photo']]);
});

const GESTURE_PANELS = [{ key: 'lights', title: 'Lights' }];
const GESTURE_SYSTEM_PANELS = [
  { key: 'sys_about', label: 'About' },
  { key: 'sys_settings', label: 'Settings' },
  { key: 'popup_notify', label: 'Notification', editable: true },
];
const SEQUENCE = { swipes: ['swipe_left', 'swipe_right'], action: 'lights', timeframe: 3 };

test('the collapsed Gestures card sums up what each gesture does, like the schedule', () => {
  const view = panelManager({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    config: { ...DEVICE_CONFIG_DEFAULTS, gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE] },
    onSetRole() {},
  });
  const text = templateText(view);
  assert.match(text, /Swipe left: Next panel · Swipe right: Previous panel · Swipe up: About · Swipe down: Settings · Swipe left → Swipe right: Lights/);
  assert.match(text, /5 entries/);
  assert.doesNotMatch(text, /panel-gesture_add/);

  const empty = templateText(panelManager({
    panels: [], config: { ...DEVICE_CONFIG_DEFAULTS, gestures: [] }, onSetRole() {},
  }));
  assert.match(empty, /No gestures: swipes do nothing\./);
  assert.doesNotMatch(empty, /0 entries/);
});

test('the Gestures card lists every gesture as a folded entry below the add button', () => {
  const view = panelManager({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    config: { ...DEVICE_CONFIG_DEFAULTS, gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE] },
    onSetRole() {}, expanded: ['gestures'],
  });
  const text = templateText(view);
  assert.ok(text.indexOf('Home & idle panels') < text.indexOf('Schedule'));
  assert.ok(text.indexOf('Schedule') < text.indexOf('Gestures'));
  assert.ok(text.indexOf('Add gesture') < text.indexOf('class="haui-entry"'));
  // A single swipe and a sequence are the same kind of entry.
  const entries = templatesMatching(view, 'class="haui-entry"');
  assert.equal(entries.length, 5);
  assert.deepEqual(entries.map((entry) => entry.values[0]), [false, false, false, false, false]);
  assert.match(templateText(entries[0]), /Entry 1/);
  assert.ok(entries[0].values.includes('Swipe left'));
  assert.ok(entries[0].values.includes('Next panel'));
  assert.match(templateText(entries[4]), /Entry 5/);
  assert.ok(entries[4].values.includes('Swipe left → Swipe right'));
  assert.ok(entries[4].values.includes('Lights'));
  assert.ok(entries.every((entry) => templateText(entry).includes('Remove gesture')));
  // Every gesture offers the same actions; a popup needs its caller's context, so none is offered.
  assert.match(templateText(entries[0]), /Previous panel/);
  assert.match(templateText(entries[0]), /Lights \(lights\)/);
  assert.match(templateText(entries[0]), /About \(sys_about\)/);
  assert.doesNotMatch(text, /popup_notify/);
  // Only a sequence has a time limit.
  assert.doesNotMatch(templateText(entries[0]), /panel-gesture_0_timeframe/);
  assert.match(templateText(entries[4]), /panel-gesture_4_timeframe/);
  const save = templatesMatching(view, 'haui-gesture-actions')[0];
  assert.match(templateText(save), /Save/);
});

test('gesture edits go to a draft that keeps every other gesture', () => {
  const drafts = [];
  const view = panelManager({
    panels: GESTURE_PANELS, systemPanels: GESTURE_SYSTEM_PANELS,
    config: { ...DEVICE_CONFIG_DEFAULTS, locale: 'de_DE', gestures: [...DEVICE_CONFIG_DEFAULTS.gestures, SEQUENCE] },
    onSetRole() {}, onGestureChange: (draft) => drafts.push(draft), expanded: ['gestures'],
  });

  eventBinding(view, 'panel-gesture_2_action', '@change')({ target: { value: 'lights' } });
  assert.deepEqual(drafts.at(-1).gestures, [
    ...DEVICE_CONFIG_DEFAULTS.gestures.slice(0, 2),
    { swipes: ['swipe_up'], action: 'lights', timeframe: 3 },
    DEVICE_CONFIG_DEFAULTS.gestures[3],
    SEQUENCE,
  ]);
  assert.equal('locale' in drafts.at(-1), false);

  eventBinding(view, 'panel-gesture_4_timeframe', '@input')({ target: { value: '90' } });
  assert.equal(drafts.at(-1).gestures[4].timeframe, 60);
  const before = drafts.length;
  eventBinding(view, 'panel-gesture_4_timeframe', '@input')({ target: { value: '' } });
  assert.equal(drafts.length, before, 'an emptied box is unfinished typing, not a time limit');

  eventBinding(view, 'panel-gesture_add', '@click')();
  assert.deepEqual(drafts.at(-1).gestures.at(-1), { swipes: [], action: '', timeframe: 3 });
  assert.equal(drafts.at(-1).gestures.length, 6);
  assert.equal(drafts.at(-1).expandedEntryIndex, 5);
});

test('a gesture\'s swipes can be added, dragged into order, and removed', () => {
  const drafts = [];
  const makeView = (gestures) => panelManager({
    panels: [], systemPanels: [], config: { ...DEVICE_CONFIG_DEFAULTS, gestures },
    onSetRole() {}, onGestureChange: (draft) => drafts.push(draft), expanded: ['gestures'],
  });
  let view = makeView([{ swipes: ['swipe_left', 'swipe_right'], action: '', timeframe: 3 }]);
  let pills = templatesMatching(view, 'class="haui-pill"');
  assert.equal(pills.length, 2);
  assert.match(templateText(pills[0]), /Swipe left/);
  assert.match(templateText(pills[1]), /Swipe right/);
  assert.match(templateText(view), /Drag swipes into order/);

  const handle = templatesMatching(pills[0], 'draggable="true"')[0];
  const dragStartIndex = handle.strings.findIndex((part) => part.trimEnd().endsWith('@dragstart='));
  handle.values[dragStartIndex]({
    currentTarget: { closest: () => ({ classList: { add() {}, remove() {} } }) },
    dataTransfer: { setData() {}, setDragImage() {}, effectAllowed: '' },
  });
  const dropIndex = pills[1].strings.findIndex((part) => part.trimEnd().endsWith('@drop='));
  pills[1].values[dropIndex]({
    currentTarget: {
      classList: { remove() {} },
      getBoundingClientRect: () => ({ left: 0, right: 100, width: 100, top: 0, bottom: 26 }),
    },
    clientX: 80, clientY: 13, preventDefault() {},
  });
  assert.deepEqual(drafts.at(-1).gestures[0].swipes, ['swipe_right', 'swipe_left']);

  view = makeView(drafts.at(-1).gestures);
  const select = { value: 'swipe_up' };
  eventBinding(view, 'panel-gesture_0_add_swipe', '@change')({ currentTarget: select });
  assert.equal(select.value, '');
  assert.deepEqual(drafts.at(-1).gestures[0].swipes, ['swipe_right', 'swipe_left', 'swipe_up']);

  view = makeView(drafts.at(-1).gestures);
  pills = templatesMatching(view, 'class="haui-pill"');
  const removeIndex = pills[0].strings.findIndex((part) => part.trimEnd().endsWith('@click='));
  pills[0].values[removeIndex]();
  assert.deepEqual(drafts.at(-1).gestures[0].swipes, ['swipe_left', 'swipe_up']);

  // One swipe left: no order to drag and no time limit.
  view = makeView([{ swipes: ['swipe_up'], action: 'lights', timeframe: 3 }]);
  assert.doesNotMatch(templateText(view), /Drag swipes into order|panel-gesture_0_timeframe/);
});



test('the unified idle list composes and splits the existing string settings in order', () => {
  assert.deepEqual(idlePanelKeys('clock', 'weather, gone, clock'), ['clock', 'weather', 'gone']);
  assert.deepEqual(idlePanelConfig(['weather', 'gone', 'weather']), {
    idle_panel: 'weather', idle_panel_extra: 'gone',
  });
  assert.deepEqual(idlePanelConfig([]), { idle_panel: '', idle_panel_extra: '' });
});

test('the preview stage draws the bezel, its states and the live tint', () => {
  const noPanel = templateText(previewStage({ state: 'no-panel' }));
  assert.match(noPanel, /No panel to preview/);
  assert.match(noPanel, /Add a panel or assign a home panel/);

  const ready = templateText(previewStage({
    screen: html`<div class="vp-screen-wrap"></div>`,
    hardware: html`<div class="vp-hw-buttons"></div>`,
    live: true,
  }));
  assert.match(ready, /haui-preview-bezel/);
  assert.match(ready, /vp-screen-wrap/);
  assert.match(ready, /vp-hw-buttons/);
  assert.match(ready, /is-live/);
  // The tools are the Diagnostics card's, not the stage's.
  assert.doesNotMatch(ready, /Reset sandbox|Redraw/);

  assert.match(templateText(previewStage({ state: 'loading' })), /Starting the live preview/);
  assert.match(templateText(previewStage({ state: 'error', error: 'no hub' })), /no hub/);
});

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

test('Panel manager marks the configured home panel and offers an idle-list placeholder', () => {
  const view = panelManager({
    panels: [{ key: 'light', title: 'Light' }, { key: 'clock', title: 'Clock' }],
    config: { home_panel: 'clock', idle_panel: '' }, saving: false, onAdd() {}, onSetRole() {},
    expanded: ['roles'],
  });
  const selects = templatesMatching(view, '<select');
  const home = selects.find((select) => select.values.includes('haui-home-panel'));
  const idle = selects.find((select) => select.values.includes('haui-idle-panels'));
  // Lit binds a select's value before its options exist, so the option carries it.
  assert.ok(!home.strings.join('').includes('.value='));
  const selected = (select) => templatesMatching(select, '<option value=')
    .filter((option) => option !== select)
    .map((option) => [option.values[0], option.values[1]]);
  assert.deepEqual(selected(home), [['light', 'Light']]);
  assert.match(templateText(home), /Set panel/);
  assert.ok(templatesMatching(view, 'class="haui-pill"')
    .some((pill) => templateText(pill).includes('Clock')));
  assert.match(templateText(idle), /Add panel/);
  assert.match(templateText(idle), /Light/);
  assert.match(templateText(idle), /Clock/);
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

test('a folded Schedule card says what is scheduled and how many entries there are', () => {
  const folded = templateText(panelManager({
    panels: [], config: {
      brightness: 80,
      schedule: [
        { start: 'sunset', start_offset: -30, end: '22:00', sound: true, brightness: 40, display_off: false },
        { start: '22:00', end: 'sunrise', sound: false, brightness: 5, display_off: true, timeout_display_off: 30 },
      ],
    },
    onSetRole() {},
  }));
  // The windows of the entries, in the order they are tried, plus the count pill.
  assert.match(folded, /Sunset −30 min → 22:00 · 22:00 → Sunrise/);
  assert.match(folded, /2 entries/);
  assert.doesNotMatch(folded, /panel-schedule_0_start_time/, 'the entries stay folded');

  const empty = templateText(panelManager({
    panels: [], config: { brightness: null, schedule: [] }, onSetRole() {},
  }));
  assert.match(empty, /Nothing scheduled: the device settings apply all day\./);
  assert.doesNotMatch(empty, /entries</);
});

test('the Schedule side-stack card edits a draft and saves it explicitly', () => {
  const edits = [];
  const saves = [];
  const config = {
    brightness: 80,
    schedule: [{
      start: '22:00', end: '07:00', sound: true, brightness: 20,
      display_off: true, timeout_display_off: 30,
    }],
  };
  const view = panelManager({
    panels: [], config, scheduleDraft: { ...config, device: 'kitchen' },
    onSetRole() {}, onScheduleChange: (draft) => edits.push(draft),
    onScheduleSave: () => saves.push(true), expanded: ['schedule'],
  });
  const text = templateText(view);
  assert.ok(text.indexOf('Home & idle panels') < text.indexOf('Schedule'));
  assert.doesNotMatch(text, /YAML configuration/);
  assert.match(text, /panel-schedule-base-brightness/);
  assert.match(text, /panel-schedule_0_start_time/);

  const onInput = eventBinding(view, 'panel-schedule_0_start_time', '@input');
  onInput({ target: { value: '21:30' } });
  assert.equal(edits.at(-1).schedule[0].start, '21:30');
  assert.equal(edits.at(-1).brightness, 80);

  const save = controlWith(view, '<button', 'Save');
  click(save);
  assert.deepEqual(saves, [true]);
});

test('the schedule outside-brightness comes from the panel when the hub sets none', () => {
  const edits = [];
  const view = panelManager({
    panels: [],
    config: { brightness: null, brightness_dim: null, schedule: [] },
    deviceBrightness: { full: 62, dimmed: 15 },
    onSetRole() {},
    onScheduleChange: (draft) => edits.push(draft), expanded: ['schedule'],
  });

  // The empty fields name the brightness the panel itself uses.
  assert.equal(placeholderFor(view, 'panel-schedule-base-brightness'), 'Panel: 62');
  assert.equal(placeholderFor(view, 'panel-schedule-base-brightness_dim'), 'Panel: 15');

  // A new entry takes the panel's full brightness, not an invented 100.
  eventBinding(view, 'panel-schedule_add', '@click')();
  assert.equal(edits[0].brightness, 62);

  // A hub setting wins over the panel reading.
  eventBinding(panelManager({
    panels: [], config: { brightness: 40, schedule: [] }, deviceBrightness: { full: 62 },
    onSetRole() {}, onScheduleChange: (draft) => edits.push(draft), expanded: ['schedule'],
  }), 'panel-schedule_add', '@click')();
  assert.equal(edits.at(-1).brightness, 40);
});

test('an entry inherit hint names the panel brightness when the hub sets none', () => {
  const view = panelManager({
    panels: [],
    config: {
      brightness: null,
      brightness_dim: null,
      timeout_dimming: 10,
      schedule: [{ start: '22:00', end: '07:00', sound: true, display_off: true, timeout_display_off: 30 }],
    },
    deviceBrightness: { full: 62, dimmed: 15 },
    onSetRole() {},
    expanded: ['schedule'],
  });

  assert.equal(placeholderFor(view, 'panel-schedule_0_brightness'), 'Inherit (62)');
  assert.equal(placeholderFor(view, 'panel-schedule_0_brightness_dim'), 'Inherit (15)');
});

test('adding the first inline Schedule entry sets the required outside brightness', () => {
  const edits = [];
  const view = panelManager({
    panels: [], config: { brightness: null, schedule: [] }, onSetRole() {},
    onScheduleChange: (draft) => edits.push(draft), expanded: ['schedule'],
  });
  eventBinding(view, 'panel-schedule_add', '@click')();
  assert.equal(edits[0].brightness, 100);  assert.deepEqual(edits[0].schedule, [{
    start: '22:00', start_offset: 0, end: '07:00', end_offset: 0,
    sound: true, brightness: 20, brightness_dim: null, display_off: true,
    timeout_dimming: null, timeout_display_off: 30, duration_dimming: null,
  }]);
});

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

test('Panels side-stack cards start collapsed to their heading', () => {
  const toggled = [];
  const view = panelManager({
    panels: [{ key: 'light' }], config: {}, onSetRole() {}, onToggle: (card) => toggled.push(card),
  });
  const text = templateText(view);
  // Add panel is the view's lead card (panelActions), not a side-stack card.
  assert.doesNotMatch(text, /Add panel/);
  assert.doesNotMatch(text, /Home panel/);
  assert.equal(templatesMatching(view, 'haui-yaml-actions').length, 0);
  assert.equal(templatesMatching(view, 'haui-surface-body').length, 0);
  const toggles = templatesMatching(view, '<button').filter((entry) => entry.values.includes('haui-icon-button haui-expand-toggle'));
  assert.equal(toggles.length, 3);
  toggles.forEach((entry) => assert.ok(entry.values.includes('false'), 'aria-expanded is false'));
  toggles.forEach(click);
  assert.deepEqual(toggled, ['roles', 'schedule', 'gestures']);
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
    onSettings: () => calls.push('settings'), onFirmware: () => calls.push('update'),
    onAdd: () => calls.push('add'), onTheme: () => calls.push('theme'),
  };
  const idle = deviceActions({ status: { connected: true, update: {} }, ...callbacks });
  assert.match(templateText(idle), /Manage this device/);
  const primary = (view) => templatesMatching(view, '<button')
    .find((entry) => entry.values.some((value) => String(value).includes('haui-button-primary')));
  assert.match(templateText(primary(idle)), /Add panel/);
  assert.match(templateText(idle), /haui-action-card-actions is-stacked is-inline/);
  // The settings are the cog beside the title; updates belong to the Connection & device card.
  assert.equal(templatesMatching(idle, 'haui-action-card-tool').length, 1);
  assert.doesNotMatch(templateText(idle), /Updates/);
  for (const label of ['Settings', 'Add panel', 'Theme']) click(controlWith(idle, '<button', label));
  assert.deepEqual(calls, ['settings', 'add', 'theme']);

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

test('a click on a side-stack card heading folds it, except on the heading controls', () => {
  const toggled = [];
  const panels = panelManager({
    panels: [], config: {}, onSetRole() {}, onToggle: (card) => toggled.push(card),
  });
  const device = deviceDetails({
    name: 'kitchen', status: { connected: true, device_info: {} },
    onLogs() {}, onToggleDetails: () => toggled.push('details'),
    yamlExpanded: false, onToggleYaml: () => toggled.push('yaml'),
    onYamlImport() {}, onYamlExport() {},
    onToggleDiagnostics: () => toggled.push('diagnostics'),
  });
  const headings = [panels, device].flatMap((view) => templatesMatching(view, 'haui-surface-heading-copy'));
  const handlers = headings.map((entry) => entry.values.find((value) => typeof value === 'function'));
  assert.equal(handlers.length, 6);
  // A click on the chevron or another heading control is that control's own.
  handlers.forEach((handler) => handler({ target: { closest: () => ({}) } }));
  assert.deepEqual(toggled, []);
  handlers.forEach((handler) => handler({ target: { closest: () => null } }));
  assert.deepEqual(toggled, ['roles', 'schedule', 'gestures', 'details', 'diagnostics', 'yaml']);
});

test('the catalog also offers a copy of an existing panel and filters both lists', () => {
  const picked = [];
  const source = { type: 'grid', key: 'grid_0', title: 'Lights' };
  const options = {
    panelTypes: [{ type_key: 'clock', label: 'Clock', description: 'A clock', category: { key: 'backgrounds', label: 'Backgrounds', icon: 'mdi:wallpaper' } }],
    onQuery() {}, onSelect() {},
    templates: [{
      id: 'kitchen:grid_0', device: 'kitchen', deviceLabel: 'Kitchen', label: 'Lights', detail: 'Grid', panel: source,
    }],
    onSelectTemplate: (panel) => picked.push(panel),
  };
  const catalog = panelCatalog(options);
  assert.match(templateText(catalog), /Copy an existing panel/);
  click(templatesMatching(catalog, 'haui-panel-catalog-option').filter((entry) => templateText(entry).includes('Lights')).at(-1));
  assert.deepEqual(picked, [source]);

  const filtered = templateText(panelCatalog({ ...options, query: 'clock' }));
  assert.match(filtered, /Clock/);
  assert.doesNotMatch(filtered, /Copy an existing panel/);
  assert.doesNotMatch(templateText(panelCatalog({ ...options, query: 'kitchen' })), /No panel types match/);
});

test('the catalog groups the panels to copy by device, collapsed until a search looks into them', () => {
  const panel = (device, key, title) => ({
    id: `${device}:${key}`, device, deviceLabel: device.toUpperCase(), label: title, detail: 'Grid',
    panel: { type: 'grid', key, title },
  });
  const options = {
    panelTypes: [], onQuery() {}, onSelect() {},
    templates: [panel('kitchen', 'grid_0', 'Lights'), panel('hall', 'grid_0', 'Doors'), panel('kitchen', 'grid_1', 'Blinds')],
  };
  const groups = (query = '') => templatesMatching(panelCatalog({ ...options, query }), 'haui-panel-catalog-group');

  const collapsed = groups();
  assert.deepEqual(collapsed.map((group) => group.values[0]), ['kitchen', 'hall']);
  assert.ok(collapsed.every((group) => group.values[1] === false));
  // Each group names its device and counts its panels.
  assert.match(templateText(collapsed[0]), /KITCHEN\s+2[\s\S]*Lights[\s\S]*Blinds/);
  assert.match(templateText(collapsed[1]), /HALL\s+1[\s\S]*Doors/);

  const found = groups('doors');
  assert.deepEqual(found.map((group) => [group.values[0], group.values[1]]), [['hall', true]]);
});

test('the catalog offers the built-in popups the device does not extend, rendered by key', () => {
  const picked = [];
  const previews = [];
  const entry = { key: 'popup_cover', type: 'popup_cover', label: 'Cover', editable: true };
  const options = {
    panelTypes: [{ type_key: 'clock', label: 'Clock', description: 'A clock', category: { key: 'backgrounds', label: 'Backgrounds', icon: 'mdi:wallpaper' } }],
    onQuery() {}, onSelect() {},
    popups: [entry],
    onSelectPopup: (popup) => picked.push(popup),
    preview: (panel, byKey) => { previews.push([panel.key, byKey]); return ''; },
  };
  const catalog = panelCatalog(options);
  assert.match(templateText(catalog), /Extend a popup/);
  assert.deepEqual(previews.at(-1), ['popup_cover', true]);
  click(templatesMatching(catalog, 'haui-panel-catalog-option').filter((item) => templateText(item).includes('popup_cover')).at(-1));
  assert.deepEqual(picked, [entry]);

  const filtered = templateText(panelCatalog({ ...options, query: 'cover' }));
  assert.match(filtered, /Extend a popup/);
  assert.doesNotMatch(filtered, /No panel types match/);
  assert.doesNotMatch(templateText(panelCatalog({ ...options, query: 'clock' })), /Extend a popup/);
});

test('the Panels view has a search field beside the view switch; the Preview does not', () => {
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
      connected: false, current_page: 'grid', haui_version: '0.5.0',
      device_info: { ip: '192.0.2.11', rssi: -61, tft_version: '53.3.1', yaml_version: '0.5.0' },
    },
    onSettings() {}, onFirmware() {}, onLogs() {},
  });
  // The tiles are dimmed while their values are stale.
  const [facts] = templatesMatching(view, '<div class=').filter((entry) => entry.values[0] === 'haui-diag-tiles stale');
  assert.ok(facts);
  assert.equal(facts.values[1].length, 4);
  const shown = facts.values[1].map(templateText).join(' ');
  // The connection readings lead: offline, the uptime tile reads Status: Offline.
  assert.match(shown, /Status[\s\S]*Offline[\s\S]*Wi-Fi[\s\S]*-61 dBm[\s\S]*Current page/);
  for (const label of ['Current page', 'IP address']) assert.match(shown, new RegExp(label));
  // A tile shows its label and value only; the other facts are in the card a hover or tap opens.
  assert.doesNotMatch(shown, /haui-diag-tile-detail/);
  for (const label of ['Last panel update', 'SSID', 'Wi-Fi signal']) assert.match(shown, new RegExp(label));
  // A status poll re-renders the tiles; the open state is not a binding it could reset.
  const [page] = templatesMatching(facts.values[1][2], 'aria-expanded="false"');
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
  assert.match(card, /mdi:wifi-off|wifi-off/);
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
  assert.match(card, /wifi-strength-4/);
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
