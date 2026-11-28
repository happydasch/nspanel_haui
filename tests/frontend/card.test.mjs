import './support/browser.mjs';

import { mock, test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  CardHomeSession,
  CardInfoSession,
  CardLiveSession,
} from '../../custom_components/nspanel_haui/frontend/virtual/card-sessions.js';
import {
  RESUBSCRIBE_DELAY_MS,
  findDevice,
  normalizeConfig,
} from '../../custom_components/nspanel_haui/frontend/card/card.js';
import '../../custom_components/nspanel_haui/frontend/card/card-editor.js';
import { loadIconMap, loadLayout } from '../../custom_components/nspanel_haui/frontend/virtual/assets.js';
import { flush } from './support/render.mjs';
import { pageId } from './support/fixtures.mjs';
import { byClass, byRole, byText } from './support/queries.mjs';

const asset = (name) => JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/${name}`, import.meta.url),
  'utf8',
));

// The assets are memoised: load them once from the files, as fetch would.
loadLayout('landscape', () => asset('layout_landscape.json'));
loadIconMap(() => asset('icon_map.json'));

const GRID_PAGE_ID = pageId('grid');
const KITCHEN = { entry_id: 'entry1', name: 'kitchen', device_id: 'ha-kitchen', enabled: true };
const HALL = { entry_id: 'entry1', name: 'hall', device_id: 'ha-hall', enabled: true };
const ATTIC = { entry_id: 'entry1', name: 'attic', device_id: 'ha-attic', enabled: false };

function fakeHass({ devices = [KITCHEN], subscribeError = null, devicesError = null } = {}) {
  const hass = {
    language: 'en',
    subscriptions: [],
    calls: [],
    listeners: {},
    connection: {
      async sendMessagePromise(message) {
        assert.equal(message.type, 'nspanel_haui/card/devices');
        if (devicesError) throw devicesError;
        return devices;
      },
      async subscribeMessage(callback, message) {
        if (subscribeError) throw subscribeError;
        const subscription = { callback, message, closed: false };
        hass.subscriptions.push(subscription);
        return async () => { subscription.closed = true; };
      },
      addEventListener(type, listener) { hass.listeners[type] = listener; },
      removeEventListener(type, listener) {
        if (hass.listeners[type] === listener) delete hass.listeners[type];
      },
    },
    async callWS(message) { hass.calls.push(message); },
    async fetchWithAuth() { return { ok: true, status: 200, json: async () => ({}) }; },
  };
  return hass;
}

async function until(condition, rounds = 50) {
  for (let i = 0; i < rounds && !condition(); i += 1) await flush(1);
  assert.ok(condition(), 'condition not met');
}

async function mountCard(config, hass = fakeHass()) {
  const card = document.createElement('nspanel-haui-card');
  card.setConfig(config);
  card.hass = hass;
  document.body.append(card);
  await flush();
  return { card, hass };
}

/** The hub draws the grid home panel with its title. */
function drawHome(subscription, title = 'Rooms') {
  subscription.callback({ type: 'started', portrait: false });
  subscription.callback({ type: 'page', page: GRID_PAGE_ID });
  subscription.callback({ type: 'commands', commands: [`tTitle.txt="${title}"`] });
}

/** A live panel: the hub mirrors the panel's own page. */
function drawLive(subscription) {
  subscription.callback({ type: 'started', session_id: 'abc', portrait: false });
  subscription.callback({ type: 'page', page: GRID_PAGE_ID });
}

/** The panel itself, as the hub reports it; every mode reports it. */
function drawPanel(subscription, { connected = true, display = 'on', queued = 0, firmware = '1.2.3', tft = '1.0.4' } = {}) {
  subscription.callback({
    type: 'physical',
    idle: false,
    display_state: display,
    connected,
    firmware,
    tft,
  });
  subscription.callback({ type: 'notifications', count: queued });
}

const statusOf = (card) => byClass(card.shadowRoot, 'haui-card-status');
const fleetCard = (card, deviceId) => card.shadowRoot.querySelector(`[data-device-id="${deviceId}"]`);
const screenOf = (card) => byRole(card.shadowRoot, 'img', { name: 'Screen of kitchen' });
// The screens of a fleet; a status dot is a role="img" too.
const screens = (card) => [...card.shadowRoot.querySelectorAll('[role="img"]')]
  .filter((element) => (element.getAttribute('aria-label') || '').startsWith('Screen of '));
const screen = (card) => screens(card)[0] ?? null;
const screenWidth = (card, index = 0) => Number(
  /--vp-preview-width:\s*([\d.]+)px/.exec(
    card.shadowRoot.querySelectorAll('.haui-preview-sim')[index].getAttribute('style'),
  )[1],
);

test('the card registers itself for the dashboard card picker', () => {
  const entry = window.customCards.find((card) => card.type === 'nspanel-haui-card');
  assert.equal(entry.name, 'NSPanel HAUI');
  assert.equal(entry.preview, true);
});

test('an unknown mode or display mode is a configuration error', () => {
  const card = document.createElement('nspanel-haui-card');
  assert.throws(() => card.setConfig({ device: 'kitchen', mode: 'sandbox' }), /sandbox/);
  assert.throws(() => card.setConfig({ mode: 'device', device: 'kitchen', display_mode: 'wide' }), /wide/);
});
test('legacy layout names normalize to shared display modes', () => {
  assert.equal(normalizeConfig({ mode: 'device', layout: 'preview' }).display_mode, 'big');
  assert.equal(normalizeConfig({ mode: 'device', layout: 'row' }).display_mode, 'small');
  assert.equal(normalizeConfig({ mode: 'fleet', layout: 'info' }).display_mode, 'status');
  assert.equal(normalizeConfig({ mode: 'overview', screen: false }).display_mode, 'big');
});


test('a new card is the fleet of every panel of the hub', async () => {
  const hass = fakeHass({ devices: [KITCHEN, HALL] });
  const card = document.createElement('nspanel-haui-card');
  const config = await card.constructor.getStubConfig(hass);
  card.setConfig(config);
  card.hass = hass;
  document.body.append(card);

  await until(() => hass.subscriptions.length === 2);
  assert.deepEqual(card.getGridOptions(), { columns: 'full', rows: 'auto', min_columns: 6 });
  assert.ok(byClass(card.shadowRoot, 'haui-card-fleet'));
  assert.ok(fleetCard(card, 'ha-kitchen'));
  assert.ok(fleetCard(card, 'ha-hall'));
  card.remove();
});

test('a device card without a device asks for one', async () => {
  const { card, hass } = await mountCard({ mode: 'device' });
  assert.ok(byText(card.shadowRoot, 'Choose a device in the card settings'));
  assert.deepEqual(hass.subscriptions, []);
  card.remove();
});

test('a card names a device the hub does not have', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'garage' });
  await until(() => byText(card.shadowRoot, 'Device not found: garage'));
  assert.deepEqual(hass.subscriptions, []);
  card.remove();
});

test('a card finds its device by its Home Assistant device id after a rename', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'old-name', device_id: 'ha-kitchen' });
  await until(() => hass.subscriptions.length === 1);
  assert.deepEqual(hass.subscriptions[0].message, {
    type: 'nspanel_haui/card/home/subscribe',
    device_id: 'ha-kitchen',
  });
  card.remove();
});

test('a device card shows the home panel the hub streams for it', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  assert.deepEqual(hass.subscriptions[0].message, {
    type: 'nspanel_haui/card/home/subscribe',
    device_id: 'ha-kitchen',
  });

  drawHome(hass.subscriptions[0]);

  await until(() => screenOf(card));
  assert.ok(byText(screenOf(card), 'Rooms'));
  card.remove();
  await flush();
  assert.equal(hass.subscriptions[0].closed, true);
});

test('a device card reports the panel itself, as the hub sends it', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  const [home] = hass.subscriptions;
  drawHome(home);

  await until(() => statusOf(card));
  assert.ok(byText(statusOf(card), 'Unknown'), 'nothing is invented before the hub reports');

  drawPanel(home, { display: 'dim', queued: 2 });

  await until(() => byText(statusOf(card), 'Dimmed'));
  // The connection is the dot's tone and its name, as on a device card.
  assert.ok(byRole(statusOf(card), 'img', { name: 'Connected' }));
  assert.ok(byText(statusOf(card), '1.2.3'));
  assert.ok(byText(statusOf(card), '1.0.4'));
  assert.ok(byText(statusOf(card), '2'));
  assert.ok(!byText(card.shadowRoot, 'Disconnected'));
  card.remove();
});

test('a device card dims and marks the panel when it goes offline, keeping its screen', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  const [home] = hass.subscriptions;
  drawHome(home);
  drawPanel(home);
  await until(() => screenOf(card));

  drawPanel(home, { connected: false });

  await until(() => byText(card.shadowRoot, 'Disconnected'));
  assert.ok(screenOf(card), 'the hub still renders the home panel');
  assert.ok(byRole(statusOf(card), 'img', { name: 'Offline' }));
  card.remove();
});

test('a device card with live mirrors the real panel', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen', live: true });
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  assert.equal(live.message.type, 'nspanel_haui/card/live/subscribe');

  drawLive(live);
  await until(() => screenOf(card));
  assert.ok(!byText(card.shadowRoot, 'Disconnected'));

  live.callback({ type: 'physical', connected: false, idle: false, display_state: 'on' });

  await until(() => byText(card.shadowRoot, 'Disconnected'));
  assert.ok(screenOf(card));
  card.remove();
});

test('each compact fleet screen scales when its preview column narrows', async () => {
  const slots = new Set();
  let resize;
  globalThis.ResizeObserver = class {
    constructor(callback) { resize = callback; }
    observe(slot) { slots.add(slot); }
    unobserve(slot) { slots.delete(slot); }
    disconnect() { slots.clear(); }
  };
  let card;
  try {
    const hass = fakeHass({ devices: [KITCHEN, HALL] });
    ({ card } = await mountCard({ mode: 'fleet', display_mode: 'small' }, hass));
    await until(() => hass.subscriptions.length === 2);
    for (const subscription of hass.subscriptions) {
      drawHome(subscription);
      drawPanel(subscription);
    }
    await until(() => slots.size === 2);
    const [first, second] = [...slots];
    const observeWidths = (firstWidth, secondWidth) => resize([
      { target: first, contentRect: { width: firstWidth } },
      { target: second, contentRect: { width: secondWidth } },
    ]);
    observeWidths(144, 144);
    await until(() => screens(card).length === 2);

    const normalWidth = screenWidth(card);
    observeWidths(95, 144);
    await until(() => screenWidth(card) < normalWidth);
    assert.ok(screenWidth(card) < 95, 'the first screen leaves room for its bezel');
    assert.equal(screenWidth(card, 1), normalWidth, 'the other screen does not shrink');

    card.setConfig({ mode: 'fleet', display_mode: 'status' });
    await until(() => slots.size === 0);
    assert.equal(screens(card).length, 0);
  } finally {
    card?.remove();
    delete globalThis.ResizeObserver;
  }
});

test('a device card can show only the panel\'s status, without a screen', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen', display_mode: 'status' });
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  assert.equal(live.message.type, 'nspanel_haui/card/live/subscribe');
  live.callback({ type: 'started', session_id: 'abc', portrait: false });
  // The state arrives without a page: a card without a screen builds none.
  drawPanel(live, { display: 'dim', queued: 1 });

  await until(() => statusOf(card) && byText(statusOf(card), 'Dimmed'));
  assert.equal(screenOf(card), null);
  assert.equal(card.shadowRoot.querySelector('.haui-preview-sim'), null, 'no display is built');
  assert.equal(byClass(card.shadowRoot, 'haui-card-queued').textContent.trim(), '1');
  assert.equal(card.getCardSize(), 2);
  card.remove();
});

test('a card can show its screen smaller', async () => {
  const { card: full, hass: fullHass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => fullHass.subscriptions.length === 1);
  drawHome(fullHass.subscriptions[0]);
  await until(() => screenOf(full));

  const { card: small, hass: smallHass } = await mountCard({ mode: 'device', device: 'kitchen', scale: 50 });
  await until(() => smallHass.subscriptions.length === 1);
  drawHome(smallHass.subscriptions[0]);
  await until(() => screenOf(small));

  assert.ok(Math.abs(screenWidth(small) * 2 - screenWidth(full)) < 2, 'half the size it would take');
  assert.ok(small.getCardSize() < full.getCardSize(), 'and a shorter card');
  full.remove();
  small.remove();
});

test('a card keeps a scale within what it can draw', () => {
  const card = document.createElement('nspanel-haui-card');
  card.setConfig({ mode: 'device', device: 'kitchen', scale: 500 });
  assert.equal(card.getCardSize(), 6);
  card.setConfig({ mode: 'device', device: 'kitchen', scale: 1 });
  assert.equal(card.getCardSize(), 1);
});

test('the status area shows hardware button lights beside the panel state', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  const [home] = hass.subscriptions;
  drawHome(home);
  home.callback({
    type: 'buttons',
    left: { relay: 'switch.kitchen_relay_left', entity: null, state: 'on', relay_state: 'on' },
    right: { relay: null, entity: null, state: 'off', relay_state: 'off' },
  });

  await until(() => card.shadowRoot.querySelector('.haui-card-hardware .haui-card-led[data-state="on"]')
    && card.shadowRoot.querySelector('.haui-card-hardware .haui-card-led[data-state="off"]'));
  const leds = [...card.shadowRoot.querySelectorAll('.haui-card-hardware .haui-card-led')];
  assert.deepEqual(leds.map((led) => led.dataset.state), ['on', 'off']);
  assert.ok(!card.shadowRoot.querySelector('.haui-card-hw'), 'there are no hardware buttons under the screen');
  card.remove();
});

test('a button that switches an entity shows it beside its relay', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  const [home] = hass.subscriptions;
  drawHome(home);
  home.callback({
    type: 'buttons',
    left: {
      relay: 'switch.kitchen_relay_left',
      entity: 'light.lamp',
      state: 'on',
      relay_state: 'off',
    },
    right: { relay: null, entity: null, state: 'unknown', relay_state: 'unknown' },
  });

  await until(() => card.shadowRoot.querySelector('.haui-card-led.is-entity'));
  assert.equal(card.shadowRoot.querySelector('.haui-card-led.is-entity').dataset.state, 'on');
  // The relay keeps its own light: this button switches the lamp.
  assert.equal(card.shadowRoot.querySelector('.haui-card-led-dot').dataset.state, 'off');
  card.remove();
});

test('a fleet card draws every device of the hub, its screen and its state', async () => {
  const hass = fakeHass({ devices: [KITCHEN, HALL] });
  const { card } = await mountCard({ mode: 'fleet' }, hass);
  await until(() => hass.subscriptions.length === 2);
  // Both devices get a screen; a live fleet would ask for the real ones.
  assert.ok(hass.subscriptions.every((subscription) =>
    subscription.message.type === 'nspanel_haui/card/home/subscribe',
  ));

  const kitchen = hass.subscriptions.find((s) => s.message.device_id === 'ha-kitchen');
  const hallway = hass.subscriptions.find((s) => s.message.device_id === 'ha-hall');
  drawHome(kitchen, 'Rooms');
  drawPanel(kitchen, { queued: 2 });
  drawHome(hallway, 'Hall');
  drawPanel(hallway, { connected: false, display: 'off' });

  await until(() => screens(card).length === 2);
  assert.ok(byText(screens(card)[0], 'Rooms'));
  await until(() => byText(card.shadowRoot, '2'));
  await until(() => fleetCard(card, 'ha-kitchen')?.getAttribute('aria-label') === 'kitchen');
  await until(() => fleetCard(card, 'ha-hall')?.getAttribute('aria-label') === 'hall');
  assert.ok(byText(fleetCard(card, 'ha-kitchen'), 'Connected'));
  assert.ok(byText(fleetCard(card, 'ha-hall'), 'Offline'));
  card.remove();
});

test('a disabled device keeps its card: the hub renders its screen', async () => {
  const hass = fakeHass({ devices: [ATTIC] });
  const { card } = await mountCard({ mode: 'fleet' }, hass);
  await until(() => hass.subscriptions.length === 1);

  drawHome(hass.subscriptions[0], 'Attic');

  await until(() => screens(card).length === 1);
  assert.ok(byText(screens(card)[0], 'Attic'), 'the state does not decide the screen');
  // It reports no state of its own, so its card says what it is.
  assert.ok(byText(card.shadowRoot, 'Disabled'));
  assert.ok(!byText(card.shadowRoot, 'Unknown'), 'no state is invented for it');
  card.remove();

  // The same device on its own: a screen, and no state invented for it.
  const alone = fakeHass({ devices: [ATTIC] });
  const { card: device } = await mountCard({ mode: 'device', device: 'attic' }, alone);
  await until(() => alone.subscriptions.length === 1);
  drawHome(alone.subscriptions[0], 'Attic');
  await until(() => screen(device));
  assert.ok(byText(statusOf(device), 'Disabled'));
  assert.ok(!byText(statusOf(device), 'Unknown'));
  device.remove();
});

test('a disabled device reports no state where a state is all a card shows', async () => {
  // `display_mode: status` has no screen, so a disabled device cannot fall back to its render.
  const error = Object.assign(new Error('disabled'), { code: 'disabled' });
  const hass = fakeHass({ devices: [ATTIC], subscribeError: error });
  const { card } = await mountCard({ mode: 'device', device: 'attic', display_mode: 'status' }, hass);

  await until(() => byText(card.shadowRoot, 'The device is disabled in NSPanel HAUI'));
  assert.equal(screen(card), null);
  card.remove();
});

test('a fleet applies the selected display mode consistently to every device', async () => {
  for (const displayMode of ['big', 'small', 'status']) {
    const hass = fakeHass({ devices: [KITCHEN, HALL] });
    const { card } = await mountCard({ mode: 'fleet', display_mode: displayMode }, hass);
    await until(() => hass.subscriptions.length === 2);
    for (const subscription of hass.subscriptions) {
      if (displayMode !== 'status') drawHome(subscription);
      else subscription.callback({ type: 'started', session_id: 'abc', portrait: false });
      drawPanel(subscription);
    }

    await until(() => displayMode === 'status'
      ? card.shadowRoot.querySelectorAll('.haui-card-panel.is-fleet-item').length === 2
      : screens(card).length === 2);
    assert.equal(screens(card).length, displayMode === 'status' ? 0 : 2);
    assert.ok(card.shadowRoot.querySelector(`.haui-card-fleet.is-${displayMode}`));
    assert.equal(card.getGridOptions().columns, displayMode === 'big' ? 'full' : 6);
    card.remove();
  }
});

test('a fleet with live mirrors each device screen without interactive controls', async () => {
  const hass = fakeHass({ devices: [KITCHEN] });
  const { card } = await mountCard({ mode: 'fleet', live: true }, hass);
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  assert.equal(live.message.type, 'nspanel_haui/card/live/subscribe');

  drawLive(live);
  await until(() => screens(card).length === 1);
  assert.ok(!card.shadowRoot.querySelector('.haui-card-back'));
  assert.ok(!byRole(card.shadowRoot, 'button'));
  card.remove();
});

test('a fleet card says why a disabled device has no live screen', async () => {
  // The hub mirrors a running panel; a disabled device has none.
  const error = Object.assign(new Error('disabled'), { code: 'disabled' });
  const hass = fakeHass({ devices: [ATTIC], subscribeError: error });
  const { card } = await mountCard({ mode: 'fleet', live: true }, hass);

  await until(() => byText(card.shadowRoot, 'The device has no live screen'));
  assert.equal(screens(card).length, 0);
  card.remove();
});

test('a card whose device goes away says why instead of keeping its last screen', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  drawHome(hass.subscriptions[0]);
  drawPanel(hass.subscriptions[0]);
  await until(() => screenOf(card));

  // Home Assistant reconnected and the device was removed meanwhile.
  card.hass = fakeHass({ devices: [HALL] });
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    hass.listeners.ready();
    mock.timers.tick(RESUBSCRIBE_DELAY_MS);
  } finally {
    mock.timers.reset();
  }

  await until(() => byText(card.shadowRoot, 'Device not found: kitchen'));
  assert.equal(screenOf(card), null);
  card.remove();
});

test('a card the hub refuses because the device is disabled says so', async () => {
  // The device was disabled between the card's device list and its subscription.
  const error = Object.assign(new Error('disabled'), { code: 'disabled' });
  const { card } = await mountCard(
    { mode: 'device', device: 'kitchen', live: true },
    fakeHass({ subscribeError: error }),
  );

  await until(() => byText(card.shadowRoot, 'The device has no live screen'));
  card.remove();
});

test('a card with a title shows it as its heading', async () => {
  const { card } = await mountCard({ mode: 'device', device: 'kitchen', title: 'Hallway' });
  await until(() => byClass(card.shadowRoot, 'haui-card-title'));
  assert.ok(byText(card.shadowRoot, 'Hallway'));
  card.remove();
});

test('a card the hub ended subscribes again and keeps its screen meanwhile', async () => {
  const { card, hass } = await mountCard({ mode: 'device', device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  drawHome(hass.subscriptions[0]);
  await until(() => screenOf(card));

  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    hass.subscriptions[0].callback({ type: 'ended' });
    mock.timers.tick(RESUBSCRIBE_DELAY_MS);
  } finally {
    mock.timers.reset();
  }

  await until(() => hass.subscriptions.length === 2);
  assert.equal(hass.subscriptions[0].closed, true);
  assert.deepEqual(hass.subscriptions[1].message, hass.subscriptions[0].message);
  assert.ok(byText(screenOf(card), 'Rooms'));
  card.remove();
});

test('a card of the first implementation keeps what it showed', async () => {
  const { card: live, hass: liveHass } = await mountCard({ mode: 'live', device: 'kitchen' });
  await until(() => liveHass.subscriptions.length === 1);
  assert.equal(liveHass.subscriptions[0].message.type, 'nspanel_haui/card/live/subscribe');
  live.remove();

  const { card: tile, hass: tileHass } = await mountCard({ mode: 'tile', device: 'kitchen' });
  await until(() => tileHass.subscriptions.length === 1);
  assert.equal(tileHass.subscriptions[0].message.type, 'nspanel_haui/card/live/subscribe');
  drawPanel(tileHass.subscriptions[0], { display: 'dim' });
  await until(() => statusOf(tile) && byText(statusOf(tile), 'Dimmed'));
  assert.equal(tile.shadowRoot.querySelector('.haui-preview-sim'), null, 'a tile keeps no screen');
  tile.remove();

  const { card: hidden, hass: hiddenHass } = await mountCard({ device: 'kitchen', screen: false });
  await until(() => hiddenHass.subscriptions.length === 1);
  assert.equal(hiddenHass.subscriptions[0].message.type, 'nspanel_haui/card/live/subscribe');
  hidden.remove();

  // The first implementation's overview is the fleet, every device included.
  const overviewHass = fakeHass({ devices: [KITCHEN, HALL] });
  const { card: overview } = await mountCard({ mode: 'overview', devices: ['ha-hall'] }, overviewHass);
  await until(() => overviewHass.subscriptions.length === 2);
  assert.ok(fleetCard(overview, 'ha-kitchen'), 'a saved device subset does not limit the fleet');
  overview.remove();
});

test('a device info session keeps the panel state and builds no display', async () => {
  const hass = fakeHass();
  const session = new CardInfoSession(hass, { deviceId: 'ha-kitchen' });
  await session.start();
  assert.deepEqual(hass.subscriptions[0].message, {
    type: 'nspanel_haui/card/live/subscribe',
    device_id: 'ha-kitchen',
  });

  const [subscription] = hass.subscriptions;
  subscription.callback({ type: 'started', session_id: 'abc', portrait: false });
  drawPanel(subscription, { display: 'dim', queued: 3 });

  assert.equal(session.display, null, 'a card without a screen draws nothing');
  assert.equal(session.ready, false);
  assert.equal(session.physical.display_state, 'dim');
  assert.equal(session.notifications, 3);
  await session.stop();
});

test('a card session sends nothing back to the hub', async () => {
  for (const Session of [CardHomeSession, CardLiveSession, CardInfoSession]) {
    const hass = fakeHass();
    const session = new Session(hass, { deviceId: 'ha-kitchen' });
    await session.start();
    assert.deepEqual(hass.subscriptions[0].message, {
      type: `${Session.API}/subscribe`,
      device_id: 'ha-kitchen',
    });
    hass.subscriptions[0].callback({ type: 'started', session_id: 'abc', portrait: false });
    hass.subscriptions[0].callback({ type: 'physical', connected: true, idle: false, display_state: 'on' });
    await until(() => session.ready || Session === CardInfoSession);

    await session.pressButton('left');
    session.sendEvent('esphome.component', '9,12,1');

    assert.equal(session.canInteract, false);
    assert.deepEqual(hass.calls, []);
    await session.stop();
  }
});

test('a start again draws on a fresh display, not on the old one', async () => {
  const hass = fakeHass();
  const session = new CardHomeSession(hass, { entryId: 'entry1', device: 'kitchen' });
  await session.start();
  const [subscription] = hass.subscriptions;
  drawHome(subscription);
  await until(() => session.ready);
  const first = session.display;

  drawHome(subscription, 'Hall');

  await until(() => session.ready && session.display !== first);
  assert.equal(session.display.component('tTitle').attrs.txt, 'Hall');
  assert.equal(first.component('tTitle').attrs.txt, 'Rooms');
  await session.stop();
});

test('the device a card means is its id first, then its name', () => {
  const devices = [KITCHEN, HALL];
  assert.equal(findDevice(devices, { mode: 'device', device: 'hall', device_id: 'ha-kitchen' }).name, 'kitchen');
  assert.equal(findDevice(devices, { mode: 'device', device: 'hall' }).name, 'hall');
  assert.equal(findDevice(devices, { mode: 'device', device: 'renamed', device_id: 'ha-hall' }).name, 'hall');
  assert.equal(findDevice(devices, { mode: 'device', device: 'garage' }), undefined);
});

test('the card editor offers every device, disabled ones marked, and stores the device id', async () => {
  const editor = document.createElement('nspanel-haui-card-editor');
  editor.setConfig({
    type: 'custom:nspanel-haui-card',
    mode: 'device',
    device: 'kitchen',
    display_mode: 'big',
    live: false,
  });
  editor.hass = fakeHass({ devices: [KITCHEN, { ...HALL, enabled: false }] });
  document.body.append(editor);
  await until(() => editor.shadowRoot.querySelector('ha-form'));
  const form = editor.shadowRoot.querySelector('ha-form');
  assert.deepEqual(form.schema.map((field) => field.name), [
    'mode', 'device', 'display_mode', 'live', 'title', 'scale',
  ]);
  const [mode, device, displayMode] = form.schema;
  assert.deepEqual(
    device.selector.select.options.map((option) => option.label),
    ['kitchen', 'hall (disabled)'],
  );
  assert.deepEqual(
    mode.selector.select.options.map((option) => option.value),
    ['fleet', 'device'],
  );
  assert.deepEqual(
    displayMode.selector.select.options.map((option) => option.value),
    ['big', 'small', 'status'],
  );

  const changes = [];
  editor.addEventListener('config-changed', (event) => changes.push(event.detail.config));
  form.dispatchEvent(new CustomEvent('value-changed', { detail: { value: { device: 'hall' } } }));

  assert.deepEqual(changes, [{
    type: 'custom:nspanel-haui-card',
    mode: 'device',
    device: 'hall',
    device_id: 'ha-hall',
    display_mode: 'big',
    live: false,
  }]);
  editor.remove();
});

test('the fleet editor configures a display mode just like a device card', async () => {
  const editor = document.createElement('nspanel-haui-card-editor');
  editor.setConfig({ type: 'custom:nspanel-haui-card', mode: 'fleet', live: false });
  editor.hass = fakeHass({ devices: [KITCHEN, HALL] });
  document.body.append(editor);
  await until(() => editor.shadowRoot.querySelector('ha-form'));
  const form = editor.shadowRoot.querySelector('ha-form');
  assert.deepEqual(form.schema.map((field) => field.name), [
    'mode', 'display_mode', 'live', 'title', 'scale',
  ]);
  assert.equal(form.data.mode, 'fleet');

  const changes = [];
  editor.addEventListener('config-changed', (event) => changes.push(event.detail.config));
  form.dispatchEvent(new CustomEvent('value-changed', { detail: { value: { mode: 'device' } } }));

  assert.deepEqual(changes, [{
    type: 'custom:nspanel-haui-card', mode: 'device', display_mode: 'big', live: false,
  }]);
  await until(() => editor.shadowRoot.querySelector('ha-form').schema.length === 6);
  editor.remove();
});

test('small and status device displays do not offer a screen-size setting', async () => {
  for (const displayMode of ['small', 'status']) {
    const editor = document.createElement('nspanel-haui-card-editor');
    editor.setConfig({
      type: 'custom:nspanel-haui-card', mode: 'device', device: 'kitchen', display_mode: displayMode,
    });
    editor.hass = fakeHass({ devices: [KITCHEN] });
    document.body.append(editor);
    await until(() => editor.shadowRoot.querySelector('ha-form'));
    assert.deepEqual(editor.shadowRoot.querySelector('ha-form').schema.map((field) => field.name), [
      'mode', 'device', 'display_mode', 'live', 'title',
    ]);
    editor.remove();
  }
});

test('the card editor can be tried again after a failed load', async () => {
  const editor = document.createElement('nspanel-haui-card-editor');
  editor.setConfig({ type: 'custom:nspanel-haui-card', mode: 'device', device: 'kitchen', layout: 'preview' });
  editor.hass = fakeHass({ devicesError: new Error('Home Assistant is starting') });
  document.body.append(editor);
  await until(() => byText(editor.shadowRoot, 'Home Assistant is starting', { exact: false }));

  editor.hass = fakeHass();
  byRole(editor.shadowRoot, 'button', { name: 'Retry' }).click();

  await until(() => editor.shadowRoot.querySelector('ha-form'));
  assert.equal(byText(editor.shadowRoot, 'Home Assistant is starting', { exact: false }), null);
  editor.remove();
});
