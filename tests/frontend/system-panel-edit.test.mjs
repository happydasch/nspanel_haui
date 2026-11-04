import './dom-shim.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/dialogs/edit.js';
import { openSysPanelEdit } from '../../custom_components/nspanel_haui/frontend/system-panels.js';
import { renderSystemPanelCard } from '../../custom_components/nspanel_haui/frontend/panel-sys-grid.js';
import { makeHost } from './fake-host.mjs';

const SYSTEM_PANELS = [
  { key: 'popup_notify', type: 'notify', label: 'Notification', editable: true, hub_driven: true },
  { key: 'sys_settings', type: 'system_settings', label: 'Settings', editable: false, hub_driven: false },
  { key: 'popup_cover', type: 'popup_cover', label: 'Cover', editable: true, hub_driven: false },
];

function collect(value, out = []) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach(v => collect(v, out));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collect(value.strings, out);
    if (Array.isArray(value.values)) collect(value.values, out);
  }
  return out;
}

/** An edit dialog without Lit's constructor (which needs a real DOM). */
function makeDialog(index, data) {
  const Edit = customElements.get('nspanel-dialog-edit-panel');
  const dlg = Object.create(Edit.prototype);
  const panel = { index, data };
  Object.assign(dlg, {
    open: true,
    hass: {},
    panel,
    panelTypes: [{ type_key: 'cover', label: 'Cover', has_header: true, options: [] }],
    saving: false,
    error: null,
    entryId: 'e',
    devicePanels: [],
    systemPanels: SYSTEM_PANELS,
    _editingPanelType: null,
    _editingPanel: panel,
    _itemListData: {},
    _userSelectedType: false,
    requestUpdate() {},
  });
  return dlg;
}

const markup = (dlg) => collect(dlg.render()).join(' ');

/** Run the dialog's save against a form that holds only the given fields. */
function save(dlg, fields = {}) {
  const form = {
    querySelector: (sel) => {
      const id = sel.slice(1);
      return id in fields ? { value: fields[id], checked: fields[id] } : null;
    },
  };
  dlg.renderRoot = { querySelector: () => form };
  let detail = null;
  dlg._emit = (_name, d) => { detail = d; };
  dlg._dispatchSave();
  return detail.panel;
}

test('a popup is edited, not added, and keeps its key and navigation', () => {
  const dlg = makeDialog(-1, { type: 'cover', key: 'popup_cover', show_in_navigation: false });
  const html = markup(dlg);
  assert.match(html, /Edit Panel/);
  assert.doesNotMatch(html, /Add Panel|Panel type|Panel key|Show in navigation/);
  // The cover popup is not hub-driven: PIN and auto-close stay available.
  assert.match(html, /Panel pin/);
  assert.match(html, /Close automatically/);

  const panel = save(dlg, { 'fld-title': 'Setup', 'fld-show-in-nav': true });
  assert.equal(panel.key, 'popup_cover');
  assert.equal(panel.show_in_navigation, false);
  assert.equal(panel.title, 'Setup');
});

test('a hub-driven system panel offers no PIN or auto-close', () => {
  const dlg = makeDialog(-1, {
    type: 'notify', key: 'popup_notify', show_in_navigation: false,
    unlock_code: '1', close_timeout: 5,
  });
  assert.doesNotMatch(markup(dlg), /Panel pin|Close automatically|Advanced/);

  const panel = save(dlg, { 'fld-title': 'Alert' });
  assert.equal(panel.unlock_code, undefined);
  assert.equal(panel.close_timeout, undefined);
  assert.equal(panel.key, 'popup_notify');
});

test('typing a system key into a user panel keeps the user panel form', () => {
  const dlg = makeDialog(0, { type: 'cover', key: 'my_cover' });
  dlg._editingPanel = { ...dlg.panel, data: { ...dlg.panel.data, key: 'popup_cover' } };
  const html = markup(dlg);
  assert.match(html, /Panel key/);
  assert.match(html, /Show in navigation/);
});

test('every entity popup opens with its panel type form, the alarm one included', () => {
  const opened = [];
  const host = {
    _devicePanels: () => [],
    requestUpdate() {},
  };
  for (const [sysType, userType] of [['popup_alarm', 'alarm'], ['popup_cover', 'cover'], ['notify', 'notify']]) {
    openSysPanelEdit(host, { type: sysType, key: `k_${sysType}` });
    opened.push([host._editingPanelType, host._editingPanel.data.key]);
    assert.equal(host._editingPanelType, userType);
    assert.equal(host._editingPanel.data.show_in_navigation, false);
  }
  assert.deepEqual(opened.map(o => o[1]), ['k_popup_alarm', 'k_popup_cover', 'k_notify']);
});

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

test('only popup cards can be edited; the other system panels are read-only', () => {
  // A stale edit of Settings in the store must not show as an override either.
  const panels = [{ type: 'system_settings', key: 'sys_settings' }, { type: 'cover', key: 'popup_cover' }];
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => { throw new Error('no fetch'); });
  host._deviceConfig = {};

  const settings = flat(renderSystemPanelCard(host, SYSTEM_PANELS[1]));
  assert.match(settings, /pg-card-readonly/);
  assert.doesNotMatch(settings, /pg-card-more|pl-badge-edited|@click=\[fn\]/);

  const cover = flat(renderSystemPanelCard(host, SYSTEM_PANELS[2]));
  assert.doesNotMatch(cover, /pg-card-readonly/);
  assert.match(cover, /pg-card-more/);
  assert.match(cover, /pl-badge-edited/);
});
