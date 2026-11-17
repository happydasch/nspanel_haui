import './support/browser.mjs';

import { mock, test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  CardHomeSession,
  CardLiveSession,
} from '../../custom_components/nspanel_haui/frontend/virtual/card-sessions.js';
import { RESUBSCRIBE_DELAY_MS } from '../../custom_components/nspanel_haui/frontend/card/card.js';
import '../../custom_components/nspanel_haui/frontend/card/card-editor.js';
import { loadIconMap, loadLayout } from '../../custom_components/nspanel_haui/frontend/virtual/assets.js';
import { flush } from './support/render.mjs';
import { byRole, byText } from './support/queries.mjs';

const asset = (name) => JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/${name}`, import.meta.url),
  'utf8',
));

// The assets are memoised: load them once from the files, as fetch would.
loadLayout('landscape', () => asset('layout_landscape.json'));
loadIconMap(() => asset('icon_map.json'));

const GRID_PAGE_ID = 9;
const KITCHEN = { entry_id: 'entry1', name: 'kitchen', portrait: false };

function fakeHass({ devices = [KITCHEN], subscribeError = null } = {}) {
  const hass = {
    language: 'en',
    subscriptions: [],
    calls: [],
    listeners: {},
    connection: {
      async sendMessagePromise(message) {
        assert.equal(message.type, 'nspanel_haui/card/devices');
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

const screenOf = (card) => byRole(card.shadowRoot, 'img', { name: 'Screen of kitchen' });

test('the card registers itself for the dashboard card picker', () => {
  const entry = window.customCards.find((card) => card.type === 'nspanel-haui-card');
  assert.equal(entry.name, 'NSPanel HAUI');
  assert.equal(entry.preview, true);
});

test('an unknown mode is a configuration error', () => {
  const card = document.createElement('nspanel-haui-card');
  assert.throws(() => card.setConfig({ device: 'kitchen', mode: 'sandbox' }), /sandbox/);
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

test('a home card shows the home panel the hub streams for the device', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen' });
  await until(() => hass.subscriptions.length === 1);
  assert.deepEqual(hass.subscriptions[0].message, {
    type: 'nspanel_haui/card/home/subscribe',
    entry_id: 'entry1',
    device: 'kitchen',
  });

  drawHome(hass.subscriptions[0]);

  await until(() => screenOf(card));
  assert.ok(byText(screenOf(card), 'Rooms'));
  card.remove();
  await flush();
  assert.equal(hass.subscriptions[0].closed, true);
});

test('a live card mirrors the panel and marks it when it goes offline', async () => {
  const { card, hass } = await mountCard({ device: 'kitchen', mode: 'live' });
  await until(() => hass.subscriptions.length === 1);
  const [live] = hass.subscriptions;
  assert.equal(live.message.type, 'nspanel_haui/card/live/subscribe');

  live.callback({ type: 'started', session_id: 'abc', portrait: false });
  live.callback({ type: 'physical', connected: true, idle: false, display_state: 'on' });
  live.callback({ type: 'page', page: GRID_PAGE_ID });
  await until(() => screenOf(card));
  assert.ok(!byText(card.shadowRoot, 'Disconnected'));

  live.callback({ type: 'physical', connected: false, idle: false, display_state: 'on' });

  await until(() => byText(card.shadowRoot, 'Disconnected'));
  assert.ok(screenOf(card));
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

test('a card session sends nothing back to the hub', async () => {
  for (const Session of [CardHomeSession, CardLiveSession]) {
    const hass = fakeHass();
    const session = new Session(hass, { entryId: 'entry1', device: 'kitchen' });
    await session.start();
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

test('the card editor offers the running devices and reports a change', async () => {
  const editor = document.createElement('nspanel-haui-card-editor');
  editor.setConfig({ type: 'custom:nspanel-haui-card', device: 'kitchen', mode: 'home' });
  editor.hass = fakeHass({ devices: [KITCHEN, { entry_id: 'entry1', name: 'hall', portrait: true }] });
  document.body.append(editor);
  await until(() => editor.shadowRoot.querySelector('ha-form'));
  const form = editor.shadowRoot.querySelector('ha-form');
  const [device, mode] = form.schema;
  assert.deepEqual(device.selector.select.options.map((option) => option.value), ['kitchen', 'hall']);
  assert.deepEqual(mode.selector.select.options.map((option) => option.value), ['home', 'live']);

  const changes = [];
  editor.addEventListener('config-changed', (event) => changes.push(event.detail.config));
  form.dispatchEvent(new CustomEvent('value-changed', { detail: { value: { mode: 'live' } } }));

  assert.deepEqual(changes, [{ type: 'custom:nspanel-haui-card', device: 'kitchen', mode: 'live' }]);
  editor.remove();
});
