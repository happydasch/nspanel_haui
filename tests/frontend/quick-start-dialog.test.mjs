import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { flush, mount } from './support/render.mjs';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';

const TAG = 'nspanel-dialog-quick-start';

/** A preset as the flow hands it in, without a preview render. */
function presetEntry(key, overrides = {}) {
  return {
    key,
    label: `${key} preset`,
    description: `${key} description`,
    icon: 'mdi:view-grid-outline',
    needsArea: false,
    error: '',
    preview: null,
    ...overrides,
  };
}

/** The chosen preset resolved, as the flow hands it in. */
function resolution(overrides = {}) {
  return {
    preset: 'room',
    area: null,
    areaName: '',
    label: 'Room panel',
    description: 'Room description',
    toggles: [
      { key: 'navigation', label: 'Show entities in navigation', description: 'Reach them by swiping', on: false },
      { key: 'wifi', label: 'Add a guest Wi-Fi page', description: 'A QR code', on: false },
    ],
    pages: [
      {
        id: 'home',
        role: 'home',
        node: 'home',
        key: 'room_kitchen',
        label: 'Kitchen',
        typeLabel: 'Grid',
        typeDescription: 'Tiles',
        entityCount: 3,
        preview: null,
        panel: { type: 'grid' },
      },
      {
        id: 'clock',
        role: 'idle',
        node: 'idle',
        key: 'room_kitchen_clock',
        label: 'Clock',
        typeLabel: 'Clock',
        typeDescription: 'A clock',
        entityCount: 0,
        preview: null,
        panel: { type: 'clock' },
      },
    ],
    dropped: [],
    config: {},
    ready: true,
    blocked: [],
    needsInput: [],
    warnings: [],
    entityCount: 3,
    preview: null,
    ...overrides,
  };
}

/** Mount the dialog and record what it asks the editor to do. */
async function dialog(props = {}) {
  const events = [];
  const element = await mount(TAG, {
    hass: {},
    open: true,
    deviceName: 'Kitchen',
    presets: [],
    resolution: null,
    choices: { preset: null, areaId: '', toggles: {}, essid: '', password: '' },
    areas: [],
    saving: false,
    error: '',
    ...props,
  });
  for (const name of ['dialog-closed', 'quick-start-choose', 'quick-start-create']) {
    element.addEventListener(name, (event) => events.push(event));
  }
  await flush();
  return { element, events };
}

const card = (element, key) => element.shadowRoot.querySelector(`button[data-preset="${key}"]`);
const toggle = (element, key) => element.shadowRoot.querySelector(`#quick-start-toggle-${key}`);
const create = (element) => element.shadowRoot.querySelector('ha-dialog-footer ha-button[slot="primaryAction"]');

test('the first step offers a configuration per use case, with its name, render and what it is for', async () => {
  const { element } = await dialog({ presets: [presetEntry('room'), presetEntry('guest')] });
  assert.equal(element.shadowRoot.querySelectorAll('button[data-preset]').length, 2);
  // The card names the configuration above the sentence describing it.
  assert.equal(card(element, 'room').querySelector('.haui-quick-start-title').textContent.trim(),
    'room preset');
  assert.equal(card(element, 'room').querySelector('.haui-quick-start-description').textContent.trim(),
    'room description');
  assert.match(card(element, 'guest').textContent, /guest preset/);
  assert.match(card(element, 'guest').textContent, /guest description/);
});

test('choosing a configuration asks the editor for it', async () => {
  const { element, events } = await dialog({ presets: [presetEntry('room')] });
  card(element, 'room').click();
  assert.deepEqual(events.map((event) => [event.type, event.detail]),
    [['quick-start-choose', { preset: 'room' }]]);
});

test('choosing a preset and going back keep the Home Assistant modal open', async () => {
  const { element, events } = await dialog({ presets: [presetEntry('room')] });
  const modal = element.shadowRoot.querySelector('ha-dialog');
  element.addEventListener('quick-start-choose', ({ detail }) => {
    element.choices = { ...element.choices, ...detail };
    element.resolution = detail.preset ? resolution() : null;
  });

  card(element, 'room').click();
  await flush();
  assert.match(create(element).textContent, /Create 2 pages/);
  assert.equal(element.shadowRoot.querySelector('ha-dialog'), modal);
  assert.equal(modal.open, true);

  modal.querySelector('[slot="secondaryAction"]').click();
  await flush();
  assert.ok(card(element, 'room'));
  assert.equal(element.shadowRoot.querySelector('ha-dialog'), modal);
  assert.equal(modal.open, true);
  assert.deepEqual(events.map((event) => event.type), ['quick-start-choose', 'quick-start-choose']);
});

test('the second step shows the choices and a gallery of the pages it creates', async () => {
  const { element } = await dialog({
    presets: [presetEntry('room', { needsArea: true })],
    resolution: resolution(),
    choices: { preset: 'room', areaId: 'kitchen', toggles: {}, essid: '', password: '' },
    areas: [{ area_id: 'kitchen', name: 'Kitchen' }, { area_id: 'bedroom', name: 'Bedroom' }],
  });
  const root = element.shadowRoot;
  assert.match(root.textContent, /room preset/);
  // The area it resolves against, with every area of the installation.
  const options = [...root.querySelectorAll('#quick-start-area option')];
  assert.deepEqual(options.map((option) => option.value), ['', 'kitchen', 'bedroom']);
  // The placeholder is not a choice.
  assert.equal(options[0].disabled, true);
  // The pages the configuration chooses are shown as they are: the type of a
  // page is the configuration's, so the second step only offers what it needs.
  assert.ok(toggle(element, 'navigation'));
  // The pages it will create, in the order it saves them.
  assert.deepEqual([...root.querySelectorAll('.haui-quick-start-page')]
    .map((item) => item.dataset.page), ['home', 'clock']);
  assert.match(create(element).textContent, /Create 2 pages/);
});

test('the second step reads top to bottom: the setup, its controls, its pages, the switches, what it needs', async () => {
  const { element } = await dialog({
    presets: [presetEntry('room', { needsArea: true })],
    resolution: resolution({ warnings: ['Lights is left out: it would show nothing'] }),
    choices: { preset: 'room', areaId: 'kitchen', toggles: {}, essid: '', password: '' },
    areas: [{ area_id: 'kitchen', name: 'Kitchen' }],
  });
  const root = element.shadowRoot;
  // What the configuration is, without opening anything: its name and sentence
  // first, then only the controls that fill it in, then the pages it creates,
  // then the switches that add optional pages, then the banner with what it
  // still needs.
  const heading = root.querySelector('.haui-quick-start-heading');
  assert.match(heading.textContent, /room preset/);
  assert.match(heading.textContent, /room description/);
  assert.deepEqual([...root.querySelector('.haui-quick-start-setup').children]
    .map((section) => section.className),
  ['haui-quick-start-form', 'haui-quick-start-result', 'haui-quick-start-toggles',
    'haui-quick-start-outcome']);
  // The pages gallery counts what it creates, and each page says where it sits.
  assert.match(root.querySelector('.haui-quick-start-pages-meta').textContent, /2 pages · 3 entities/);
  // What it needs comes after the pages and their switches - not between the
  // controls and them, and not out in the footer - and it is a banner of the
  // hub's own alert, not a line of text lost under the gallery.
  const outcome = root.querySelector('ha-alert.haui-quick-start-outcome');
  assert.equal(outcome.getAttribute('alert-type'), 'warning');
  assert.equal(outcome.previousElementSibling.className, 'haui-quick-start-toggles');
  assert.equal(outcome.closest('[slot="footer"]'), null);
  assert.match(outcome.textContent, /Lights is left out/);
  assert.equal(outcome.title, '');
  assert.equal(root.querySelector('.haui-quick-start-form [role="status"]'), null);
  assert.equal(root.querySelector('details'), null);
  // Every field and switch carries its explanation as a hint of its own - and
  // only one: a native title beside it would draw a second tooltip.
  const hints = [...root.querySelectorAll('.haui-field-hint')].map((hint) => hint.textContent);
  assert.ok(hints.some((hint) => /Reach them by swiping/.test(hint)), hints.join('|'));
  assert.ok(hints.some((hint) => /from this area/.test(hint)), hints.join('|'));
  const titled = [...root.querySelectorAll(
    '.haui-quick-start-form [title], .haui-quick-start-toggles [title]',
  )].map((control) => control.getAttribute('title'));
  assert.deepEqual(titled, []);
});

test('the second step offers the theme the device draws in, and passes the choice back', async () => {
  const { element, events } = await dialog({
    presets: [presetEntry('guest')],
    resolution: resolution({ preset: 'guest' }),
    choices: { preset: 'guest', areaId: '', themeId: 'ocean', toggles: {}, essid: '', password: '' },
    themeOptions: [
      { value: 'dark', label: 'Dark Color' },
      { value: 'ocean', label: 'Ocean' },
    ],
  });
  const select = element.shadowRoot.querySelector('#quick-start-theme');
  assert.deepEqual([...select.options].map((option) => option.value), ['dark', 'ocean']);
  // The theme every configuration offers, not only those that fill an area in.
  assert.equal(select.value, 'ocean');
  select.value = 'dark';
  select.dispatchEvent(new Event('change'));
  assert.deepEqual(events.map((event) => event.detail), [{ themeId: 'dark' }]);
});

test('the pages it creates are a gallery: each page render, its role and its type', async () => {
  const { element } = await dialog({
    presets: [presetEntry('room')],
    resolution: resolution({
      pages: [
        ...resolution().pages,
        {
          id: 'switches',
          role: 'page',
          node: 'navigation',
          key: 'room_kitchen_switches',
          label: 'Switches',
          typeLabel: 'Row',
          typeDescription: 'One row of switches',
          entityCount: 4,
          preview: null,
          panel: { type: 'row' },
        },
      ],
    }),
    choices: { preset: 'room', areaId: 'kitchen' },
  });
  const entries = [...element.shadowRoot.querySelectorAll('.haui-quick-start-page')];
  assert.equal(entries.length, 3);
  assert.match(entries[0].textContent, /Kitchen/);
  assert.match(entries[0].textContent, /Grid · 3 entities/);
  // Where a page sits is a marker of its own, as the panel list draws it: the
  // role's icon, named for a screen reader, never a word in the card's text.
  const roles = (entry) => [...entry.querySelectorAll('[role="img"]')]
    .map((marker) => marker.getAttribute('aria-label'));
  assert.deepEqual(roles(entries[0]), ['Home panel']);
  assert.deepEqual(roles(entries[1]), ['Idle panel']);
  // A page the device reaches by swiping carries the panel list's own word for
  // it, not a second name for the same setting.
  assert.deepEqual(roles(entries[2]), ['Navigation']);
  for (const entry of entries) {
    assert.doesNotMatch(entry.textContent, /Home panel|Idle panel|Navigation|Hidden/);
  }
  assert.equal(entries[1].title, 'A clock');
});

test('a switch for a page this installation cannot fill is not offered', async () => {
  const { element } = await dialog({
    presets: [presetEntry('room')],
    resolution: resolution({
      toggles: [
        { key: 'navigation', label: 'Show entities in navigation', description: 'They become navigation pages', on: false, available: true },
        { key: 'cover', label: 'Blind page', description: 'A blind', on: false, available: false },
      ],
    }),
    choices: { preset: 'room' },
  });
  assert.ok(toggle(element, 'navigation'));
  assert.equal(toggle(element, 'cover'), null);
});

test('a choice in the second step is passed back to the editor', async () => {
  const { element, events } = await dialog({
    presets: [presetEntry('room', { needsArea: true })],
    resolution: resolution(),
    choices: { preset: 'room', areaId: 'kitchen', toggles: {}, essid: '', password: '' },
    areas: [{ area_id: 'kitchen', name: 'Kitchen' }, { area_id: 'bedroom', name: 'Bedroom' }],
  });
  const root = element.shadowRoot;
  const select = root.querySelector('#quick-start-area');
  select.value = 'bedroom';
  select.dispatchEvent(new Event('change'));
  const wifi = toggle(element, 'wifi');
  wifi.checked = true;
  wifi.dispatchEvent(new Event('change'));
  assert.deepEqual(events.map((event) => event.detail), [
    { areaId: 'bedroom' },
    { toggles: { wifi: true } },
  ]);
});

test('the standalone Guest Wi-Fi setup shows both network fields', async () => {
  const { element, events } = await dialog({
    presets: [presetEntry('guest')],
    resolution: resolution({
      preset: 'guest',
      pages: [{ id: 'home', role: 'home', label: 'Guest Wi-Fi', panel: { type: 'qr' } }],
    }),
    choices: { preset: 'guest', areaId: '', toggles: {}, essid: '', password: '' },
  });
  assert.equal(element.shadowRoot.querySelector('#quick-start-password').type, 'password');
  const essid = element.shadowRoot.querySelector('#quick-start-essid');
  assert.ok(essid);
  essid.value = 'MyNet';
  essid.dispatchEvent(new Event('input'));
  assert.deepEqual(events.map((event) => event.detail), [{ essid: 'MyNet' }]);
});

test('a setup that is not ready cannot be created, and says why', async () => {
  const { element, events } = await dialog({
    presets: [presetEntry('security')],
    resolution: resolution({
      preset: 'security', ready: false, blocked: ['alarm_control_panel'], warnings: ['Some pages were omitted'],
    }),
    choices: { preset: 'security', areaId: '', toggles: {}, essid: '', password: '' },
  });
  assert.equal(create(element).disabled, true);
  const root = element.shadowRoot;
  // Both the reason and the warnings it came with are one error banner, not
  // folded away.
  assert.equal(root.querySelector('details'), null);
  const banner = root.querySelector('ha-alert.haui-quick-start-outcome');
  assert.equal(banner.getAttribute('alert-type'), 'error');
  assert.match(banner.title, /alarm_control_panel/);
  assert.match(banner.textContent, /Some pages were omitted/);
  // A ready setup is the one whose action creates pages; the flow refuses a blocked one.
  assert.deepEqual(events, []);
});

test('a ready setup creates its pages', async () => {
  const { element, events } = await dialog({
    presets: [presetEntry('room')],
    resolution: resolution(),
    choices: { preset: 'room', areaId: 'kitchen', toggles: {}, essid: '', password: '' },
  });
  assert.equal(create(element).disabled, false);
  create(element).click();
  assert.deepEqual(events.map((event) => event.type), ['quick-start-create']);
});

test('going back returns to the list of configurations', async () => {
  const { element, events } = await dialog({
    presets: [presetEntry('room')],
    resolution: resolution(),
    choices: { preset: 'room', areaId: '', toggles: {}, essid: '', password: '' },
  });
  element.shadowRoot.querySelector('ha-button[slot="secondaryAction"]').click();
  assert.deepEqual(events.map((event) => event.detail), [{ preset: null }]);
});

test('a failure is announced and every action waits while the setup is created', async () => {
  const failed = await dialog({
    presets: [presetEntry('room')],
    resolution: resolution(),
    choices: { preset: 'room', areaId: '', toggles: {}, essid: '', password: '' },
    error: 'The pages could not be saved.',
  });
  assert.equal(failed.element.shadowRoot.querySelector('ha-alert.haui-quick-start-save-error').textContent,
    'The pages could not be saved.');

  const saving = await dialog({ presets: [presetEntry('room')], saving: true });
  assert.equal(card(saving.element, 'room').disabled, true);
});
test('a configuration that could not be resolved is still listed, with its reason', async () => {
  const { element } = await dialog({ presets: [
    presetEntry('room', { error: 'Something went wrong' }),
    presetEntry('home'),
  ] });
  // One broken configuration never empties the chooser.
  assert.equal(element.shadowRoot.querySelectorAll('button[data-preset]').length, 2);
  assert.match(card(element, 'room').textContent, /Something went wrong/);
  assert.equal(card(element, 'home').querySelector('[role="alert"]'), null);
});


test('Done closes the quick start', async () => {
  const { element, events } = await dialog({ presets: [presetEntry('room')] });
  element.shadowRoot.querySelector('ha-dialog-footer ha-button').click();
  assert.deepEqual(events.map((event) => event.type), ['dialog-closed']);
});
