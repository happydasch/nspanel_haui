import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import * as Crud from '../../custom_components/nspanel_haui/frontend/crud.js';
import { getPanelMoveState, getSystemPanelKeys } from '../../custom_components/nspanel_haui/frontend/panel-utils.js';
import { jsonResponse, makeHost } from './fake-host.mjs';

// The system-panel override is stored among the user panels but the editor lists
// it under System Panels, so the Non-Navigation group shows only first, second.
const first = { type: 'clock', key: 'clock_0', show_in_navigation: false };
const override = { type: 'light', key: 'popup_light', show_in_navigation: false };
const second = { type: 'clock', key: 'clock_1', show_in_navigation: false };

function hostWithOverride() {
  const host = makeHost(
    {
      devices: { kitchen: { config: {}, panels: [first, override, second] } },
      system_panels: [{ key: 'popup_light', type: 'popup_light' }],
    },
    () => jsonResponse({ status: 'ok' }),
  );
  host._deviceConfig = { enabled: true };
  host._savePanels = (p, m, c) => Crud.savePanels(host, p, m, c);
  return host;
}

test('moving a panel up skips a hidden system-panel override', async () => {
  const host = hostWithOverride();

  Crud.moveUp(host, 'clock_1');
  await new Promise((r) => setImmediate(r));

  const keys = host._panels.devices.kitchen.panels.map((p) => p.key);
  assert.deepEqual(keys.filter((k) => k !== 'popup_light'), ['clock_1', 'clock_0']);
});

test('moving a panel down skips a hidden system-panel override', async () => {
  const host = hostWithOverride();

  Crud.moveDown(host, 'clock_0');
  await new Promise((r) => setImmediate(r));

  const keys = host._panels.devices.kitchen.panels.map((p) => p.key);
  assert.deepEqual(keys.filter((k) => k !== 'popup_light'), ['clock_1', 'clock_0']);
});

test('move buttons ignore a hidden system-panel override', () => {
  const host = hostWithOverride();
  const sysKeys = getSystemPanelKeys(host);
  const panels = [override, first, second];

  const top = getPanelMoveState(first, panels, false, sysKeys);
  const bottom = getPanelMoveState(second, panels, false, sysKeys);

  assert.equal(top.canMoveUp, false);
  assert.equal(top.canMoveDown, true);
  assert.equal(bottom.canMoveUp, true);
  assert.equal(bottom.canMoveDown, false);
});
