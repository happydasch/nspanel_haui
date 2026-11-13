import './support/browser.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/views/panel-editor.js';
import '../../custom_components/nspanel_haui/frontend/views/workspace.js';

function collect(value, out = []) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach(v => collect(v, out));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collect(value.strings, out);
    if (Array.isArray(value.values)) collect(value.values, out);
  }
  return out;
}

function renderText(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(renderText).join('');
  if (value && Array.isArray(value.strings) && Array.isArray(value.values)) {
    return value.strings.map((part, index) => `${part}${renderText(value.values[index])}`).join('');
  }
  return '';
}

function fakeHass() {
  const hass = {
    subscriptions: [],
    unsubscribed: 0,
    calls: [],
    connection: {
      async subscribeMessage(callback, message) {
        hass.subscriptions.push({ callback, message });
        return async () => { hass.unsubscribed++; };
      },
    },
    async callWS(message) { hass.calls.push(message); return null; },
  };
  return hass;
}

/** An inactive workspace instance without Lit's constructor (which needs a real DOM). */
function makeWorkspace(props = {}) {
  const Workspace = customElements.get('nspanel-preview-workspace');
  const workspace = document.createElement('nspanel-preview-workspace');
  const events = [];
  Object.assign(workspace, {
    requestUpdate() {},
    dispatchEvent(event) { events.push(event); return true; },
    events,
    entryId: 'entry1',
    device: 'kitchen',
    active: false,
    _session: null,
    _error: '',
    _stageWidth: 0,
    _pointerId: null,
    _resizeObserver: null,
    renderRoot: { querySelector: () => null },
    hass: fakeHass(),
  }, props);
  return { dlg: workspace };
}

const flush = () => new Promise(r => setTimeout(r, 0));

function renderEditDialog(type, data = {}, inline = false) {
  const Edit = customElements.get('nspanel-panel-editor');
  const dlg = document.createElement('nspanel-panel-editor');
  const panel = { index: 0, data: { type, key: `${type}_0`, ...data } };
  Object.assign(dlg, {
    requestUpdate() {},
    open: true,
    inline,
    hass: {},
    panel,
    panelTypes: [
      { type_key: 'weather', label: 'Weather', has_header: false, options: [] },
      { type_key: 'grid', label: 'Grid', has_header: true, options: [] },
    ],
    saving: false,
    error: null,
    entryId: 'e',
    devicePanels: [],
    systemPanels: [],
    _editingPanelType: null,
    _editingPanel: panel,
    _itemListData: {},
    _userSelectedType: false,
    requestUpdate() {},
  });
  return collect(dlg.render()).join(' ');
}

test('pages without header buttons offer long press to go back', () => {
  assert.match(renderEditDialog('weather'), /Long press to go back/);
  assert.doesNotMatch(renderEditDialog('grid'), /Long press to go back/);
});
test('panel editor can render its existing form in the Device sidebar without dialog chrome', () => {
  const markup = renderEditDialog('weather', {}, true);
  assert.match(markup, /haui-panel-editor-sidebar/);
  assert.match(markup, /Panel title/);
  assert.match(markup, /Long press to go back/);
  assert.doesNotMatch(markup, /<ha-dialog[ >]/);
});

/** A panel editor without Lit's constructor, with a stand-in form. */
function editorWith(data, extra = {}) {
  const Edit = customElements.get('nspanel-panel-editor');
  const dlg = document.createElement('nspanel-panel-editor');
  const fields = { 'fld-key': data.key || '', 'fld-title': data.title || '' };
  Object.assign(dlg, {
    requestUpdate() {},
    open: true, inline: true,
    panel: { index: 0, data },
    panelTypes: [{ type_key: 'grid', label: 'Grid', options: [{ key: 'items', kind: 'item_list' }] }],
    devicePanels: [data, { type: 'clock', key: 'clock_0' }],
    systemPanels: [{ key: 'sys_settings', editable: false }, { key: 'popup_light', editable: true }],
    _editingPanelType: 'grid',
    _editingPanel: { index: 0, data },
    _itemListData: {},
    renderRoot: { querySelector: () => ({
      querySelector: (selector) => (selector in fields || selector.replace('#', '') in fields
        ? { value: fields[selector.replace('#', '')] } : null),
    }) },
    ...extra,
  });
  return dlg;
}

test('the panel editor names the field that cannot be saved and blocks the save', () => {
  const ok = editorWith({ type: 'grid', key: 'grid_0', unlock_code: '1234' });
  assert.equal(ok._fieldErrors().size, 0);

  const taken = editorWith({ type: 'grid', key: 'Clock_0' });
  assert.match(taken._fieldErrors().get('fld-key'), /already used/);
  // The key typed into a user panel's form, not the key the editor was opened with.
  const typed = editorWith({ type: 'grid', key: 'grid_0' }, {
    _editingPanel: { index: 0, data: { type: 'grid', key: 'sys_settings' } },
  });
  assert.match(typed._fieldErrors().get('fld-key'), /system panel/);
  assert.match(editorWith({ type: 'grid', key: 'my panel' })._fieldErrors().get('fld-key'), /spaces/);
  assert.match(editorWith({ type: 'grid', key: 'grid_0', unlock_code: '12a4' })._fieldErrors().get('fld-unlock-code'), /digits/);

  const markup = collect(taken.render()).join(' ');
  assert.match(markup, /role="alert"/);
  const events = [];
  taken._emit = (name) => events.push(name);
  taken._dispatchSave();
  assert.deepEqual(events, []);
});

test('a new field error opens its section once; the user can collapse it again', () => {
  const section = { open: false };
  const field = { closest: (selector) => (selector === 'details' ? section : null) };
  const dlg = editorWith({ type: 'grid', key: 'grid_0', unlock_code: '12a4' }, {
    renderRoot: { querySelector: (selector) => (selector === '#fld-unlock-code' ? field : null) },
    _schedulePreview() {},
  });

  dlg.updated(new Map());
  assert.equal(section.open, true);
  section.open = false;
  dlg.updated(new Map());
  assert.equal(section.open, false);

  // Fixed and broken again: the new error opens the section again.
  dlg.panel.data.unlock_code = '1234';
  dlg.updated(new Map());
  dlg.panel.data.unlock_code = '12b4';
  dlg.updated(new Map());
  assert.equal(section.open, true);
});

test('the panel editor previews the unsaved form after a pause, not on every keystroke', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const data = { type: 'grid', key: 'grid_0', title: 'Lights' };
  const dlg = editorWith(data, { previewContext: { entryId: 'e', device: 'kitchen' } });
  dlg._itemListData = { items: [{ item: 'light.kitchen' }] };

  dlg._schedulePreview();
  t.mock.timers.tick(0);
  assert.equal(dlg._previewPanel.title, 'Lights');
  assert.deepEqual(dlg._previewPanel.items, [{ item: 'light.kitchen' }]);

  // An unchanged form asks for nothing; an edit waits for the typing to pause.
  const first = dlg._previewPanel;
  dlg._schedulePreview();
  dlg._itemListData = { items: [] };
  dlg._schedulePreview();
  t.mock.timers.tick(399);
  assert.equal(dlg._previewPanel, first);
  t.mock.timers.tick(1);
  assert.deepEqual(dlg._previewPanel.items, []);
});
