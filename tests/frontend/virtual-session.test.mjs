import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { VirtualPanelSession } from '../../custom_components/nspanel_haui/frontend/virtual/virtual-panel-session.js';

const load = o => JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/layout_${o}.json`, import.meta.url),
  'utf8',
));

function fakeHass() {
  const hass = {
    calls: [],
    subscribed: null,
    unsubscribed: false,
    async fetchWithAuth(path) {
      assert.equal(path, '/api/nspanel_haui/icon_chars');
      return { ok: true, json: async () => ({ '': 'lightbulb' }) };
    },
    connection: {
      async subscribeMessage(callback, message) {
        hass.subscribed = { callback, message };
        return async () => { hass.unsubscribed = true; };
      },
    },
    async callWS(message) {
      hass.calls.push(message);
      return null;
    },
  };
  return hass;
}

async function started(opts = {}) {
  const hass = fakeHass();
  let resolveLayout;
  const layoutLoaded = new Promise(r => { resolveLayout = r; });
  const loaded = [];
  const session = new VirtualPanelSession(hass, {
    entryId: 'entry1',
    device: 'kitchen',
    scheduler: { every: () => 0, cancel() {} },
    loadLayout: async o => { loaded.push(o); await layoutLoaded; return load(o); },
    onError: msg => { throw new Error(msg); },
    ...opts,
  });
  await session.start();
  const push = m => hass.subscribed.callback(m);
  return { hass, session, push, loaded, resolveLayout };
}

const flush = () => new Promise(r => setTimeout(r, 0));

test('subscribes for the device and loads the layout of its orientation', async () => {
  const { hass, session, push, loaded, resolveLayout } = await started({ live: true });
  assert.deepEqual(hass.subscribed.message, {
    type: 'nspanel_haui/virtual_panel/subscribe',
    entry_id: 'entry1',
    device: 'kitchen',
    live: true,
    protocol_version: 2,
  });
  push({ type: 'started', session_id: 'abc', portrait: true, live: true });
  resolveLayout();
  await flush();
  assert.deepEqual(loaded, ['portrait']);
  assert.equal(session.ready, true);
  assert.equal(session.display.layout.orientation, 'portrait');
  assert.equal(session.iconName(''), 'lightbulb');
});

test('output that arrives before the layout is replayed in order', async () => {
  const { session, push, resolveLayout } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  push({ type: 'page', page: 9 });
  push({ type: 'commands', commands: ['g1Name.txt="Lamp"'] });
  assert.equal(session.ready, false);
  resolveLayout();
  await flush();
  assert.equal(session.display.page.name, 'grid');
  assert.equal(session.display.component('g1Name').attrs.txt, 'Lamp');
});

test('touches go to the hub as device events, in order', async () => {
  const { hass, session, push, resolveLayout } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  push({ type: 'page', page: 9 });
  push({ type: 'commands', commands: ['vis g1Overlay,1'] });
  resolveLayout();
  await flush();

  session.touch.press(40, 70);
  await session.touch.release(40, 70);
  await session._sendChain;

  assert.deepEqual(
    hass.calls.map(c => [c.type, c.session_id, c.name, c.value]),
    [
      ['nspanel_haui/virtual_panel/event', 'abc', 'esphome.component', '9,11,1'],
      ['nspanel_haui/virtual_panel/event', 'abc', 'esphome.touch_start', '1'],
      ['nspanel_haui/virtual_panel/event', 'abc', 'esphome.touch_start', ''],
      ['nspanel_haui/virtual_panel/event', 'abc', 'esphome.component', '9,11,0'],
      ['nspanel_haui/virtual_panel/event', 'abc', 'esphome.touch_end', '40,70,40,70'],
    ],
  );
});

test('a hub read request is answered with the widget value', async () => {
  const { hass, push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  push({ type: 'page', page: 13 });
  push({ type: 'commands', commands: ['hBrightness.val=37'] });
  push({ type: 'request', kind: 'val', name: 'hBrightness' });
  resolveLayout();
  await flush();
  await session._sendChain;
  assert.deepEqual(hass.calls.at(-1), {
    type: 'nspanel_haui/virtual_panel/event',
    session_id: 'abc',
    name: 'esphome.read_response',
    value: JSON.stringify({ name: 'hBrightness', type: 'number', value: 37 }),
  });
});

test('hardware buttons, idle timeout and live mode', async () => {
  const { hass, push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();

  await session.pressButton('left');
  await session.idleTimeout();
  await session.setLive(true);

  assert.deepEqual(hass.calls.map(c => c.type), [
    'nspanel_haui/virtual_panel/event',
    'nspanel_haui/virtual_panel/event',
    'nspanel_haui/virtual_panel/idle',
    'nspanel_haui/virtual_panel/configure',
  ]);
  assert.deepEqual(hass.calls.slice(0, 2).map(c => c.name), [
    'esphome.button_left', 'esphome.button_left',
  ]);
  assert.deepEqual(hass.calls.slice(0, 2).map(c => c.value), ['1', '0']);
  assert.equal(hass.calls[2].session_id, 'abc');
  assert.equal(hass.calls[3].live, true);
  assert.equal(session.live, true);
});

test('resetting the sandbox does not change the current preview mode', async () => {
  const { hass, push, resolveLayout, session } = await started({ live: true });
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();

  await session.resetSandbox();

  assert.equal(session.live, true);
  assert.deepEqual(hass.calls.at(-1), {
    type: 'nspanel_haui/virtual_panel/configure',
    session_id: 'abc',
    reset_sandbox: true,
  });
});

test('brightness and sandbox messages update the session state', async () => {
  const updates = [];
  const actions = [];
  const { push, resolveLayout, session } = await started({
    onUpdate: () => updates.push(1),
    onAction: a => actions.push(a.name),
  });
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();
  push({ type: 'action', name: 'set_brightness', value: '30' });
  push({ type: 'action', name: 'play_sound', value: 'notification' });
  push({ type: 'sandbox', entities: ['light.lamp'] });
  assert.equal(session.brightness, 30);
  assert.deepEqual(session.sandboxEntities, ['light.lamp']);
  assert.deepEqual(actions, ['set_brightness', 'play_sound']);
  assert.ok(updates.length >= 3);
});

test('stop unsubscribes and ignores later output', async () => {
  const { hass, push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();
  await session.stop();
  assert.equal(hass.unsubscribed, true);
  push({ type: 'page', page: 9 });
  assert.notEqual(session.display.page?.name, 'grid');
  await session.sendEvent('esphome.touch_start', '');
  assert.deepEqual(hass.calls, []);
});

test('entity-map metadata is accepted by the current protocol', async () => {
  const { push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();

  push({ type: 'entities', map: { g1Overlay: 'light.lamp' } });

  assert.deepEqual(session.entityMap, { g1Overlay: 'light.lamp' });
});

test('hub errors are reported', async () => {
  const errors = [];
  const { push } = await started({ onError: msg => errors.push(msg) });
  push({ type: 'error', message: 'start_failed' });
  assert.deepEqual(errors, ['start_failed']);
});

test('the hub\'s idle page state is tracked', async () => {
  const { push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();
  assert.equal(session.idle, false);
  push({ type: 'idle', active: true });
  assert.equal(session.idle, true);
  push({ type: 'idle', active: false });
  assert.equal(session.idle, false);
});
