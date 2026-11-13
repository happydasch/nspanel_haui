import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import * as Crud from '../../custom_components/nspanel_haui/frontend/crud.js';
import { saveTheme } from '../../custom_components/nspanel_haui/frontend/theme-editor.js';
import { jsonResponse, makeHost } from './fake-host.mjs';

const clock = { type: 'clock', key: 'clock_0', show_in_navigation: true };

function rejectingHost() {
  const host = makeHost(
    { devices: { kitchen: { config: {}, panels: [clock] } } },
    () => jsonResponse({ message: 'Invalid panel config' }, 400),
  );
  host._deviceConfig = { enabled: true };
  host._savePanels = (p, m, c) => Crud.savePanels(host, p, m, c);
  return host;
}

test('a rejected colour save shows only the error and keeps the old colours', async () => {
  const host = rejectingHost();

  await saveTheme(host, { themeId: 'dark', resetPanelColors: true, themeVariant: 'dark' });

  assert.deepEqual(host.toasts.map(([kind]) => kind), ['error']);
  assert.equal(host._deviceConfig.enabled, true);
});
test('a drop reorders within the group and preserves hidden-panel slots', () => {
  const panels = [
    { type: 'clock', key: 'a', show_in_navigation: true },
    { type: 'clock', key: 'hidden', show_in_navigation: false },
    { type: 'clock', key: 'b', show_in_navigation: true },
    { type: 'clock', key: 'c', show_in_navigation: true },
  ];
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => {});
  let saved;
  host._savePanels = (next, message) => { saved = { next, message }; };

  Crud.movePanelToGroup(host, 'b', 'navigation', 'a');

  assert.deepEqual(saved.next.map((panel) => panel.key), ['b', 'hidden', 'a', 'c']);
  assert.equal(saved.message, 'Panel moved to Navigation');
});

test('a drop before a row further down lands directly before it', () => {
  const panels = ['a', 'b', 'c', 'd'].map((key) => ({ type: 'clock', key, show_in_navigation: true }));
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => {});
  let saved;
  host._savePanels = (next) => { saved = next.map((panel) => panel.key); };

  Crud.movePanelToGroup(host, 'a', 'navigation', 'c');
  assert.deepEqual(saved, ['b', 'a', 'c', 'd']);
  Crud.movePanelToGroup(host, 'a', 'navigation');
  assert.deepEqual(saved, ['b', 'c', 'd', 'a']);
});

test('a new panel can start as a copy of an existing one under a free key', () => {
  const panels = [{ type: 'grid', key: 'grid_0', title: 'Lights', items: [{ item: 'light.a' }] }];
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => {});

  Crud.openAddFrom(host, panels[0]);

  assert.equal(host._editingPanel.index, -1);
  assert.equal(host._editingPanel.data.key, 'grid_1');
  assert.equal(host._editingPanel.data.title, 'Lights');
  assert.notEqual(host._editingPanel.data.items, panels[0].items);
  assert.equal(host.store.getState().ui.overlays.at(-1).kind, 'panel-editor');
});

test('duplicating a panel copies it under a new key right after the original', () => {
  const panels = [
    { type: 'grid', key: 'grid_0', title: 'Lights', items: [{ item: 'light.a' }] },
    { type: 'clock', key: 'clock_0' },
  ];
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => {});
  let saved;
  host._savePanels = (next) => { saved = next; };

  Crud.duplicatePanel(host, 'grid_0');
  assert.deepEqual(saved.map((panel) => panel.key), ['grid_0', 'grid_1', 'clock_0']);
  assert.equal(saved[1].title, 'Lights (copy)');
  assert.deepEqual(saved[1].items, [{ item: 'light.a' }]);
  assert.notEqual(saved[1].items, panels[0].items);
});

test('a drop into the other group flips visibility and lands at the drop position', () => {
  const panels = [
    { type: 'clock', key: 'a', show_in_navigation: true },
    { type: 'clock', key: 'b', show_in_navigation: true },
    { type: 'clock', key: 'hidden', show_in_navigation: false },
  ];
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => {});
  let saved;
  host._savePanels = (next, message) => { saved = { next, message }; };

  Crud.movePanelToGroup(host, 'a', 'hidden');

  assert.deepEqual(saved.next.map((panel) => panel.key), ['b', 'hidden', 'a']);
  assert.equal(saved.next[2].show_in_navigation, false);
  assert.equal(saved.message, 'Panel moved to Non-Navigation');
});

test('an invalid drop never saves', () => {
  const panels = [
    { type: 'clock', key: 'a', show_in_navigation: true },
    { type: 'light', key: 'popup_light', show_in_navigation: false },
  ];
  const host = makeHost({
    devices: { kitchen: { config: {}, panels } },
    system_panels: [{ key: 'popup_light', editable: true }],
  }, () => {});
  host._savePanels = () => assert.fail('Invalid drag must not save');

  Crud.movePanelToGroup(host, 'a', 'navigation', 'a');
  Crud.movePanelToGroup(host, 'popup_light', 'navigation');
  Crud.movePanelToGroup(host, 'a', 'popups');
  Crud.movePanelToGroup(host, 'a', 'navigation');
});

test('a save started while another is in flight is not sent', async () => {
  const pending = [];
  const host = makeHost({ devices: { kitchen: { config: {}, panels: [clock] } } }, () =>
    new Promise((resolve) => pending.push(() => resolve(jsonResponse({ status: 'ok' })))));

  const first = Crud.savePanels(host, [clock], 'first');
  const second = Crud.savePanels(host, [], 'second');
  pending.forEach((release) => release());
  await first;

  assert.equal(await second, false);
  assert.deepEqual(host.calls, ['POST /api/nspanel_haui/panels/entry1']);
  assert.deepEqual(host._panels.devices.kitchen.panels, [clock]);
});

test('a rejected panel save keeps the dialog item list for the next attempt', async () => {
  const host = rejectingHost();
  host._panelTypes = [{ type_key: 'grid', options: [{ key: 'items', kind: 'item_list' }] }];
  const dialogItems = { items: [{ item: 'light.kitchen' }, { item: 'light.office' }] };
  host._itemListData = dialogItems;

  await Crud.saveFromData(host, { type: 'grid', key: 'grid_0' }, -1);

  assert.deepEqual(dialogItems.items, [{ item: 'light.kitchen' }, { item: 'light.office' }]);
});

test('a user panel cannot take the key of a fixed system panel, only of a popup', async () => {
  const host = makeHost({ devices: { kitchen: { config: {}, panels: [clock] } } }, () =>
    jsonResponse({ status: 'ok' }));
  host.store.setState((state) => ({
    ...state,
    hub: {
      ...state.hub,
      systemPanels: [
        { key: 'sys_settings', editable: false },
        { key: 'popup_cover', editable: true },
      ],
    },
  }));
  host._panelTypes = [{ type_key: 'grid', options: [] }, { type_key: 'cover', options: [] }];
  host._savePanels = (p, m, c) => Crud.savePanels(host, p, m, c);

  await Crud.saveFromData(host, { type: 'grid', key: 'Sys_Settings' }, -1);
  assert.match(host._error, /belongs to a system panel/);
  assert.deepEqual(host.calls, []);

  host._error = null;
  await Crud.saveFromData(host, { type: 'cover', key: 'popup_cover', show_in_navigation: false }, -1);
  assert.equal(host._error, null);
  assert.deepEqual(host.calls, ['POST /api/nspanel_haui/panels/entry1']);
});

test('generateAutoKey picks the first unused {type}_{n} for the type', () => {
  const panels = [
    { type: 'clock', key: 'clock_0' },
    { type: 'clock', key: 'clock_2' },
    { type: 'grid', key: 'clock_1' },
  ];
  assert.equal(Crud.generateAutoKey(panels, 'clock'), 'clock_1');
  assert.equal(Crud.generateAutoKey(panels, 'grid'), 'grid_0');
  assert.equal(Crud.generateAutoKey([], 'clock'), 'clock_0');
  assert.equal(Crud.generateAutoKey(undefined, 'clock'), 'clock_0');
});

test('selecting a type from the catalog seeds that exact panel type', () => {
  const host = makeHost({ devices: { kitchen: { config: {}, panels: [] } } }, () => {});
  host._panelTypes = [{ type_key: 'clock' }, { type_key: 'cover' }];

  Crud.openAdd(host, 'cover');

  assert.equal(host._editingPanel.data.type, 'cover');
  assert.equal(host._editingPanel.data.key, 'cover_0');
});

test('opening the edit dialog resets the dialog session state', () => {
  const host = makeHost({ devices: { kitchen: { config: {}, panels: [clock] } } }, () => {});
  host._panelTypes = [{ type_key: 'clock' }];
  host._itemListData = { stale: 1 };
  host._error = 'old';
  host._deleteTarget = 3;
  host._dialogVersion = 4;

  Crud.openEdit(host, 0);

  assert.deepEqual(host._editingPanel, { index: 0, data: clock });
  assert.equal(host._editingPanelType, 'clock');
  assert.deepEqual(host._itemListData, {});
  assert.equal(host._error, null);
  assert.equal(host._deleteTarget, null);
  assert.equal(host._dialogVersion, 5);

  Crud.openAdd(host);
  assert.equal(host._editingPanel.index, -1);
  assert.equal(host._editingPanel.data.key, 'clock_1');
  assert.equal(host._dialogVersion, 6);
});
