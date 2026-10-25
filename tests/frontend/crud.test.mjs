import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import * as Crud from '../../custom_components/nspanel_haui/frontend/crud.js';
import { saveColors } from '../../custom_components/nspanel_haui/frontend/colors-editor.js';
import { jsonResponse, makeHost } from './fake-host.mjs';

const clock = { type: 'clock', key: 'clock_0', show_in_navigation: true };

function rejectingHost() {
  const host = makeHost(
    { devices: { kitchen: { config: {}, panels: [clock] } } },
    () => jsonResponse({ message: 'Invalid panel config' }, 400),
  );
  host._deviceConfig = { enabled: true, color_overrides: {} };
  host._savePanels = (p, m, c) => Crud.savePanels(host, p, m, c);
  return host;
}

test('a rejected colour save shows only the error and keeps the old colours', async () => {
  const host = rejectingHost();

  await saveColors(host, { background: 123 });

  assert.deepEqual(host.toasts.map(([kind]) => kind), ['error']);
  assert.deepEqual(host._deviceConfig.color_overrides, {});
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
