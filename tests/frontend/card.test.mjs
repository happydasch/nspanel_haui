import './support/browser.mjs';

import { mock, test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  CardHomeSession,
  CardLiveSession,
  CardStatusSession,
} from '../../custom_components/nspanel_haui/frontend/virtual/card-sessions.js';
import {
  RESUBSCRIBE_DELAY_MS,
  findDevice,
} from '../../custom_components/nspanel_haui/frontend/card/card.js';
import '../../custom_components/nspanel_haui/frontend/card/card-editor.js';
import { loadIconMap, loadLayout } from '../../custom_components/nspanel_haui/frontend/virtual/assets.js';
import { flush } from './support/render.mjs';
import { byClass, byRole, byText } from './support/queries.mjs';

const asset = (name) => JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/${name}`, import.meta.url),
  'utf8',
));

// The assets are memoised: load them once from the files, as fetch would.
loadLayout('landscape', () => asset('layout_landscape.json'));
loadIconMap(() => asset('icon_map.json'));

const GRID_PAGE_ID = 9;
const KITCHEN = { entry_id: 'entry1', name: 'kitchen', device_id: 'ha-kitchen', enabled: true };

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

/** The panel itself, as the hub reports it with the home panel. */
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

const screenOf = (card) => byRole(card.shadowRoot, 'img', { name: 'Screen of kitchen' });
const statusOf = (card) => byClass(card.shadowRoot, 'haui-card-status');

test('the card registers itself for the dashboard card picker', () => {
  const entry = window.customCards.find((card) => card.type === 'nspanel-haui-card');
  assert.equal(entry.name, 'NSPanel HAUI');
  assert.equal(entry.preview, true);
});

test('an unknown mode is a configuration error', () => {
  const card = document.createElement('nspanel-haui-card');
  assert.throws(() => card.setConfig({ device: 'kitchen', mode: 'sandbox' }), /sandbox/);
});

test('the picker starts with a card that asks for a device, without starting the hub', async () => {
  const hass = fakeHass();
  const card = document.createElement('nspanel-haui-card');
  card.setConfig(await card.constructor.getStubConfig(hass));
  card.hass = hass;
  document.body.append(card);
  await flush();

  assert.ok(byText(card.shadowRoot, 'Choose a device in the card settings'));
  assert.deepEqual(hass.subscriptions, []);
  card.remove();
});

test('a card without a device asks for one', async () => {
  const { card, hass } = await mountCard({});
  assert.ok(byText(card.shadowRoot, 'Choose a device in the card settings'));
  assert.deepEqual(hass.subscriptions, []);
  card.remove();
});

test('a card names a device the hub does not run', async () => {
  const { card, hass } = await mountCard({ device: 'garage' });
  await until(() => byText(card.shadowRoot, 'Device not found: garage'));
  assert.deepEqual(hass.subscriptions, []);
  card.remove();
});

test('a card finds its device by its Home Assistant device id after a rename', async () => {
  const { card, hass } = await mountCard({ device: 'old-name', device_id: 'ha-kitchen' });
  await until(() => hass.subscriptions.length === 1);
  assert.deepEqual(hass.subscriptions[0].message, {
    type: 'nspanel_haui/card/home/subscribe',
    device_id: 'ha-kitchen',
  });
  card.remove();
});

test('a home card shows the home panel the hub streams for the device', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
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

test('a home card reports the panel itself, as the hub sends it', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
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

test('a home card dims and marks the panel when it goes offline, keeping its screen', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
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

test('a live card mirrors the panel and marks it when it goes offline', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen', mode: 'live' });
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  assert.equal(live.message.type, 'nspanel_haui/card/live/subscribe');

  live.callback({ type: 'started', session_id: 'abc', portrait: false });
  live.callback({
    type: 'physical',
    connected: true,
    idle: false,
    display_state: 'on',
    firmware: '0.5.2',
    tft: '1.0.4',
  });
  live.callback({ type: 'page', page: GRID_PAGE_ID });
  await until(() => screenOf(card));
  assert.ok(!byText(card.shadowRoot, 'Disconnected'));

  live.callback({ type: 'physical', connected: false, idle: false, display_state: 'on' });

  await until(() => byText(card.shadowRoot, 'Disconnected'));
  assert.ok(screenOf(card));
  card.remove();
});

test('a live card reports what the panel runs, as the panel sent it', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen', mode: 'live' });
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  live.callback({ type: 'started', session_id: 'abc', portrait: false });
  live.callback({ type: 'page', page: GRID_PAGE_ID });
  await until(() => statusOf(card));

  live.callback({
    type: 'physical',
    connected: true,
    idle: false,
    display_state: 'on',
    firmware: '0.5.2',
    tft: '1.0.4',
  });

  await until(() => byText(statusOf(card), '0.5.2'));
  assert.ok(byText(statusOf(card), '1.0.4'));
  assert.ok(!byText(statusOf(card), 'Unknown'), 'the hub reported both versions');
  card.remove();
});

test('a card can show its screen smaller', async () => {
  const widthOf = (card) => {
    const sim = card.shadowRoot.querySelector('.haui-preview-sim');
    return Number(/--vp-preview-width:\s*([\d.]+)px/.exec(sim.getAttribute('style'))[1]);
  };
  const { card: full, hass: fullHass } = await mountCard({ device: 'kitchen' });
  await until(() => fullHass.subscriptions.length === 1);
  drawHome(fullHass.subscriptions[0]);
  await until(() => screenOf(full));

  const { card: small, hass: smallHass } = await mountCard({ device: 'kitchen', scale: 50 });
  await until(() => smallHass.subscriptions.length === 1);
  drawHome(smallHass.subscriptions[0]);
  await until(() => screenOf(small));

  assert.ok(Math.abs(widthOf(small) * 2 - widthOf(full)) < 2, 'half the size it would take');
  assert.ok(small.getCardSize() < full.getCardSize(), 'and a shorter card');
  full.remove();
  small.remove();
});

test('a card keeps a scale within what it can draw', () => {
  const card = document.createElement('nspanel-haui-card');
  card.setConfig({ device: 'kitchen', scale: 500 });
  assert.equal(card.getCardSize(), 6);
  card.setConfig({ device: 'kitchen', scale: 1 });
  assert.equal(card.getCardSize(), 1);
});

test('the frame shows the panel\'s hardware buttons and their lights', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  const [home] = hass.subscriptions;
  drawHome(home);
  home.callback({
    type: 'buttons',
    left: { relay: 'switch.kitchen_relay_left', entity: null, state: 'on', relay_state: 'on' },
    right: { relay: null, entity: null, state: 'off', relay_state: 'off' },
  });

  await until(() => byClass(card.shadowRoot, 'haui-card-led'));
  const leds = [...card.shadowRoot.querySelectorAll('.haui-card-led')];
  assert.deepEqual(leds.map((led) => led.dataset.state), ['on', 'off']);
  card.remove();
});

test('a frame button that switches an entity shows it beside its relay', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
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

  await until(() => card.shadowRoot.querySelector('.haui-card-led.entity'));
  assert.equal(card.shadowRoot.querySelector('.haui-card-led.entity').dataset.state, 'on');
  // The relay keeps its own light: this button switches the lamp.
  assert.equal(card.shadowRoot.querySelector('.haui-card-led-dot').dataset.state, 'off');
  card.remove();
});

test('a card always draws its frame and the row under it', async () => {
  // Nothing in the config hides part of the card: it is the panel, or a tile.
  const { card, hass } = await mountCard({ device: 'kitchen', frame: false, status: false });
  await until(() => hass.subscriptions.length === 1);
  drawHome(hass.subscriptions[0]);
  await until(() => screenOf(card));

  assert.ok(byClass(card.shadowRoot, 'haui-card-hw'));
  assert.ok(statusOf(card));
  card.remove();
});

test('a status tile shows the panel without a screen to draw', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen', mode: 'tile' });
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  assert.equal(live.message.type, 'nspanel_haui/card/live/subscribe');
  live.callback({ type: 'started', session_id: 'abc', portrait: false });
  // The hub has no page for this device; the panel itself is still reported.
  drawPanel(live, { display: 'dim', queued: 1 });

  await until(() => statusOf(card) && byText(statusOf(card), 'Dimmed'));
  assert.equal(screenOf(card), null);
  assert.equal(card.shadowRoot.querySelector('.haui-preview-sim'), null, 'no display is built');
  assert.ok(byRole(statusOf(card), 'img', { name: 'Connected' }));
  assert.equal(byClass(card.shadowRoot, 'haui-card-status-queued').textContent.trim(), '1');
  card.remove();
});

test('a card saved before the status tile existed keeps its tile', () => {
  const card = document.createElement('nspanel-haui-card');
  card.setConfig({ device: 'kitchen', screen: false });
  assert.equal(card.getCardSize(), 2);
  assert.deepEqual(card.getGridOptions(), { columns: 6, rows: 'auto', min_columns: 3 });
});

test('a card of a disabled device says so instead of showing nothing', async () => {
  const hass = fakeHass({ devices: [{ ...KITCHEN, enabled: false }] });
  const { card } = await mountCard({ device: 'kitchen' }, hass);

  await until(() => byText(card.shadowRoot, 'The device is disabled in NSPanel HAUI'));
  assert.deepEqual(hass.subscriptions, []);
  card.remove();
});

test('a card whose device goes away says why instead of keeping its last screen', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  drawHome(hass.subscriptions[0]);
  drawPanel(hass.subscriptions[0]);
  await until(() => screenOf(card));

  // Home Assistant reconnected and the panel was disabled meanwhile.
  card.hass = fakeHass({ devices: [{ ...KITCHEN, enabled: false }] });
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    hass.listeners.ready();
    mock.timers.tick(RESUBSCRIBE_DELAY_MS);
  } finally {
    mock.timers.reset();
  }

  await until(() => byText(card.shadowRoot, 'The device is disabled in NSPanel HAUI'));
  assert.equal(screenOf(card), null);
  card.remove();
});

test('a card the hub refuses because the device is disabled says so', async () => {
  // The device was disabled between the card's device list and its subscription.
  const error = Object.assign(new Error('disabled'), { code: 'disabled' });
  const { card } = await mountCard({ device: 'kitchen' }, fakeHass({ subscribeError: error }));

  await until(() => byText(card.shadowRoot, 'The device is disabled in NSPanel HAUI'));
  card.remove();
});

test('a card with a title shows it as its heading', async () => {
  const { card } = await mountCard({ device: 'kitchen', title: 'Hallway' });
  await until(() => byClass(card.shadowRoot, 'haui-card-title'));
  assert.ok(byText(card.shadowRoot, 'Hallway'));
  card.remove();
});

test('a card the hub ended subscribes again and keeps its screen meanwhile', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
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

test('a status tile session keeps the panel state and builds no display', async () => {
  const hass = fakeHass();
  const session = new CardStatusSession(hass, { deviceId: 'ha-kitchen' });
  await session.start();
  assert.deepEqual(hass.subscriptions[0].message, {
    type: 'nspanel_haui/card/live/subscribe',
    device_id: 'ha-kitchen',
  });

  const [subscription] = hass.subscriptions;
  subscription.callback({ type: 'started', session_id: 'abc', portrait: false });
  drawPanel(subscription, { display: 'dim', queued: 3 });

  assert.equal(session.display, null, 'a tile draws nothing');
  assert.equal(session.ready, false);
  assert.equal(session.physical.display_state, 'dim');
  assert.equal(session.notifications, 3);
  await session.stop();
});

test('a card session sends nothing back to the hub', async () => {
  for (const Session of [CardHomeSession, CardLiveSession]) {
    const hass = fakeHass();
    const session = new Session(hass, { deviceId: 'ha-kitchen' });
    await session.start();
    assert.deepEqual(hass.subscriptions[0].message, {
      type: `${Session.API}/subscribe`,
      device_id: 'ha-kitchen',
    });
    hass.subscriptions[0].callback({ type: 'started', session_id: 'abc', portrait: false });
    hass.subscriptions[0].callback({ type: 'physical', connected: true, idle: false, display_state: 'on' });
    await until(() => session.ready);

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
  const devices = [
    { entry_id: 'entry1', name: 'kitchen', device_id: 'ha-kitchen', enabled: true },
    { entry_id: 'entry1', name: 'hall', device_id: 'ha-hall', enabled: true },
  ];
  assert.equal(findDevice(devices, { device: 'hall', device_id: 'ha-kitchen' }).name, 'kitchen');
  assert.equal(findDevice(devices, { device: 'hall' }).name, 'hall');
  assert.equal(findDevice(devices, { device: 'renamed', device_id: 'ha-hall' }).name, 'hall');
  assert.equal(findDevice(devices, { device: 'garage' }), undefined);
});

test('the card editor offers the hub devices, disabled ones marked, and stores the device id', async () => {
  const editor = document.createElement('nspanel-haui-card-editor');
  editor.setConfig({ type: 'custom:nspanel-haui-card', device: 'kitchen', mode: 'home' });
  editor.hass = fakeHass({
    devices: [KITCHEN, { entry_id: 'entry1', name: 'hall', device_id: 'ha-hall', enabled: false }],
  });
  document.body.append(editor);
  await until(() => editor.shadowRoot.querySelector('ha-form'));
  const form = editor.shadowRoot.querySelector('ha-form');
  const [device, mode] = form.schema;
  assert.deepEqual(
    device.selector.select.options.map((option) => option.label),
    ['kitchen', 'hall (disabled)'],
  );
  assert.deepEqual(
    mode.selector.select.options.map((option) => option.value),
    ['home', 'live', 'tile'],
  );
  assert.deepEqual(
    form.schema.slice(2).map((field) => field.name),
    ['title', 'scale'],
  );

  const changes = [];
  editor.addEventListener('config-changed', (event) => changes.push(event.detail.config));
  form.dispatchEvent(new CustomEvent('value-changed', { detail: { value: { device: 'hall' } } }));

  assert.deepEqual(changes, [{
    type: 'custom:nspanel-haui-card', device: 'hall', device_id: 'ha-hall', mode: 'home',
  }]);
  editor.remove();
});

test('the card editor can be tried again after a failed load', async () => {
  const editor = document.createElement('nspanel-haui-card-editor');
  editor.setConfig({ type: 'custom:nspanel-haui-card', device: 'kitchen', mode: 'home' });
  editor.hass = fakeHass({ devicesError: new Error('Home Assistant is starting') });
  document.body.append(editor);
  await until(() => byText(editor.shadowRoot, 'Home Assistant is starting', { exact: false }));

  editor.hass = fakeHass();
  byRole(editor.shadowRoot, 'button', { name: 'Retry' }).click();

  await until(() => {
    const form = editor.shadowRoot.querySelector('ha-form');
    return form?.schema?.[0]?.selector?.select?.options?.length === 1;
  });
  assert.equal(byText(editor.shadowRoot, 'Home Assistant is starting', { exact: false }), null);
  editor.remove();
});

