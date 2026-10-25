import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { renderEntityPicker } from '../../custom_components/nspanel_haui/frontend/haui-entity.js';

const DIALOGS = [
  'nspanel-dialog-edit-panel',
  'nspanel-dialog-confirm',
  'nspanel-dialog-device-config',
  'nspanel-dialog-device-info',
  'nspanel-dialog-logs',
  'nspanel-dialog-device-manager',
  'nspanel-dialog-colors',
];

function shouldUpdate(tag, open, changed) {
  const proto = customElements.get(tag).prototype;
  return proto.shouldUpdate.call({ open }, new Map(changed));
}

test('closed dialogs skip renders caused only by a new hass object', () => {
  for (const tag of DIALOGS) {
    assert.equal(shouldUpdate(tag, false, [['hass', {}]]), false, tag);
  }
});

test('dialogs still render when open, opening, or given other changes', () => {
  for (const tag of DIALOGS) {
    assert.equal(shouldUpdate(tag, true, [['hass', {}]]), true, tag);
    assert.equal(shouldUpdate(tag, true, [['open', false]]), true, tag);
    assert.equal(shouldUpdate(tag, false, [['hass', {}], ['open', true]]), true, tag);
  }
});

test('entity pickers sharing one hass read its states once', () => {
  let scans = 0;
  const states = new Proxy(
    { 'light.b': { attributes: {} }, 'light.a': { attributes: {} }, 'switch.c': { attributes: {} } },
    { ownKeys(target) { scans++; return Reflect.ownKeys(target); } },
  );
  const hass = { states };

  for (const id of ['e1', 'e2', 'e3']) renderEntityPicker({ id, value: '', hass });

  assert.equal(scans, 1);
});
