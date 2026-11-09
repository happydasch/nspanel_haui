import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { LivePanelSession } from '../../custom_components/nspanel_haui/frontend/virtual/live-panel-session.js';
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
    // Resolved by the test when set: the subscription is still pending.
    subscribeGate: null,
    connection: {
      async subscribeMessage(callback, message) {
        hass.subscribed = { callback, message };
        if (hass.subscribeGate) await hass.subscribeGate;
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

async function started({ Session = VirtualPanelSession, ...opts } = {}) {
  const hass = fakeHass();
  let resolveLayout;
  const layoutLoaded = new Promise(r => { resolveLayout = r; });
  const loaded = [];
  const session = new Session(hass, {
    entryId: 'entry1',
    device: 'kitchen',
    scheduler: { every: () => 0, cancel() {} },
    loadLayout: async o => { loaded.push(o); await layoutLoaded; return load(o); },
    loadIconMap: async () => ({ '': 'lightbulb' }),
    onError: msg => { throw new Error(msg); },
    ...opts,
  });
  await session.start();
  const push = m => hass.subscribed.callback(m);
  return { hass, session, push, loaded, resolveLayout };
}

async function connectedLive(opts = {}) {
  const result = await started({ Session: LivePanelSession, ...opts });
  result.push({ type: 'started', session_id: 'live', portrait: false });
  result.push({ type: 'physical', connected: true, idle: false, display_state: 'on' });
  result.resolveLayout();
  await flush();
  return result;
}

const flush = () => new Promise(r => setTimeout(r, 0));

test('subscribes for the device and loads the layout of its orientation', async () => {
  const { hass, session, push, loaded, resolveLayout } = await started();
  assert.deepEqual(hass.subscribed.message, {
    type: 'nspanel_haui/virtual_panel/subscribe',
    entry_id: 'entry1',
    device: 'kitchen',
  });
  push({ type: 'started', session_id: 'abc', portrait: true });
  resolveLayout();
  await flush();
  assert.deepEqual(loaded, ['portrait']);
  assert.equal(session.ready, true);
  assert.equal(session.live, false);
  assert.equal(session.display.layout.orientation, 'portrait');
  assert.equal(session.iconName(''), 'lightbulb');
});

test('a live session subscribes to the live panel', async () => {
  const { hass, session } = await started({ Session: LivePanelSession });
  assert.deepEqual(hass.subscribed.message, {
    type: 'nspanel_haui/live_panel/subscribe',
    entry_id: 'entry1',
    device: 'kitchen',
  });
  assert.equal(session.live, true);
});

test('a session stopped while it subscribes closes the subscription', async () => {
  const hass = fakeHass();
  let open;
  hass.subscribeGate = new Promise(r => { open = r; });
  const session = new VirtualPanelSession(hass, { entryId: 'entry1', device: 'kitchen' });
  const starting = session.start();
  await session.stop();
  open();
  await starting;
  assert.equal(hass.unsubscribed, true);
});

test('a sandbox session opens home when asked to during a mode switch', async () => {
  const { hass, session, push, resolveLayout } = await started({
    Session: VirtualPanelSession,
    openHome: true,
  });
  push({ type: 'started', session_id: 'sandbox', portrait: false });
  resolveLayout();
  await flush();
  await session._sendChain;

  assert.deepEqual(hass.calls, [{
    type: 'nspanel_haui/virtual_panel/home',
    session_id: 'sandbox',
  }]);
});

test('reset sandbox clears simulated states through the hub session', async () => {
  const { hass, session, push } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });

  await session.resetSandbox();

  assert.deepEqual(hass.calls, [{
    type: 'nspanel_haui/virtual_panel/reset_sandbox',
    session_id: 'abc',
  }]);
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

test('a reconnect starts again on a fresh display', async () => {
  const { session, push, resolveLayout } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();
  const first = session.display;
  let disposed = false;
  first.dispose = () => { disposed = true; };

  push({ type: 'started', session_id: 'def', portrait: false });
  await flush();

  assert.equal(disposed, true);
  assert.notEqual(session.display, first);
  assert.equal(session.sessionId, 'def');
});

test('a live reconnect drops old page state until the new attach redraws it', async () => {
  const { push, resolveLayout, session } = await started({ Session: LivePanelSession });
  const clockId = Number(Object.entries(load('landscape').pages)
    .find(([, page]) => page.name === 'clock')[0]);
  push({ type: 'started', session_id: 'first', portrait: false });
  push({ type: 'page', page: clockId });
  push({ type: 'commands', commands: ['tTime.txt="07:35"'] });
  resolveLayout();
  await flush();

  const first = session.display;
  let disposed = false;
  first.dispose = () => { disposed = true; };
  assert.equal(first.component('tTime').attrs.txt, '07:35');

  push({ type: 'started', session_id: 'reconnected', portrait: false });
  await flush();

  assert.equal(disposed, true);
  assert.notEqual(session.display, first);
  assert.equal(session.display.page, null);
  assert.equal(session.display.components.size, 0);
});

test('a live page switch updates the rendered simulator page', async () => {
  const { push, resolveLayout, session } = await started({ Session: LivePanelSession });
  push({ type: 'started', session_id: 'live', portrait: false });
  push({ type: 'page', page: 9 });
  push({ type: 'commands', commands: ['vis g1Overlay,1', 'g1Name.txt="Lamp"'] });
  resolveLayout();
  await flush();
  assert.equal(session.display.page.name, 'grid');
  assert.equal(session.display.component('g1Name').attrs.txt, 'Lamp');

  push({ type: 'physical', idle: false, display_state: 'on', connected: true });
  push({ type: 'page', page: 13 });
  push({ type: 'commands', commands: ['vis hBrightness,1', 'hBrightness.val=57'] });

  assert.equal(session.physical.connected, true);
  assert.equal(session.display.page.name, 'light');
  assert.equal(session.display.component('hBrightness').attrs.val, 57);
});

test('a live weather page replays its weather content after the clock page loads', async () => {
  const { push, resolveLayout, session } = await started({ Session: LivePanelSession });
  const weatherId = Number(Object.entries(load('landscape').pages)
    .find(([, page]) => page.name === 'weather')[0]);
  push({ type: 'started', session_id: 'live', portrait: false });
  push({ type: 'physical', idle: false, display_state: 'on', connected: true });
  push({ type: 'page', page: weatherId });
  push({
    type: 'commands',
    commands: [
      'tMainIcon.txt="\\ue596"',
      'tMainIcon.pco=38047',
      'vis tMainIcon,1',
      'tMainText.txt="\\ue50e15°C"',
      'tMainText.pco=65535',
      'vis tMainText,1',
      'tSubText.txt="1003hPa"',
      'tSubText.pco=65535',
      'vis tSubText,1',
      'tTime.txt="07:35"',
      'vis tTime,1',
    ],
  });
  resolveLayout();
  await flush();

  for (const [name, text] of [
    ['tMainIcon', '\\ue596'],
    ['tMainText', '\\ue50e15°C'],
    ['tSubText', '1003hPa'],
  ]) {
    const component = session.display.component(name);
    assert.equal(component.attrs.txt, text);
    assert.equal(component.hidden, false);
  }
});

test('a live attach applies system.vBackground before the page load script', async () => {
  const { push, resolveLayout, session } = await started({ Session: LivePanelSession });
  const clockId = Number(Object.entries(load('landscape').pages)
    .find(([, page]) => page.name === 'clock')[0]);
  push({ type: 'started', session_id: 'live', portrait: false });
  push({ type: 'commands', commands: ['system.vBackground.val=5'] });
  push({ type: 'page', page: clockId });
  resolveLayout();
  await flush();

  assert.equal(session.display.component('clock').attrs.pic, 5);
  assert.equal(session.display.component('tTime').attrs.picc, 5);
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

test('stopping a session ends an active touch without producing a swipe', async () => {
  const { hass, push, session } = await connectedLive();
  push({ type: 'page', page: 9 });
  session.touch.press(10, 200);
  session.touch.move(300, 200);

  await session.stop();
  await session._sendChain;

  const events = hass.calls.map(call => call.name);
  assert.equal(session.touch._touch, null);
  assert.ok(events.includes('esphome.touch_end'));
  assert.equal(events.includes('esphome.gesture'), false);
});

test('live slider drags send the selected value without simulating other display input', async () => {
  const { hass, push, session } = await connectedLive();
  push({ type: 'page', page: 13 });
  push({ type: 'commands', commands: ['vis hBrightness,1', 'hBrightness.val=37'] });

  const component = session.display.component('hBrightness');
  session.touch.press(component.attrs.x + 10, component.attrs.y + component.attrs.h - 1);
  session.touch.move(component.attrs.x + 10, component.attrs.y + 5);
  session.touch.release(component.attrs.x + 10, component.attrs.y + 5);
  await session._sendChain;

  assert.equal(component.attrs.val, 98);
  assert.ok(hass.calls.some(call => call.type === 'nspanel_haui/live_panel/slider'
    && call.page_id === 13 && call.component_id === component.id && call.value === 98));
  assert.ok(hass.calls.some(call => call.type === 'nspanel_haui/live_panel/event'
    && call.name === 'esphome.component' && call.value === '13,13,1'));
  assert.equal(hass.calls.some(call => call.type === 'nspanel_haui/live_panel/event'
    && call.name === 'esphome.component' && call.value === '13,13,0'), false);
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

test('sandbox hardware buttons and idle timeout go to the virtual app', async () => {
  const { hass, push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();

  await session.pressButton('left');
  await session.idleTimeout();

  assert.deepEqual(hass.calls, [
    { type: 'nspanel_haui/virtual_panel/event', session_id: 'abc', name: 'esphome.button_left', value: '1' },
    { type: 'nspanel_haui/virtual_panel/event', session_id: 'abc', name: 'esphome.button_left', value: '0' },
    { type: 'nspanel_haui/virtual_panel/idle', session_id: 'abc' },
  ]);
});

test('live hardware buttons, idle and timer reset go to the panel', async () => {
  const { hass, session } = await connectedLive();

  await session.pressButton('right');
  await session.idleTimeout();
  await session.resetInteractionTimer();

  assert.deepEqual(hass.calls, [
    { type: 'nspanel_haui/live_panel/event', session_id: 'live', name: 'esphome.button_right', value: '1' },
    { type: 'nspanel_haui/live_panel/event', session_id: 'live', name: 'esphome.button_right', value: '0' },
    { type: 'nspanel_haui/live_panel/action', session_id: 'live', action: 'idle' },
    { type: 'nspanel_haui/live_panel/action', session_id: 'live', action: 'reset_interaction_timer' },
  ]);
});

test('a live session sends nothing while the panel is disconnected', async () => {
  const { hass, push, session } = await connectedLive();
  push({ type: 'physical', connected: false, idle: false, display_state: 'on' });

  assert.equal(session.canInteract, false);
  await session.pressButton('left');
  await session.idleTimeout();
  await session.resetInteractionTimer();
  assert.deepEqual(hass.calls, []);
});

test('brightness and action messages update the session state', async () => {
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
  assert.equal(session.brightness, 30);
  assert.equal(session.screenBrightness, 0.3);
  assert.deepEqual(actions, ['set_brightness', 'play_sound']);
  assert.ok(updates.length >= 2);

  push({ type: 'action', name: 'set_brightness', value: '5' });
  assert.equal(session.screenBrightness, 0.15);
  push({ type: 'action', name: 'display_off', value: '' });
  assert.equal(session.displayOff, true);
  push({ type: 'action', name: 'display_on', value: '' });
  assert.equal(session.displayOff, false);
});

test('relay-state messages update the hardware indicators', async () => {
  const updates = [];
  const { push, resolveLayout, session } = await started({ onUpdate: () => updates.push(1) });
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();

  const updateCount = updates.length;
  push({ type: 'relays', left: 'on', right: 'off', entities: { left: 'off', right: null } });

  assert.deepEqual(session.relays, { left: 'on', right: 'off' });
  assert.deepEqual(session.buttonEntityStates, { left: 'off', right: null });
  assert.equal(updates.length, updateCount + 1);
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

test('the panel\'s state updates the live session', async () => {
  const updates = [];
  const { push, session } = await connectedLive({ onUpdate: () => updates.push(1) });
  const before = updates.length;

  push({ type: 'physical', idle: true, display_state: 'off', connected: true });

  assert.deepEqual(session.physical, { display_state: 'off', connected: true });
  assert.equal(session.idle, true);
  assert.equal(session.displayOff, true);
  assert.equal(session.screenBrightness, 0);
  assert.equal(updates.length, before + 1);
});

test('entity maps are kept for the hover tooltip', async () => {
  const { push, resolveLayout, session } = await started();
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();

  push({ type: 'entities', map: { g1Overlay: 'light.lamp' } });

  assert.deepEqual(session.entityMap, { g1Overlay: 'light.lamp' });
});

test('sandbox state tracks whether simulated entity changes can be reset', async () => {
  const updates = [];
  const { push, session, resolveLayout } = await started({ onUpdate: () => updates.push(1) });
  push({ type: 'started', session_id: 'abc', portrait: false });
  resolveLayout();
  await flush();
  const updatesBeforeSandboxChange = updates.length;
  assert.equal(session.sandboxChanged, false);
  push({ type: 'sandbox', changed: true });
  assert.equal(session.sandboxChanged, true);
  assert.equal(updates.length, updatesBeforeSandboxChange + 1);
  push({ type: 'sandbox', changed: false });
  assert.equal(session.sandboxChanged, false);
  assert.equal(updates.length, updatesBeforeSandboxChange + 2);
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
