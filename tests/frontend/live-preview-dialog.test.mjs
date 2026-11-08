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
    async fetchWithAuth(path) {
      const body = path.includes('/notifications/') ? [] : {};
      return { ok: true, json: async () => body };
    },
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
    protocol_version: 2,
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
  const markup = renderText(dlg.render());
  assert.match(markup, /Starting the live preview/);
  const modeNote = markup.indexOf('vp-mode-note');
  const controls = markup.indexOf('view-toggle-group');
  const idleButton = markup.indexOf('vp-idle-button');
  const moreButton = markup.indexOf('vp-more');
  const simulator = markup.indexOf('vp-stage');
  assert.ok(controls < idleButton);
  assert.ok(idleButton < moreButton);
  assert.ok(moreButton < simulator);
  assert.ok(simulator < modeNote);
  assert.match(markup, /Simulated mode: touches update simulated states only/);
  assert.doesNotMatch(markup, /vp-hint/);
  assert.match(markup, /Left button/);
});
test('the entity switch is available at every preview width', () => {
  for (const narrow of [false, true]) {
    const { dlg } = makeDialog({ open: true, _showTools: true });
    dlg.narrow = narrow;
    const markup = collect(dlg.render()).join(' ');
    assert.match(markup, /vp-show-entities/);
  }
});

test('the More tools area resets sandbox state only when changed and keeps reset out of Live mode', async () => {
  const { dlg } = makeDialog();
  let resets = 0;
  dlg._session = { resetSandbox: async () => { resets++; } };
  const unchangedTools = dlg._renderTools({ ready: true, live: false, sandboxChanged: false });
  assert.equal(resetSandboxDisabled(unchangedTools), true);
  const sandboxTools = dlg._renderTools({ ready: true, live: false, sandboxChanged: true });
  assert.equal(resetSandboxDisabled(sandboxTools), false);
  assert.match(renderText(sandboxTools), /vp-reset-sandbox/);
  assert.match(renderText(sandboxTools), /Reset sandbox/);
  await sandboxTools.values.find(value => typeof value === 'function')();
  assert.equal(resets, 1);

  const liveTools = dlg._renderTools({ ready: true, live: true, sandboxChanged: true });
  assert.equal(resetSandboxDisabled(liveTools), true);
});

function resetSandboxDisabled(value) {
  if (Array.isArray(value)) {
    for (const child of value) {
      const found = resetSandboxDisabled(child);
      if (found !== null) return found;
    }
  } else if (value && Array.isArray(value.strings) && Array.isArray(value.values)) {
    for (let i = 0; i < value.values.length; i++) {
      if (value.strings[i].includes('?disabled=')
          && value.strings.slice(0, i + 1).join('').includes('vp-reset-sandbox')) {
        return value.values[i];
      }
      const found = resetSandboxDisabled(value.values[i]);
      if (found !== null) return found;
    }
  }
  return null;
}

/** The toolbar's two mode buttons: icon -> { pressed, click }. */
function modeButtons(value, out = {}) {
  if (Array.isArray(value)) value.forEach(v => modeButtons(v, out));
  else if (value && Array.isArray(value.values)) {
    const icon = value.values.find(v => v === 'mdi:flask-outline' || v === 'mdi:access-point');
    if (icon) {
      out[icon] = {
        pressed: value.values.find(v => v === 'true' || v === 'false'),
        click: value.values.find(v => typeof v === 'function'),
      };
    }
    value.values.forEach(v => modeButtons(v, out));
  }
  return out;
}

test('the toolbar switches between Simulated and Live', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg.updated(new Map([['open', false]]));
  await flush();
  const pressed = () => Object.fromEntries(
    Object.entries(modeButtons(dlg._renderToolbar(dlg._session))).map(([icon, b]) => [icon, b.pressed]),
  );
  assert.deepEqual(pressed(), { 'mdi:flask-outline': 'true', 'mdi:access-point': 'false' });

  // The other mode switches to Live, dropping simulated state server-side.
  modeButtons(dlg._renderToolbar(dlg._session))['mdi:flask-outline'].click();
  modeButtons(dlg._renderToolbar(dlg._session))['mdi:access-point'].click();
  await flush();
  const configure = dlg.hass.calls.filter(c => c.type === 'nspanel_haui/virtual_panel/configure');
  assert.deepEqual(configure.map(c => c.live), [true]);
  assert.deepEqual(pressed(), { 'mdi:flask-outline': 'false', 'mdi:access-point': 'true' });
  assert.match(
    collect(dlg._renderModeNote(dlg._session)).join(' '),
    /Live mode: touches and the hardware buttons switch your real devices/,
  );
  dlg._stopSession();
});

test('the extra tools stay hidden until opened; hiding them stops entity hover', async () => {
  const { dlg } = makeDialog({ open: true });
  dlg.updated(new Map([['open', false]]));
  await flush();
  const markup = () => collect(dlg.render()).join(' ');
  assert.match(markup(), /Idle timeout/);
  assert.doesNotMatch(markup(), /vp-show-entities/);

  dlg._setShowTools(true);
  assert.ok(markup().includes('mdi:sleep'));
  assert.ok(markup().includes('vp-show-entities'));
  dlg._setShowEntities(true);
  dlg._setShowTools(false);
  assert.equal(dlg._showEntities, false);
  assert.match(markup(), /Idle timeout/);
  assert.doesNotMatch(markup(), /vp-show-entities/);
  dlg._stopSession();
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
  // One frame holds the screen and, below it, the hardware buttons.
  assert.doesNotMatch(markup, /vp-device/);
  assert.ok(markup.indexOf('class="vp-bezel"') < markup.indexOf('vp-screen-wrap'));
  assert.ok(markup.indexOf('vp-screen-wrap') < markup.indexOf('vp-hw-buttons'));

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


test('hardware buttons render as part of the frame with relay lights', () => {
  const Dialog = customElements.get('nspanel-dialog-live-preview');
  assert.match(Dialog.styles.map(style => style.cssText || '').join(' '), /#ffcc33/);
  const { dlg } = makeDialog();
  const session = {
    ready: true,
    relays: { left: 'on', right: 'off' },
    pressButton(side) { this.pressed = side; },
  };
  const markup = collect(dlg._renderHardwareButtons(session)).join(' ');
  assert.equal((markup.match(/class="vp-hw"/g) || []).length, 2);
  assert.match(markup, /class="vp-relay-light" data-state=/);
  assert.match(markup, / on /);
  assert.match(markup, / off$/);
  const unknown = collect(dlg._renderHardwareButtons({
    ready: false,
    relays: { left: 'unknown', right: 'unknown' },
  })).join(' ');
  assert.match(unknown, /unknown\s*$/);
  assert.doesNotMatch(markup, /vp-relay-light entity/);

  // A button that switches an entity instead of its relay shows only the entity.
  const entity = collect(dlg._renderHardwareButtons({
    ...session,
    relays: { left: 'off', right: 'off' },
    buttonEntityStates: { left: 'on', right: null },
  })).join(' ');
  assert.equal((entity.match(/class="vp-relay-light/g) || []).length, 2);
  assert.equal((entity.match(/class="vp-relay-light entity"/g) || []).length, 1);
  assert.match(entity, / on off /);
  assert.equal((entity.match(/class="vp-relay-dot"/g) || []).length, 1);
  assert.ok(entity.indexOf('class="vp-relay-light entity"') < entity.indexOf('class="vp-relay-dot"'));
  assert.match(entity, / on off /);

  // Boolean false is still a configured entity state, not the relay state.
  const falseEntity = renderText(dlg._renderHardwareButtons({
    ...session,
    relays: { left: 'on', right: 'off' },
    buttonEntityStates: { left: false, right: null },
  }));
  assert.match(falseEntity, /class="vp-relay-light entity"/);
  assert.match(falseEntity, /class="vp-relay-dot"/);
});

test('idle timeout button keeps its accessible label and hides it on mobile', () => {
  const { dlg } = makeDialog();
  const rendered = dlg._renderIdleButton({ ready: true, idleTimeout() {} });
  const markup = collect(rendered).join(' ');
  const styles = customElements.get('nspanel-dialog-live-preview').styles
    .map(style => style.cssText || '').join(' ');
  assert.match(markup, /aria-label=/);
  assert.match(markup, /mdi:sleep/);
  assert.match(markup, /class="vp-idle-label"/);
  assert.match(markup, /Idle/);
  assert.match(styles, /@media\s*\(max-width:\s*600px\)/);
  assert.match(styles, /\.vp-idle-label\s*\{\s*display:\s*none;/);
});
test('live preview sections use consistent spacing around the toolbar and mode note', () => {
  const styles = customElements.get('nspanel-dialog-live-preview').styles
    .map(style => style.cssText || '').join(' ');
  assert.match(styles, /\.dialog-body\s*\{[^}]*display:\s*flex;[^}]*gap:\s*16px;/);
  assert.match(styles, /\.vp-toolbar\s*\{\s*margin:\s*0;/);
  assert.match(styles, /\.vp-toolbar-actions\s*\{[^}]*gap:\s*8px;/);
  assert.doesNotMatch(styles, /\.vp-status\s*\{[^}]*margin-top:/);
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
  const { dlg } = makeDialog({ open: true, _showTools: true });
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
