import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { isPortraitModel } from '../../custom_components/nspanel_haui/frontend/constants.js';
import { renderPanelList } from '../../custom_components/nspanel_haui/frontend/views/panel-list.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import { makeHost } from './fake-host.mjs';

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

/**
 * Build the Device panel-list model through the shell's own builder, so the
 * thumbnail orientation, role markers and system entries are the shipped ones.
 */
function listFor(displayModel, panels = [{ type: 'clock', key: 'clock_0', items: [] }], systemPanels = []) {
  const host = makeHost({
    devices: { kitchen: { config: { display_model: displayModel }, panels } },
    system_panels: systemPanels,
  }, () => { throw new Error('no fetch'); });
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._panelTypes = [{ type_key: 'clock', label: 'Clock', page_id: 3 }];
  host._collapsedPanelGroups = [];

  const state = host.store.getState();
  const device = { name: 'kitchen', panels, config: state.devices.byName.kitchen.config };
  return renderPanelList(host._panelListModel(device, state.devices.byName.kitchen.status));
}

test('the display model decides whether a device uses the portrait layout', () => {
  assert.equal(isPortraitModel('us'), true);
  assert.equal(isPortraitModel('US'), true);
  assert.equal(isPortraitModel('eu'), false);
  assert.equal(isPortraitModel(undefined), false);
});

test('portrait devices render their panel thumbnails in portrait', () => {
  assert.match(flat(listFor('us')), /haui-panel-thumb portrait/);
});

test('landscape devices render their panel thumbnails without portrait', () => {
  const out = flat(listFor('eu'));
  assert.match(out, /haui-panel-thumb/);
  assert.doesNotMatch(out, /haui-panel-thumb portrait/);
});

test('panel thumbnails directly contain the hub-rendered simulator frame', () => {
  assert.match(flat(listFor('eu')), /haui-panel-thumb[\s\S]*nspanel-simulator-frame/);
});

test('the simulator preview draws no duplicate fake header/footer chrome', () => {
  assert.doesNotMatch(flat(listFor('eu')), /pg-card-preview-header|pg-card-preview-footer|pg-card-preview--with-header/);
});

test('only replaced popups are listed, fixed system panels are not', () => {
  const out = flat(listFor('us', [{ type: 'cover', key: 'popup_cover', items: [] }], [
    { type: 'system', key: 'sys_settings', label: 'Settings', editable: false, page_id: 30 },
    { type: 'popup_cover', key: 'popup_cover', label: 'Cover popup', editable: true },
    { type: 'popup_light', key: 'popup_light', label: 'Light popup', editable: true },
  ]));
  assert.match(out, /Cover popup/);
  assert.match(out, /nspanel-simulator-frame/);
  assert.doesNotMatch(out, /Light popup/);
  assert.doesNotMatch(out, /Settings/);
});

test('the panel list builder hands the view a menu for user panels only', () => {
  const host = makeHost({
    devices: { kitchen: { config: {}, panels: [{ type: 'clock', key: 'clock_0', items: [{}, {}] }] } },
    system_panels: [{ key: 'sys_settings', label: 'Settings', editable: false }],
  }, () => { throw new Error('no fetch'); });
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._panelTypes = [{ type_key: 'clock', label: 'Clock', page_id: 3 }];
  host._collapsedPanelGroups = [];
  const state = host.store.getState();
  const model = host._panelListModel(
    { name: 'kitchen', panels: [{ type: 'clock', key: 'clock_0', items: [{}, {}] }], config: {} },
    null,
  );
  assert.deepEqual(model.groups.map((group) => group.id), ['navigation', 'hidden', 'popups']);
  const userEntry = model.groups[0].entries[0];
  assert.equal(userEntry.itemCount, 2);
  assert.ok(userEntry.menu.some((item) => item !== 'divider' && item.danger === true));
  assert.equal(model.groups[2].entries.length, 0);
  assert.equal(state.devices.selected, 'kitchen');
  assert.equal(typeof NSPanelEditor.prototype._panelListModel, 'function');
});
