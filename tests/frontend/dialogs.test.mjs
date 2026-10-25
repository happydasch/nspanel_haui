import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';

const DIALOGS = [
  'nspanel-dialog-edit-panel',
  'nspanel-dialog-confirm',
  'nspanel-dialog-device-config',
  'nspanel-dialog-device-info',
  'nspanel-dialog-logs',
  'nspanel-dialog-device-manager',
  'nspanel-dialog-colors',
];

/** A dialog instance without Lit's constructor (which needs a real DOM), recording its events. */
function dialog(tag, props = {}) {
  const dlg = Object.create(customElements.get(tag).prototype);
  const events = [];
  Object.assign(dlg, { requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

test('every editor dialog shares the dialog base class', () => {
  for (const tag of DIALOGS) {
    assert.ok(customElements.get(tag).prototype instanceof HauiDialog, tag);
  }
});

test('closing a dialog emits dialog-closed', () => {
  const { dlg, events } = dialog('nspanel-dialog-logs');
  dlg._dispatchClose();
  assert.deepEqual(events.map((e) => e.type), ['dialog-closed']);
});

test('the Device Manager emits add-device with the detail the editor handler reads', () => {
  const { dlg, events } = dialog('nspanel-dialog-device-manager', { devices: {}, _newDeviceName: 'office' });
  dlg._onAddDevice();
  assert.equal(events.length, 1);
  assert.equal(events[0].type, 'add-device');
  assert.deepEqual(events[0].detail, { device: { name: 'office', esphome_device_id: '' } });
});
