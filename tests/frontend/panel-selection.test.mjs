import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeHost } from './fake-host.mjs';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

/** An editor whose own state is the fake host's store, as the shell reads it. */
function editor(panels, systemPanels = []) {
  const host = makeHost({ version: 1, system_panels: systemPanels, devices: panels }, () => {
    throw new Error('unexpected request');
  });
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._panelTypes = [
    { type_key: 'grid', label: 'Grid', description: 'A grid of entities.', icon: 'mdi:view-grid' },
    { type_key: 'light', label: 'Light', description: 'One light.', icon: 'mdi:lightbulb' },
  ];
  host._selectedPanelKey = null;
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
  assert.equal(model.idlePanels, 'Clock');
});

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

test('a selected panel carries its type, key, group, role and row actions', () => {
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
  assert.equal(facts.Role, 'Home panel');

  assert.deepEqual(model.actions.map((action) => action.label), ['Edit', 'Duplicate', 'Delete']);
  model.actions[0].onClick();
  model.actions[2].onClick();
  assert.deepEqual(edits, [0, 'delete 0']);
  model.onClose();
  assert.equal(host._selectedPanelKey, null);
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
  const hidden = Object.fromEntries(
    host._panelSideModel(host._store.getState().devices.byName.kitchen, null)
      .facts.map(([label, value]) => [label, value]),
  );
  assert.equal(hidden.Group, 'Hidden');
  // The configured home is unset, so the first navigation panel carries no role here.
  assert.equal(hidden.Role, undefined);

  host._selectedPanelKey = 'popup_light';
  const resets = [];
  host._resetSysPanelOverride = (key) => resets.push(key);
  const popup = host._panelSideModel(host._store.getState().devices.byName.kitchen, null);
  assert.deepEqual(popup.actions.map((action) => action.label), ['Edit', 'Reset to default']);
  assert.equal(Object.fromEntries(popup.facts.map(([label, value]) => [label, value])).Group, 'Popup');
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
