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
