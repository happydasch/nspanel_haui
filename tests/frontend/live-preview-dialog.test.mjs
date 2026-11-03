import './dom-shim.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/dialogs/edit.js';
import '../../custom_components/nspanel_haui/frontend/dialogs/live-preview.js';
import { renderDeviceInfoStrip } from '../../custom_components/nspanel_haui/frontend/toolbar.js';

function collect(value, out = []) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach(v => collect(v, out));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collect(value.strings, out);
    if (Array.isArray(value.values)) collect(value.values, out);
  }
  return out;
}

function fakeHass() {
  const hass = {
    subscriptions: [],
    unsubscribed: 0,
    calls: [],
    async fetchWithAuth() { return { ok: true, json: async () => ({}) }; },
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

/** A dialog instance without Lit's constructor (which needs a real DOM). */
function makeDialog(props = {}) {
  const Dialog = customElements.get('nspanel-dialog-live-preview');
  const dlg = Object.create(Dialog.prototype);
  const events = [];
  Object.assign(dlg, {
    entryId: 'entry1',
    device: 'kitchen',
    open: false,
    _session: null,
    _error: '',
    _stageWidth: 0,
    _sound: '',
    _displayOff: false,
    _pointerId: null,
    _soundTimer: null,
    _resizeObserver: null,
    renderRoot: { querySelector: () => null },
    requestUpdate() {},
    dispatchEvent(e) { events.push(e); return true; },
    hass: fakeHass(),
  }, props);
  return { dlg, events };
}

const flush = () => new Promise(r => setTimeout(r, 0));

test('opening starts a session for the selected device; closing stops it', async () => {
  const { dlg } = makeDialog();
  dlg.open = true;
  dlg.updated(new Map([['open', false]]));
  await flush();
  assert.equal(dlg.hass.subscriptions.length, 1);
  assert.deepEqual(dlg.hass.subscriptions[0].message, {
    type: 'nspanel_haui/virtual_panel/subscribe',
    entry_id: 'entry1',
    device: 'kitchen',
    live: false,
  });

  dlg.open = false;
  dlg.updated(new Map([['open', true]]));
  await flush();
  assert.equal(dlg._session, null);
  assert.equal(dlg.hass.unsubscribed, 1);
});

test('switching device while open restarts the session', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg.updated(new Map([['open', false]]));
  await flush();
  dlg.device = 'office';
  dlg.updated(new Map([['device', 'kitchen']]));
  await flush();
  assert.equal(dlg.hass.unsubscribed, 1);
  assert.equal(dlg.hass.subscriptions.at(-1).message.device, 'office');
});

test('a closed dialog renders nothing and a starting one says so', async () => {
  const { dlg } = makeDialog();
  assert.equal(collect(dlg.render()).length, 0);
  dlg.open = true;
  dlg.updated(new Map([['open', false]]));
  await flush();
  const markup = collect(dlg.render()).join(' ');
  assert.match(markup, /Starting the live preview/);
  assert.match(markup, /Sandbox mode: touches change simulated states only/);
  assert.match(markup, /Left button/);
});

test('a started session renders the screen and maps pointer input to touches', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg.updated(new Map([['open', false]]));
  await flush();
  const session = dlg._session;
  session._loadLayout = async () => ({
    orientation: 'landscape', width: 480, height: 320, visible_width: 450,
    fonts: [{ id: 0, size: 20, family: 'Roboto', weight: 400 }], globals: {}, pictures: {},
    pages: { 9: { name: 'grid', components: [
      { id: 0, name: 'grid', type: 121, attrs: { x: 0, y: 0, w: 480, h: 320, sta: 1, bco: 0, sendkey: 0 }, events: {} },
      { id: 1, name: 'b', type: 98, attrs: { x: 0, y: 0, w: 225, h: 160, sendkey: 3, sta: 1, bco: 0, pco: 65535, font: 0, txt: 'Hi' }, events: {} },
    ] } },
  });
  dlg.hass.subscriptions[0].callback({ type: 'started', session_id: 's1', portrait: false });
  await flush();
  dlg.hass.subscriptions[0].callback({ type: 'page', page: 9 });

  const markup = collect(dlg.render()).join(' ');
  assert.match(markup, /vp-screen-wrap/);
  assert.doesNotMatch(markup, /Starting the live preview/);

  // The screen is drawn at twice its size: (200, 100) on screen is (100, 50).
  dlg.renderRoot = {
    querySelector: () => ({ getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 640 }) }),
  };
  const target = { setPointerCapture() {} };
  dlg._onPointerDown({ pointerId: 1, clientX: 200, clientY: 100, currentTarget: target, preventDefault() {} });
  dlg._onPointerUp({ pointerId: 1, clientX: 200, clientY: 100 });
  await session._sendChain;
  assert.deepEqual(dlg.hass.calls.map(c => [c.name, c.value]), [
    ['esphome.component', '9,1,1'],
    ['esphome.touch_start', '1'],
    ['esphome.touch_start', ''],
    ['esphome.component', '9,1,0'],
    ['esphome.touch_end', '100,50,100,50'],
  ]);
  dlg._stopSession();
});

test('sounds and display power are shown', () => {
  const { dlg } = makeDialog();
  dlg._onAction({ name: 'play_sound', value: 'notification' });
  assert.equal(dlg._sound, 'notification');
  clearTimeout(dlg._soundTimer);
  dlg._onAction({ name: 'display_off', value: '' });
  assert.equal(dlg._displayOff, true);
  dlg._onAction({ name: 'display_on', value: '' });
  assert.equal(dlg._displayOff, false);
});

test('closing emits dialog-closed', () => {
  const { dlg, events } = makeDialog();
  dlg._close();
  assert.deepEqual(events.map(e => e.type), ['dialog-closed']);
});

test('the toolbar offers the live preview next to colours and settings', () => {
  let opened = 0;
  const host = {
    _deviceStatus: { connected: true, connection_state: 'connected', current_page: 'home', device_info: {} },
    _selectedDevice: 'kitchen',
    _deviceStatusError: null,
    _actionsMenuIndex: '__header__',
    narrow: false,
    hass: { states: {} },
    _onHeaderLivePreview() { opened++; },
  };
  const tpl = renderDeviceInfoStrip(host);
  const markup = collect(tpl).join(' ');
  assert.equal((markup.match(/mdi:television-play/g) || []).length, 2, 'toolbar button and menu entry');
  assert.match(markup, /Live preview/);
});

function renderEditDialog(type, data = {}) {
  const Edit = customElements.get('nspanel-dialog-edit-panel');
  const dlg = Object.create(Edit.prototype);
  const panel = { index: 0, data: { type, key: `${type}_0`, ...data } };
  Object.assign(dlg, {
    open: true,
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

test('the idle timeout button looks selected while the idle page is shown', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg.updated(new Map([['open', false]]));
  await flush();
  // Only the idle timeout button binds its appearance; the others are static.
  const markup = () => collect(dlg.render()).join(' ');
  assert.doesNotMatch(markup(), /\baccent\b/);
  dlg._session.idle = true;
  assert.match(markup(), /\baccent\b/);
  dlg._session.idle = false;
  assert.doesNotMatch(markup(), /\baccent\b/);
  dlg._stopSession();
});

/** The tooltip's two position declarations (its style's interpolated values). */
function tooltipStyle(dlg) {
  return dlg._renderTooltip().values.slice(0, 2);
}

test('hovering a linked widget shows its entity; leaving or pressing hides it', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg.hass.states = { 'light.lamp': { attributes: { friendly_name: 'Lamp' } } };
  dlg.updated(new Map([['open', false]]));
  await flush();
  const session = dlg._session;
  session.display = {
    layout: { width: 480, height: 320, visible_width: 450 },
    components: new Map([['b', { id: 1, name: 'b', hidden: false, attrs: { x: 0, y: 0, w: 225, h: 160 } }]]),
    component: id => (id === 0 ? { name: 'grid' } : null),
  };
  session.entityMap = { b: 'light.lamp' };
  const rect = { left: 0, top: 0, width: 900, height: 640 };
  dlg.renderRoot = { querySelector: () => ({ getBoundingClientRect: () => rect }) };

  // Off by default: no tooltip until "Show entities" is switched on.
  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 100, clientY: 100 });
  assert.equal(dlg._hover, null);
  dlg._setShowEntities(true);

  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 100, clientY: 100 });
  assert.equal(dlg._hover.entityId, 'light.lamp');
  assert.deepEqual(tooltipStyle(dlg), ['left:114px;', 'top:114px;']);
  const tip = collect(dlg._renderTooltip()).join(' ');
  assert.match(tip, /Lamp/);
  assert.match(tip, /light\.lamp/);

  // nothing linked there
  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 800, clientY: 600 });
  assert.equal(dlg._hover, null);
  // touch input never shows it
  dlg._onPointerMove({ pointerId: 8, pointerType: 'touch', clientX: 100, clientY: 100 });
  assert.equal(dlg._hover, null);

  // switching it off hides a shown tooltip
  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 100, clientY: 100 });
  dlg._setShowEntities(false);
  assert.equal(dlg._hover, null);
  dlg._stopSession();
});

test('near the right or bottom edge the tooltip flips to the cursor\'s other side', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg._hover = { entityId: 'light.lamp', x: 800, y: 600, width: 900, height: 640 };
  assert.deepEqual(tooltipStyle(dlg), ['right:114px;', 'bottom:54px;']);
  dlg._hover = { entityId: 'light.lamp', x: 800, y: 100, width: 900, height: 640 };
  assert.deepEqual(tooltipStyle(dlg), ['right:114px;', 'top:114px;']);
});
