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
