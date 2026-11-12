import './dom-shim.mjs';

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
  const workspace = Object.create(Workspace.prototype);
  Object.assign(workspace, {
    entryId: 'entry1',
    device: 'kitchen',
    active: false,
    _session: null,
    _error: '',
    _stageWidth: 0,
    _pointerId: null,
    _resizeObserver: null,
    renderRoot: { querySelector: () => null },
    requestUpdate() {},
    hass: fakeHass(),
  }, props);
  return { dlg: workspace };
}

const flush = () => new Promise(r => setTimeout(r, 0));

test('activating starts a session for the selected device; deactivating stops it', async () => {
  const { dlg } = makeWorkspace();
  dlg.active = true;
  dlg.updated(new Map([['active', false]]));
  await flush();
  assert.equal(dlg.hass.subscriptions.length, 1);
  assert.deepEqual(dlg.hass.subscriptions[0].message, {
    type: 'nspanel_haui/virtual_panel/subscribe',
    entry_id: 'entry1',
    device: 'kitchen',
  });
  // A reused virtual app starts over on its home panel once it is attached.
  assert.equal(dlg._session._openHome, true);

  dlg.active = false;
  dlg.updated(new Map([['active', true]]));
  await flush();
  assert.equal(dlg._session, null);
  assert.equal(dlg.hass.unsubscribed, 1);
});

test('switching device while open restarts the session', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg.device = 'office';
  dlg.updated(new Map([['device', 'kitchen']]));
  await flush();
  assert.equal(dlg.hass.unsubscribed, 1);
  assert.equal(dlg.hass.subscriptions.at(-1).message.device, 'office');
});

test('an active workspace renders only the stage: no note, status row or page controls', async () => {
  const { dlg } = makeWorkspace();
  assert.equal(collect(dlg.render()).length, 0);
  dlg.active = true;
  dlg.updated(new Map([['active', false]]));
  await flush();
  const markup = renderText(dlg.render());
  assert.match(markup, /Starting the live preview/);
  assert.match(markup, /haui-preview-stage/);
  assert.doesNotMatch(markup, /vp-mode-note|vp-status|Simulated mode/);
  assert.doesNotMatch(markup, /view-toggle-group|vp-idle-button|vp-more/);
});

test('workspace renders the real stage without dialog chrome', () => {
  const { dlg } = makeWorkspace({ active: true });
  const markup = renderText(dlg.render());
  assert.match(markup, /vp-workspace/);
  assert.match(markup, /haui-preview-stage/);
  assert.doesNotMatch(markup, /<ha-dialog[ >]/);
});

test('the entity hover follows the Show entities switch', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg._hover = { entityId: 'light.lamp', x: 1, y: 1, width: 10, height: 10 };
  dlg.updated(new Map([['showEntities', false]]));
  assert.equal(dlg._hover, null);
  dlg._hover = { entityId: 'light.lamp', x: 1, y: 1, width: 10, height: 10 };
  dlg.showEntities = true;
  dlg.updated(new Map([['showEntities', true]]));
  assert.ok(dlg._hover);
  dlg._stopSession();
});

test('the workspace resets the sandbox or the interaction timer on request', async () => {
  const { dlg } = makeWorkspace();
  let resets = 0;
  dlg._session = { resetSandbox: async () => { resets++; } };
  await dlg.resetSandbox();
  assert.equal(resets, 1);

  let timerResets = 0;
  dlg._session = { resetInteractionTimer: async () => { timerResets++; } };
  await dlg.resetInteractionTimer();
  assert.equal(timerResets, 1);

  dlg._session = { resetSandbox: async () => { throw new Error('offline'); } };
  await dlg.resetSandbox();
  assert.equal(dlg._error, 'offline');
});

test('the workspace follows the mode the Device header reports', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();
  assert.equal(dlg._session.live, false);

  dlg.setLive(true);
  await flush();
  assert.equal(dlg.hass.calls.length, 0);
  assert.equal(dlg.hass.unsubscribed, 1);
  assert.equal(dlg.hass.subscriptions.at(-1).message.type, 'nspanel_haui/live_panel/subscribe');
  dlg._session._onMessage({
    type: 'physical',
    display_state: 'on',
    connected: true,
    idle: false,
  });
  // The connection state belongs to the side card, not to the stage.
  assert.doesNotMatch(renderText(dlg.render()), /Connected|lan-connect/);

  dlg.setLive(false);
  await flush();
  assert.equal(dlg.hass.calls.length, 0);
  assert.equal(dlg.hass.unsubscribed, 2);
  assert.equal(dlg.hass.subscriptions.at(-1).message.type, 'nspanel_haui/virtual_panel/subscribe');
  assert.equal(dlg._session._openHome, true);
  dlg._stopSession();
});

test('a mode property change starts the session for that mode', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg.mode = 'live';
  dlg.updated(new Map([['mode', 'simulated']]));
  await flush();
  assert.equal(dlg._session.live, true);
  dlg._stopSession();
});

test('switching device in Live mode keeps the Live session', async () => {
  const { dlg } = makeWorkspace({ active: true, mode: 'live' });
  dlg.updated(new Map([['active', false]]));
  await flush();
  assert.equal(dlg._session.live, true);
  dlg.device = 'hall';
  dlg.updated(new Map([['device', 'kitchen']]));
  await flush();
  assert.equal(dlg._session.device, 'hall');
  assert.equal(dlg._session.live, true);
  dlg._stopSession();
});

test('switching to Live drops the simulated states before leaving the sandbox', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();
  Object.assign(dlg._session, { sessionId: 'sandbox', sandboxChanged: true });
  const unsubscribedAtCall = [];
  const callWS = dlg.hass.callWS;
  dlg.hass.callWS = message => {
    unsubscribedAtCall.push(dlg.hass.unsubscribed);
    return callWS(message);
  };

  dlg.setLive(true);
  await flush();

  assert.deepEqual(dlg.hass.calls, [{
    type: 'nspanel_haui/virtual_panel/reset_sandbox',
    session_id: 'sandbox',
  }]);
  // Sent while the sandbox was still subscribed, so the hub knows its session.
  assert.deepEqual(unsubscribedAtCall, [0]);
  assert.equal(dlg.hass.unsubscribed, 1);
  assert.equal(dlg.hass.subscriptions.at(-1).message.type, 'nspanel_haui/live_panel/subscribe');
  dlg._stopSession();
});

test('deactivating immediately after switching modes stops the replacement session', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();

  dlg.setLive(true);
  const liveSubscription = dlg.hass.subscriptions.at(-1);
  dlg.active = false;
  dlg.updated(new Map([['active', true]]));
  dlg.setLive(true);
  await flush();

  assert.equal(liveSubscription.message.type, 'nspanel_haui/live_panel/subscribe');
  assert.equal(dlg._session, null);
  assert.equal(dlg.hass.subscriptions.length, 2);
  assert.equal(dlg.hass.unsubscribed, 2);
});

test('the Diagnostics card reset follows the session mode; the stage has no tools', async () => {
  const resets = [];
  const { dlg } = makeWorkspace({
    active: true,
    _session: {
      ready: true, live: false, canInteract: true,
      resetSandbox: async () => { resets.push('sandbox'); },
      resetInteractionTimer: async () => { resets.push('timer'); },
    },
    _renderScreen: () => '',
  });
  assert.doesNotMatch(renderText(dlg.render()), /Reset sandbox|Redraw/);
  await dlg.resetSession();
  dlg._session.live = true;
  await dlg.resetSession();
  assert.deepEqual(resets, ['sandbox', 'timer']);
});

test('a started session renders the screen and maps pointer input to touches', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.updated(new Map([['active', false]]));
  await flush();
  const session = dlg._session;
  session._loadIconMap = async () => ({});
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
  // The app may be the one a previous preview left behind: start it over.
  assert.deepEqual(dlg.hass.calls, [{
    type: 'nspanel_haui/virtual_panel/home',
    session_id: 's1',
  }]);
  dlg.hass.calls.length = 0;
  dlg.hass.subscriptions[0].callback({ type: 'page', page: 9 });

  const markup = collect(dlg.render()).join(' ');
  assert.match(markup, /vp-screen-wrap/);
  assert.doesNotMatch(markup, /Starting the live preview/);
  // One frame holds the screen and, below it, the hardware buttons.
  assert.doesNotMatch(markup, /vp-device/);
  assert.ok(markup.indexOf('haui-preview-bezel') < markup.indexOf('vp-screen-wrap'));
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
  const Dialog = customElements.get('nspanel-preview-workspace');
  assert.match(Dialog.styles.map(style => style.cssText || '').join(' '), /#ffcc33/);
  const { dlg } = makeWorkspace();
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

test('the workspace reports the idle state the header shows', async () => {
  const { dlg } = makeWorkspace({ active: true });
  const events = [];
  dlg.dispatchEvent = (event) => events.push(event.detail);
  dlg.updated(new Map([['active', false]]));
  await flush();
  assert.equal(events.at(-1).idle, false);
  dlg._session.idle = true;
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, true);
  dlg._session.idle = false;
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, false);
  // The Diagnostics card offers Reset sandbox only while a simulated state exists.
  assert.equal(events.at(-1).sandboxChanged, false);
  dlg._session.sandboxChanged = true;
  dlg.updated(new Map());
  assert.equal(events.at(-1).sandboxChanged, true);
  dlg._stopSession();
});

test('the header Idle control reaches the running session', () => {
  const { dlg } = makeWorkspace();
  const calls = [];
  dlg._session = { idleTimeout: () => calls.push('idle') };
  dlg.idleTimeout();
  assert.deepEqual(calls, ['idle']);
  dlg._session = null;
  dlg.idleTimeout();
});

test('a panel opens in the simulated session only', () => {
  const { dlg } = makeWorkspace();
  const calls = [];
  const openPanel = (key, idle) => calls.push([key, idle]);
  dlg._session = { live: false, openPanel };
  dlg.openPanel('sleep', true);
  dlg._session = { live: true, openPanel };
  dlg.openPanel('grid_0');
  dlg._session = null;
  dlg.openPanel('grid_0');
  assert.deepEqual(calls, [['sleep', true]]);
});

test('the preview stage fills the workspace card and centres the device', () => {
  const styles = customElements.get('nspanel-preview-workspace').styles
    .map(style => style.cssText || '').join(' ');
  const stage = /\.haui-preview-stage\s*\{([^}]*)\}/.exec(styles)[1];
  assert.match(stage, /place-items:\s*center;/);
  assert.match(stage, /padding:\s*40px;/);
  assert.match(stage, /background:\s*var\(--haui-screen\);/);
  assert.doesNotMatch(stage, /border-radius/);
  assert.doesNotMatch(styles, /\.vp-status\s*\{[^}]*margin-top:/);
});

test('sounds and errors of a running preview go out as notices, not onto the stage', async () => {
  const notices = [];
  const { dlg } = makeWorkspace({ dispatchEvent: (event) => notices.push([event.type, event.detail]) });
  dlg._onAction({ name: 'play_sound', value: 'notification' });
  assert.deepEqual(notices, [['preview-notice', { message: 'Sound: notification', type: 'info' }]]);

  // Without a screen the stage shows the error itself.
  dlg._session = { ready: false, resetSandbox: async () => { throw new Error('offline'); } };
  await dlg.resetSandbox();
  assert.equal(notices.length, 1);
  assert.equal(dlg._error, 'offline');

  dlg._session.ready = true;
  await dlg.resetSandbox();
  assert.deepEqual(notices[1], ['preview-notice', { message: 'Live preview error: offline', type: 'error' }]);
});



function renderEditDialog(type, data = {}, inline = false) {
  const Edit = customElements.get('nspanel-panel-editor');
  const dlg = Object.create(Edit.prototype);
  const panel = { index: 0, data: { type, key: `${type}_0`, ...data } };
  Object.assign(dlg, {
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
  const dlg = Object.create(Edit.prototype);
  const fields = { 'fld-key': data.key || '', 'fld-title': data.title || '' };
  Object.assign(dlg, {
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
    requestUpdate() {},
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
  assert.match(markup, /haui-field-error/);
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

test('the reported state follows the session idle flag', async () => {
  const { dlg } = makeWorkspace({ active: true });
  const events = [];
  dlg.dispatchEvent = (event) => events.push(event.detail);
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg._session.idle = true;
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, true);
  dlg._session.idle = false;
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, false);
  dlg._stopSession();
});

function tooltipStyle(dlg) {
  return dlg._renderTooltip().values.slice(0, 2);
}

test('the reported state follows physical idle-state events', async () => {
  const { dlg } = makeWorkspace({ active: true });
  const events = [];
  dlg.dispatchEvent = (event) => events.push(event.detail);
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg.setLive(true);
  await flush();
  assert.equal(events.at(-1).idle, false);
  dlg._session._onMessage({
    type: 'physical',
    idle: true,
    display_state: 'off',
    connected: true,
  });
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, true);
  dlg._stopSession();
});

test('hovering a linked widget shows its entity; leaving or pressing hides it', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.hass.states = { 'light.lamp': { attributes: { friendly_name: 'Lamp' } } };
  dlg.updated(new Map([['active', false]]));
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
  dlg.showEntities = true;

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
  dlg.showEntities = false;
  dlg.updated(new Map([['showEntities', false]]));
  assert.equal(dlg._hover, null);
  dlg._stopSession();
});

test('near the right or bottom edge the tooltip flips to the cursor\'s other side', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg._hover = { entityId: 'light.lamp', x: 800, y: 600, width: 900, height: 640 };
  assert.deepEqual(tooltipStyle(dlg), ['right:114px;', 'bottom:54px;']);
  dlg._hover = { entityId: 'light.lamp', x: 800, y: 100, width: 900, height: 640 };
  assert.deepEqual(tooltipStyle(dlg), ['right:114px;', 'top:114px;']);
});
