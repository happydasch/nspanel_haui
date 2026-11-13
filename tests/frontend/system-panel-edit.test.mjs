import './support/browser.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/views/panel-editor.js';
import { openSysPanelEdit } from '../../custom_components/nspanel_haui/frontend/system-panels.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
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
  const Edit = customElements.get('nspanel-panel-editor');
  const dlg = document.createElement('nspanel-panel-editor');
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
  const overlays = [];
  const host = {
    _devicePanels: () => [],
    requestUpdate() {},
    store: {
      getState: () => ({ ui: { overlays } }),
      actions: {
        pushOverlay: (overlay) => overlays.push(overlay),
        replaceTopOverlay: (overlay) => overlays.splice(-1, 1, overlay),
        closeOverlay: (kind) => {
          const index = overlays.findLastIndex((overlay) => overlay.kind === kind);
          if (index >= 0) overlays.splice(index, 1);
        },
      },
    },
  };
  for (const [sysType, userType] of [['popup_alarm', 'alarm'], ['popup_cover', 'cover'], ['notify', 'notify']]) {
    openSysPanelEdit(host, { type: sysType, key: `k_${sysType}` });
    opened.push([host._editingPanelType, host._editingPanel.data.key]);
    assert.equal(host._editingPanelType, userType);
    assert.equal(host._editingPanel.data.show_in_navigation, false);
  }
  assert.deepEqual(opened.map(o => o[1]), ['k_popup_alarm', 'k_popup_cover', 'k_notify']);
  assert.deepEqual(overlays.map(({ kind, subject }) => [kind, subject]), [['panel-editor', 'k_notify']]);
});

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

test('the Popups group lists only extended popups, with edit and reset; fixed system panels are left out', () => {
  const device = { name: 'kitchen', panels: [{ type: 'cover', key: 'popup_cover' }], config: {} };
  const modelFor = (systemPanels) => {
    const host = makeHost({
      system_panels: systemPanels,
      devices: { kitchen: { config: {}, panels: device.panels } },
    }, () => { throw new Error('no fetch'); });
    Object.setPrototypeOf(host, NSPanelEditor.prototype);
    host._store = host.store;
    host._panelTypes = [];
    host._collapsedPanelGroups = [];
    return host._panelListModel(device, null);
  };

  const fixedModel = modelFor([SYSTEM_PANELS[1]]);
  assert.deepEqual(fixedModel.groups.map((group) => group.id), ['navigation', 'hidden', 'popups']);
  assert.equal(fixedModel.groups[2].entries.length, 0);

  const popup = modelFor([SYSTEM_PANELS[2]]).groups[2].entries[0];
  assert.deepEqual(popup.menu.map((item) => (item === 'divider' ? item : item.label)), [
    'Edit', 'divider', 'Reset to default',
  ]);
  assert.equal(typeof popup.onEdit, 'function');
});

test('an entity popup without an entity previews a random one of its domain, kept for the session', (t) => {
  const states = {
    'light.desk': { state: 'on' },
    'light.attic': { state: 'unavailable' },
    'light.porch': { state: 'off' },
    'switch.fan': { state: 'on' },
  };
  const lightType = { type_key: 'light', label: 'Light', options: [{ key: 'item', kind: 'item', domain: 'light' }] };
  const popup = (data) => Object.assign(makeDialog(-1, { type: 'light', key: 'popup_light', ...data }), {
    hass: { states }, panelTypes: [lightType],
  });
  t.mock.method(Math, 'random', () => 0.99);

  const dlg = popup({});
  // An unavailable light shows the layout only: a light with a state goes first.
  assert.deepEqual(dlg._popupSample(), { item: 'light.porch', item_id: 'light.porch' });
  Math.random.mock.mockImplementation(() => 0);
  assert.deepEqual(dlg._popupSample(), { item: 'light.porch', item_id: 'light.porch' });

  // A saved popup keeps an empty single-item field; one that names its entity shows that one.
  assert.deepEqual(popup({ item: { item: null } })._popupSample(), { item: 'light.desk', item_id: 'light.desk' });
  assert.equal(popup({ item: { item: 'light.attic' } })._popupSample(), null);
  // A popup that opens for no entity has no sample.
  assert.equal(makeDialog(-1, { type: 'cover', key: 'popup_cover' })._popupSample(), null);
});

test('in the sidebar a small preview with the name, type and key pins once the preview scrolls away', () => {
  const dlg = Object.assign(makeDialog(-1, { type: 'cover', key: 'popup_cover', title: 'Blinds' }), {
    inline: true,
    previewContext: { entryId: 'e', device: 'kitchen', deviceConfig: {}, panels: [] },
    _previewPinned: false,
  });
  const text = markup(dlg);
  assert.match(text, /haui-panel-editor-pin-bar/);
  assert.match(text, /Blinds/);
  assert.match(text, /Cover · popup_cover/);

  const scroll = (previewBottom) => {
    dlg.renderRoot = { querySelector: () => ({ getBoundingClientRect: () => ({ bottom: previewBottom }) }) };
    dlg._onFormScroll({ currentTarget: { getBoundingClientRect: () => ({ top: 100 }) } });
    return dlg._previewPinned;
  };
  assert.equal(scroll(400), false);
  assert.equal(scroll(150), true);
  assert.equal(scroll(400), false);
});
