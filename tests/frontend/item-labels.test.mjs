import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { itemLabels, itemTypeShort } from '../../custom_components/nspanel_haui/frontend/haui-item.js';
import { fetchTranslations } from '../../custom_components/nspanel_haui/frontend/localize.js';

test('item type labels use the language loaded after the module was imported', async () => {
  const translations = { Navigate: 'Nawiguj', 'Target Panel': 'Panel docelowy' };
  const hass = { fetchWithAuth: async () => ({ json: async () => translations }) };

  await fetchTranslations(hass, 'pl');

  assert.equal(itemTypeShort().navigate, 'Nawiguj');
  assert.equal(itemLabels().navigate.label, 'Panel docelowy');
});

import { panelTargetOptions } from '../../custom_components/nspanel_haui/frontend/haui-item.js';

test('navigate targets list device panels, then system panels, as "title (key)"', () => {
  const options = panelTargetOptions(
    [{ key: 'grid_cover', title: 'Rolety' }, { key: 'qr_0' }],
    [{ key: 'sys_settings', label: 'Settings' }],
    'grid_cover',
  );

  assert.deepEqual(options, [
    { value: 'grid_cover', label: 'Rolety (grid_cover)' },
    { value: 'qr_0', label: 'qr_0' },
    { value: 'sys_settings', label: 'Settings (sys_settings)' },
  ]);
});

test('a target key that no panel has stays selectable', () => {
  const options = panelTargetOptions([{ key: 'grid_0', title: 'Home' }], [], 'removed_panel');

  assert.equal(options[0].value, 'removed_panel');
  assert.match(options[0].label, /^removed_panel \(/);
});
