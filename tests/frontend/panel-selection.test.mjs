import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { jsonResponse, makeHost } from './fake-host.mjs';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import * as Crud from '../../custom_components/nspanel_haui/frontend/crud.js';

/** Keys of the rows the Panels view's list marks as new. */
function newRowKeys(host) {
  return host._panelListModel(host._store.getState().devices.byName.kitchen, null)
    .groups.flatMap((group) => group.entries)
    .filter((entry) => entry.isNew)
    .map((entry) => entry.key);
}

/** Flatten a Lit TemplateResult tree to text. */
function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (value?.strings) return value.strings.reduce((text, part, index) => text + part + flatten(value.values[index]), '');
  return value == null ? '' : String(value);
}

/** An editor whose own state is the fake host's store, as the shell reads it. */
function editor(panels, systemPanels = [], respond = () => {
  throw new Error('unexpected request');
}) {
  const host = makeHost({ version: 1, system_panels: systemPanels, devices: panels }, respond);
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._panelTypes = [
    { type_key: 'grid', label: 'Grid', description: 'A grid of entities.', icon: 'mdi:view-grid' },
    { type_key: 'light', label: 'Light', description: 'One light.', icon: 'mdi:lightbulb' },
  ];
  host._selectedPanelKey = null;
  host._collapsedPanelGroups = [];
  return host;
}

const DEVICE = {
  kitchen: {
    config: { home_panel: 'lights', idle_panel: 'clock', display_model: 'eu' },
    panels: [
      { key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true, items: [{}, {}] },
      { key: 'clock', type: 'grid', title: 'Clock', show_in_navigation: false, items: [] },
    ],
  },
};

test('with no panel selected the side model describes the list and its home and idle panels', () => {
  const host = editor(DEVICE);
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  assert.equal(model.kind, 'overview');
  assert.equal(model.navigationCount, 1);
  assert.equal(model.hiddenCount, 1);
  assert.equal(model.popupCount, 0);
  // The configured assignments, by their panel titles.
  assert.equal(model.homePanel, 'Lights');
  assert.equal(model.idlePanels, 'Clock');});

test('the overview names the first navigation panel as home while none is configured', () => {
  const host = editor({
    kitchen: { config: {}, panels: [{ key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true }] },
  });
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  assert.equal(model.homePanel, 'Lights');
  assert.equal(model.idlePanels, '');

  const empty = editor({ kitchen: { config: {}, panels: [] } });
  const none = empty._panelSideModel(empty._store.getState().devices.byName.kitchen, null);
  assert.equal(none.homePanel, '');
  assert.equal(none.idlePanels, '');
});

test('a configured panel the device no longer has is not used as home or idle', () => {
  const host = editor({
    kitchen: {
      config: { home_panel: 'gone', idle_panel: 'gone2', idle_panel_extra: 'weather' },
      panels: [
        { key: 'clock', type: 'grid', title: 'Clock', show_in_navigation: true },
        { key: 'weather', type: 'grid', title: 'Weather', show_in_navigation: false },
      ],
    },
  });
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  // Both roles answer alike: the stale key is named, and neither tile claims a
  // panel the device does not play for that role.
  assert.equal(model.homePanel, 'Unknown key "gone"');
  assert.equal(model.homePanelKey, '');
  assert.equal(model.idlePanels, 'Weather');
  assert.equal(model.idlePanelKey, 'weather');
});

test('an idle list whose panels are all gone names its unknown key, like home', () => {
  const host = editor({
    kitchen: {
      config: { home_panel: 'gone', idle_panel: 'gone2' },
      panels: [{ key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true }],
    },
  });
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  assert.equal(model.homePanel, 'Unknown key "gone"');
  assert.equal(model.idlePanels, 'Unknown key "gone2"');
  assert.equal(model.idlePanelKey, '');
});

test('a stale idle assignment names the unknown key and selects nothing', () => {
  const host = editor({
    kitchen: {
      config: { idle_panel: 'gone' },
      panels: [{ key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true }],
    },
  });
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  // The device opens no idle page, and the tile says why rather than "Not set".
  assert.equal(model.idlePanels, 'Unknown key "gone"');
  assert.equal(model.idlePanelKey, '');
});

test('the Home marker follows the panel the device actually opens', () => {
  const host = editor({
    kitchen: {
      config: { home_panel: 'gone' },
      panels: [
        { key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true },
        { key: 'clock', type: 'grid', title: 'Clock', show_in_navigation: true },
      ],
    },
  });
  const model = host._panelListModel(host._store.getState().devices.byName.kitchen, null);
  const marked = model.groups[0].entries
    .filter((entry) => entry.roles.length)
    .map((entry) => entry.key);
  assert.deepEqual(marked, ['lights']);
});

test('the idle list is summarised by its first panel and the rest', () => {
  const host = editor({
    kitchen: {
      config: { idle_panel: 'clock', idle_panel_extra: 'weather, lights' },
      panels: [
        { key: 'clock', type: 'grid', title: 'Clock' },
        { key: 'weather', type: 'grid', title: 'Weather' },
        { key: 'lights', type: 'grid', title: 'Lights' },
      ],
    },
  });
  assert.equal(host._panelSideModel(host._store.getState().devices.byName.kitchen, null).idlePanels,
    'Clock and 2 more');
});

test('every panel of the idle sequence carries its marker, numbered after the first', () => {
  const host = editor({
    kitchen: {
      config: { home_panel: 'weather', idle_panel: 'clock', idle_panel_extra: 'weather, lights' },
      panels: [
        { key: 'clock', type: 'grid', title: 'Clock', show_in_navigation: true },
        { key: 'weather', type: 'grid', title: 'Weather', show_in_navigation: true },
        { key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true },
      ],
    },
  });
  const model = host._panelListModel(host._store.getState().devices.byName.kitchen, null);
  const labels = Object.fromEntries(model.groups[0].entries.map((entry) => [
    entry.key,
    entry.roles.map((marker) => flatten(marker).match(/aria-label=(.*?)>/)?.[1]),
  ]));
  // The home panel may also be part of the cycle; each role keeps its own marker.
  assert.deepEqual(labels, {
    clock: ['Idle panel'],
    weather: ['Home panel', 'Idle panel 2'],
    lights: ['Idle panel 3'],
  });
});

test('folding the preview is remembered per browser', () => {
  const memory = new Map();
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: { getItem: (key) => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, String(value)) },
  });
  try {
    const host = makeHost({ version: 1, system_panels: [], devices: DEVICE }, () => {
      throw new Error('unexpected request');
    });
    Object.setPrototypeOf(host, NSPanelEditor.prototype);
    host._store = host.store;
    host._panelPreviewCollapsed = false;

    host._togglePanelPreview();
    assert.equal(host._panelPreviewCollapsed, true);
    assert.equal(memory.get('haui_panelPreviewFolded'), '1');
    host._togglePanelPreview();
    assert.equal(host._panelPreviewCollapsed, false);
    assert.equal(memory.get('haui_panelPreviewFolded'), '0');

    // A new editor starts from the stored choice.
    memory.set('haui_panelPreviewFolded', '1');
    const started = new NSPanelEditor();
    assert.equal(started._panelPreviewCollapsed, true);
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous);
    else delete globalThis.localStorage;
  }
});

test('the catalog preview size is remembered per browser', () => {
  const memory = new Map();
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: { getItem: (key) => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, String(value)) },
  });
  try {
    const host = makeHost({ version: 1, system_panels: [], devices: DEVICE }, () => {
      throw new Error('unexpected request');
    });
    Object.setPrototypeOf(host, NSPanelEditor.prototype);
    host._store = host.store;
    host._panelCatalogCompact = false;

    host._chooseCatalogPreviewSize(true);
    assert.equal(host._panelCatalogCompact, true);
    assert.equal(memory.get('haui_panelCatalogCompact'), '1');
    host._chooseCatalogPreviewSize(false);
    assert.equal(host._panelCatalogCompact, false);
    assert.equal(memory.get('haui_panelCatalogCompact'), '0');

    // A new editor opens the catalog the way it was left.
    memory.set('haui_panelCatalogCompact', '1');
    const started = new NSPanelEditor();
    assert.equal(started._panelCatalogCompact, true);
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous);
    else delete globalThis.localStorage;
  }
});

test('a selected panel carries its type, key, group, roles and row actions', () => {
  const host = editor(DEVICE);
  host._selectedPanelKey = 'lights';
  const edits = [];
  host._openEdit = (index) => edits.push(index);
  host._confirmDelete = (index) => edits.push(`delete ${index}`);
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);

  assert.equal(model.kind, 'panel');
  assert.equal(model.title, 'Lights');
  assert.equal(model.subtitle, 'Grid');
  assert.equal(model.description, 'A grid of entities.');
  assert.equal(model.iconName, 'mdi:view-grid');
  assert.ok(model.preview.strings.join('').includes('nspanel-simulator-frame'));
  // The render asks for the panel's page, not for a system panel by key.
  const byKey = model.preview.values[model.preview.strings.findIndex((part) => part.includes('.byKey='))];
  assert.equal(byKey, false);

  const facts = Object.fromEntries(model.facts.map(([label, value]) => [label, value]));
  assert.equal(facts.Type, 'Grid');
  assert.match(facts.Key.strings.join(''), /haui-panel-info-key/);
  assert.equal(facts.Group, 'Navigation');
  assert.equal(facts.Items, '2');

  // The configured roles this panel holds, as toggles.
  assert.deepEqual(model.roles.map((role) => [role.key, role.active]), [['home', true], ['idle', false]]);

  assert.deepEqual(model.actions.map((action) => action.label), ['Edit', 'Duplicate', 'Delete']);
  model.actions[0].onClick();
  model.actions[2].onClick();
  assert.deepEqual(edits, [0, 'delete 0']);
  model.onClose();
  assert.equal(host._selectedPanelKey, null);
});

test('the card sets and unsets the home and idle panels in the device settings', async () => {
  const writes = [];
  const host = makeHost({ version: 1, system_panels: [], devices: DEVICE }, (method, path, opts) => {
    if (method === 'PUT' && path.includes('/devices/')) {
      const body = JSON.parse(opts.body);
      writes.push(body.config);
      // The hub answers with what it stored, which is what the store applies.
      return jsonResponse({ config: body.config });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._panelTypes = [];
  // The clock is the idle panel, the lights are the home panel.
  host._selectedPanelKey = 'clock';
  const device = () => host._store.getState().devices.byName.kitchen;
  const rolesOf = (model) => Object.fromEntries(model.roles.map((role) => [role.key, role.active]));
  const roles = rolesOf(host._panelSideModel(device(), null));
  assert.deepEqual(roles, { home: false, idle: true });

  // Setting the home panel moves the role from the lights to the clock.
  await host._panelSideModel(device(), null).roles.find((role) => role.key === 'home').onToggle();
  assert.equal(writes[0].home_panel, 'clock');
  // Taking the clock out of the idle sequence leaves the sequence empty.
  await host._panelSideModel(device(), null).roles.find((role) => role.key === 'idle').onToggle();
  assert.equal(writes[1].home_panel, 'clock');
  assert.equal(writes[1].idle_panel, '');
  assert.equal(writes[1].idle_panel_extra, '');
  assert.deepEqual(rolesOf(host._panelSideModel(device(), null)), { home: true, idle: false });
});

test('the idle role adds the panel to the end of the idle sequence', async () => {
  const writes = [];
  const host = makeHost({
    version: 1,
    system_panels: [],
    devices: {
      kitchen: {
        config: { idle_panel: 'clock', idle_panel_extra: 'weather' },
        panels: [
          { key: 'clock', type: 'grid', title: 'Clock' },
          { key: 'weather', type: 'grid', title: 'Weather' },
          { key: 'lights', type: 'grid', title: 'Lights' },
        ],
      },
    },
  }, (method, path, opts) => {
    const body = JSON.parse(opts.body);
    writes.push(body.config);
    return jsonResponse({ config: body.config });
  });
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._panelTypes = [];
  host._selectedPanelKey = 'lights';
  const model = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  assert.equal(model.roles.find((role) => role.key === 'idle').active, false);

  await model.roles.find((role) => role.key === 'idle').onToggle();
  assert.equal(writes[0].idle_panel, 'clock');
  assert.equal(writes[0].idle_panel_extra, 'weather, lights');
});

test('a hidden panel names its group, and a popup override is edited or reset', () => {
  const host = editor({
    kitchen: {
      config: {},
      panels: [
        { key: 'clock', type: 'grid', title: 'Clock', show_in_navigation: false, items: [] },
        { key: 'popup_light', type: 'light', title: 'Lamp' },
      ],
    },
  }, [{ key: 'popup_light', label: 'Light', editable: true }]);

  host._selectedPanelKey = 'clock';
  const hiddenModel = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  const hidden = Object.fromEntries(hiddenModel.facts.map(([label, value]) => [label, value]));
  assert.equal(hidden.Group, 'Hidden');
  // No role is configured, so neither toggle is pressed.
  assert.deepEqual(hiddenModel.roles.map((role) => role.active), [false, false]);

  host._selectedPanelKey = 'popup_light';
  const resets = [];
  host._resetSysPanelOverride = (key) => resets.push(key);
  const popup = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  assert.deepEqual(popup.actions.map((action) => action.label), ['Edit', 'Reset to default']);
  assert.equal(Object.fromEntries(popup.facts.map(([label, value]) => [label, value])).Group, 'Popup');
  // A popup override is not part of the page cycle, so it takes no role.
  assert.deepEqual(popup.roles, []);
  popup.actions[1].onClick();
  assert.deepEqual(resets, ['popup_light']);
});

test('a selection that no longer exists falls back to the overview', () => {
  const host = editor(DEVICE);
  host._selectedPanelKey = 'gone';
  assert.equal(host._panelSideModel(host._store.getState().devices.byName.kitchen, null).kind, 'overview');
});

test('picking a row selects it, and picking it again clears the selection', () => {
  const host = editor(DEVICE);
  host._togglePanelSelection('lights');
  assert.equal(host._selectedPanelKey, 'lights');
  host._togglePanelSelection('clock');
  assert.equal(host._selectedPanelKey, 'clock');
  host._togglePanelSelection('clock');
  assert.equal(host._selectedPanelKey, null);
});

test('a panel the user adds is marked as new in the list, an edit is not', async () => {
  const host = editor(DEVICE, [], () => jsonResponse({ status: 'ok' }));

  await Crud.saveFromData(host, { type: 'grid', key: 'grid_0', title: 'New grid' }, -1);
  assert.deepEqual(newRowKeys(host), ['grid_0']);

  // A save that changes an existing panel leaves the list's marks where they are.
  await Crud.saveFromData(host, { type: 'grid', key: 'lights', title: 'Lights at home' }, 0);
  assert.deepEqual(newRowKeys(host), ['grid_0']);
});

test('only the rows just created are marked as new', () => {
  const host = editor(DEVICE);
  assert.deepEqual(newRowKeys(host), []);
  host._markNewPanels(['lights']);
  assert.deepEqual(newRowKeys(host), ['lights']);
});
