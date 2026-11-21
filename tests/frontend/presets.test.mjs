import { test } from 'node:test';
import assert from 'node:assert/strict';

import { presets, presetByKey, presetKeys, resolvePreset } from '../../custom_components/nspanel_haui/frontend/presets.js';
import { registryWorld } from './support/hass.mjs';

/** The option descriptors of the types the presets use, as the hub serves them. */
const PANEL_TYPES = [
  { type_key: 'grid', options: [{ key: 'items', kind: 'item_list' }] },
  { type_key: 'row', options: [{ key: 'items', kind: 'item_list' }] },
  { type_key: 'climate', options: [{ key: 'item', kind: 'item', domain: 'climate', required: true }] },
  { type_key: 'media', options: [{ key: 'item', kind: 'item', domain: 'media_player', required: true }] },
  { type_key: 'light', options: [{ key: 'item', kind: 'item', domain: 'light', required: true }] },
  { type_key: 'cover', options: [{ key: 'item', kind: 'item', domain: 'cover', required: true }] },
  { type_key: 'vacuum', options: [{ key: 'item', kind: 'item', domain: 'vacuum', required: true }] },
  { type_key: 'alarm', options: [{ key: 'item', kind: 'item', domain: 'alarm_control_panel', required: true }] },
  { type_key: 'timer', options: [] },
  {
    type_key: 'weather',
    options: [
      { key: 'item', kind: 'item', domain: 'weather' },
      { key: 'inside_temp_item', kind: 'item', domain: 'sensor' },
      { key: 'info_items', kind: 'item_list', max_items: 2 },
    ],
  },
  {
    type_key: 'clock',
    options: [
      { key: 'item', kind: 'item', domain: 'weather' },
      { key: 'inside_temp_item', kind: 'item', domain: 'sensor' },
      { key: 'items', kind: 'item_list', max_items: 6 },
    ],
  },
  { type_key: 'clocktwo', options: [] },
  {
    type_key: 'qr',
    options: [
      { key: 'essid', kind: 'str', label: 'WiFi SSID', required: true },
      { key: 'password', kind: 'str' },
    ],
  },
];

/** An installation with a kitchen and a bedroom, and the entities presets show. */
function installation({ kitchen = true, alarm = true, lights = true } = {}) {
  const entities = [
    { entity_id: 'weather.home' },
    { entity_id: 'sensor.outside' },
    { entity_id: 'sensor.aaaa_illuminance' },
    { entity_id: 'sensor.plug_power' },
    { entity_id: 'switch.fan' },
    { entity_id: 'scene.movie' },
    { entity_id: 'vacuum.robot' },
    { entity_id: 'sensor.robot_battery' },
  ];
  if (alarm) entities.push({ entity_id: 'alarm_control_panel.home' });
  if (lights) { entities.push({ entity_id: 'light.lamp' }, { entity_id: 'light.bedroom', area_id: 'bedroom' }); }
  if (kitchen) {
    entities.push(
      { entity_id: 'light.kitchen', area_id: 'kitchen' },
      // In the kitchen through its device, like Home Assistant's own rule.
      { entity_id: 'light.kitchen_spot', device_id: 'dev_thermostat' },
      { entity_id: 'switch.kettle', area_id: 'kitchen' },
      { entity_id: 'cover.kitchen', area_id: 'kitchen' },
      { entity_id: 'climate.kitchen', area_id: 'kitchen' },
      { entity_id: 'media_player.kitchen', area_id: 'kitchen' },
      { entity_id: 'sensor.kitchen_temperature', area_id: 'kitchen' },
      { entity_id: 'sensor.kitchen_humidity', area_id: 'kitchen' },
    );
  }
  const states = Object.fromEntries(entities.map((entry) => [entry.entity_id, { state: 'on' }]));
  for (const [id, device_class] of Object.entries({
    'sensor.outside': 'temperature',
    'sensor.aaaa_illuminance': 'illuminance',
    'sensor.plug_power': 'power',
    'sensor.robot_battery': 'battery',
    'sensor.kitchen_humidity': 'humidity',
  })) {
    if (states[id]) states[id].attributes = { device_class };
  }
  return {
    ...registryWorld({
      areas: [
        { area_id: 'bedroom', name: 'Bedroom' },
        {
          area_id: 'kitchen',
          name: 'Kitchen',
          temperature_entity_id: 'sensor.kitchen_temperature',
          humidity_entity_id: 'sensor.kitchen_humidity',
        },
      ],
      devices: [{ id: 'dev_thermostat', area_id: 'kitchen' }],
      entities,
    }),
    states,
  };
}

/** @param {string} key */
const preset = (key) => presetByKey(key);

/** @param {string} key @param {any} [world] */
function resolve(key, world = {}) {
  const { areaId = 'kitchen', ...rest } = world;
  const entry = preset(key);
  return resolvePreset(entry, {
    hass: installation(),
    panelTypes: PANEL_TYPES,
    // Only an area preset resolves against one; the others read the installation.
    areaId: entry.needsArea ? areaId : '',
    ...rest,
  });
}

test('every preset resolves pages and the settings that make them work', () => {
  for (const { key } of presets()) {
    // The guest QR code requires a network name.
    const choices = key === 'guest' ? { essid: 'MyNet' } : {};
    const resolved = resolve(key, { areaId: 'kitchen', choices });
    assert.ok(resolved.pages.some((page) => page.role === 'home'), key);
    assert.equal(resolved.pages.filter((page) => page.role === 'home').length, 1, key);
    assert.equal(resolved.ready, true, `${key}: ${resolved.blocked.join(',')}`);
    for (const page of resolved.pages) {
      assert.ok(page.key, `${key}/${page.id} has a key`);
      assert.ok(page.panel.type, `${key}/${page.id} names its type`);
    }
  }
});

test('a room preset takes its home page from the area and its title from its name', () => {
  const resolved = resolve('room');
  const home = resolved.pages.find((page) => page.role === 'home');
  assert.equal(home.panel.title, 'Kitchen');
  assert.equal(home.panel.type, 'grid');
  // An entity in the area, one in the area through its device, and the rest.
  assert.deepEqual(home.panel.items.map((item) => item.item), [
    'light.kitchen', 'cover.kitchen', 'climate.kitchen', 'media_player.kitchen', 'switch.kettle',
  ]);
  // The scene slot had no entity in this area, so it is left out, not blank -
  // and not asked for: a tile list takes the entities the room has.
  assert.ok(home.panel.items.every((item) => item.domain === undefined));
  assert.deepEqual(home.missing, []);
  assert.equal(resolved.config.home_panel, home.key);
});

test('a room with no entity of any tile list is still set up', () => {
  // The bedroom has nothing a grid looks for. Its home page is created with no
  // tiles (the user adds them in the editor once they have the entities) instead
  // of the setup demanding a light, a blind or a thermostat it cannot have.
  const resolved = resolve('room', {
    areaId: 'bedroom', hass: installation({ kitchen: false, lights: false }),
  });
  const home = resolved.pages.find((page) => page.role === 'home');
  assert.deepEqual(home.panel.items, []);
  assert.deepEqual(resolved.blocked, []);
  assert.equal(resolved.ready, true);
  assert.equal(resolved.config.home_panel, home.key);
  assert.ok(!resolved.warnings.some((warning) => /no entity for/.test(warning)));
  // The idle clock still comes with it.
  assert.ok(resolved.pages.some((page) => page.role === 'idle'));
});

test('a page for an entity the installation has comes with the setup', () => {
  const room = resolve('room');
  assert.ok(room.pages.some((page) => page.id === 'climate'));
  // Its toggle is off unless the room has one: the bedroom has no thermostat.
  const bedroom = resolve('room', { areaId: 'bedroom' });
  assert.ok(!bedroom.pages.some((page) => page.id === 'climate'));
});

test('a toggle adds a page, and one that cannot be filled in blocks the setup', () => {
  const withMedia = resolve('room', { choices: { toggles: { media: true } } });
  assert.ok(withMedia.pages.some((page) => page.id === 'media'));
  // Forced on with no thermostat in the room: the page cannot be created.
  const bedroom = resolve('room', { areaId: 'bedroom', choices: { toggles: { climate: true } } });
  const climate = bedroom.pages.find((page) => page.id === 'climate');
  assert.deepEqual(climate.blocked, ['climate']);
  assert.equal(bedroom.ready, false);
});

test('a preset whose home page needs a required entity is blocked without it', () => {
  const resolved = resolve('security', { hass: installation({ alarm: false }) });
  assert.equal(resolved.ready, false);
  assert.deepEqual(resolved.blocked, ['alarm_control_panel']);
  const home = resolved.pages.find((page) => page.role === 'home');
  assert.equal(home.panel.item.item, '');
});

test('the alarm keypad keeps the alarm colours the theme already sets', () => {
  const palette = { background: 0, entity_on: 0xFFFF, component_pressed: 0x8410 };
  const home = resolve('security', { theme: palette }).pages
    .find((page) => page.role === 'home').panel;
  // The theme's label colour is chosen for the page background; a fill of the
  // preset's own would put it on a colour it was never picked for.
  assert.equal(home.arm_button_back_color, undefined);
  assert.equal(home.disarm_button_back_color, undefined);
});

test('the kitchen timer works without entities and can add a clock for idle', () => {
  const base = resolve('kitchen', { hass: {} });
  assert.equal(base.ready, true);
  assert.deepEqual(base.pages.map(({ panel }) => panel.type), ['timer']);
  assert.equal(base.pages[0].panel.show_notification, true);
  assert.equal(base.config.home_panel, base.pages[0].key);

  const withClock = resolve('kitchen', { hass: {}, choices: { toggles: { idle: true } } });
  assert.equal(withClock.pages.find(({ key }) => key === withClock.config.idle_panel).panel.type, 'clocktwo');
});

test('Guest Wi-Fi needs a network name, not an area or controllable entities', () => {
  const asked = resolve('guest', { hass: {} });
  assert.equal(asked.ready, false);
  assert.deepEqual(asked.needsInput.map((input) => input.key), ['essid']);
  const filled = resolve('guest', { hass: {}, choices: { essid: 'GuestNet', password: 'test-password' } });
  assert.equal(filled.ready, true);
  assert.deepEqual(filled.pages.map(({ panel }) => panel.type), ['qr']);
  const wifi = filled.pages[0].panel;
  assert.equal(wifi.essid, 'GuestNet');
  assert.equal(wifi.password, 'test-password');
  assert.equal(wifi.show_info, false);
  assert.equal(filled.config.home_panel, wifi.key);
});

test('the Status board is a row of the sensors that match each reading', () => {
  const board = resolve('status');
  const home = board.pages.find(({ role }) => role === 'home').panel;
  assert.equal(home.type, 'row');
  assert.deepEqual(home.items.map(({ item }) => item), [
    'sensor.outside', 'sensor.kitchen_humidity', 'sensor.plug_power', 'sensor.robot_battery',
  ]);
  assert.equal(board.pages.find(({ id }) => id === 'weather').panel.item.item, 'weather.home');
  // The forecast is a second idle panel, not a page to swipe to: the automatic page
  // switch cycles to it after the idle page.
  const weather = board.pages.find(({ id }) => id === 'weather');
  assert.equal(weather.panel.show_in_navigation, false);
  assert.equal(board.config.idle_panel_extra, weather.key);
  assert.equal(board.config.use_auto_page, true);
  assert.notEqual(board.config.idle_panel, weather.key);
});

test('an optional page that would show nothing is left out with a warning', () => {
  const resolved = resolve('home', { hass: installation({ lights: false, kitchen: false }) });
  assert.ok(!resolved.pages.some((page) => page.id === 'lights'));
  assert.deepEqual(resolved.dropped.map((page) => page.id), ['lights']);
  assert.match(resolved.warnings.join(' '), /Lights/);
});

test('pages are not navigation pages unless the setup puts them there', () => {
  const quiet = resolve('room');
  assert.ok(quiet.pages.filter((page) => page.role === 'page')
    .every((page) => page.panel.show_in_navigation === false));
  assert.equal(quiet.config.show_home_button, undefined);
  const navigated = resolve('room', { choices: { toggles: { navigation: true } } });
  assert.ok(navigated.pages.filter((page) => page.role === 'page')
    .every((page) => page.panel.show_in_navigation === undefined));
  assert.equal(navigated.config.show_home_button, true);
  // The idle panel is never a navigation page.
  assert.equal(navigated.pages.find((page) => page.role === 'idle').panel.show_in_navigation, false);
});

test('the settings only fill roles the device leaves open', () => {
  // The roles name panels the device has, so the preset keeps them.
  const resolved = resolve('room', {
    deviceConfig: {
      home_panel: 'grid_9', idle_panel: 'clock_1', use_auto_page: true, show_home_button: true,
    },
    taken: ['grid_9', 'clock_1'],
    choices: { toggles: { navigation: true } },
  });
  assert.deepEqual(resolved.config, {});
});

test('a role naming a panel the device no longer has is filled in', () => {
  const resolved = resolve('room', {
    deviceConfig: { home_panel: 'grid_9', idle_panel: 'clock_1' },
  });
  assert.equal(resolved.config.home_panel, 'room_kitchen');
  assert.equal(resolved.config.idle_panel, 'room_kitchen_clock');
});

test('keys are the area and the page, and never take one already in use', () => {
  const keys = presetKeys(preset('room'), 'Living Room');
  assert.equal(keys.get('home'), 'room_living_room');
  assert.equal(keys.get('climate'), 'room_living_room_climate');
  assert.equal(presetKeys(preset('room'), 'Living Room', ['room_living_room']).get('home'),
    'room_living_room_2');
  assert.equal(
    presetKeys(preset('room'), 'Living Room', ['room_living_room', 'room_living_room_2']).get('home'),
    'room_living_room_3',
  );
  // Without an area the preset's own key is the home page.
  assert.equal(presetKeys(preset('home')).get('home'), 'home');
  // A key that is taken moves the pages that hang off it too.
  assert.equal(presetKeys(preset('room'), 'Kitchen', ['room_kitchen']).get('clock'),
    'room_kitchen_clock');
});

test('an area preset without an area is not ready', () => {
  const resolved = resolve('room', { areaId: '' });
  assert.equal(resolved.ready, false);
  assert.equal(resolved.area, null);
});

test('every preset offers an idle panel, and its other switches only for pages that can fill', () => {
  for (const entry of presets()) {
    assert.ok(entry.toggles.some((toggle) => toggle.key === 'idle'), entry.key);
    assert.ok(entry.pages.some((page) => page.role === 'idle'), entry.key);
    for (const toggle of entry.toggles) {
      if (toggle.key === 'navigation' || toggle.key === 'idle') continue;
      // A page switch without a domain gate is one the user may still refuse;
      // nothing else is offered unconditionally.
      assert.ok(toggle.when || toggle.default === false, `${entry.key}/${toggle.key}`);
    }
  }
});
test('a setup is not ready while the panel types are missing, so a page is never saved unfilled', () => {
  // The editor resolves against the hub's descriptors: without them a page's
  // entity slots stay empty, and the hub refuses such a panel when it is saved.
  const resolved = resolve('room', { panelTypes: [] });
  assert.equal(resolved.ready, false);
  assert.ok(resolved.pages.every((page) => page.typeKnown === false));
  assert.match(resolved.warnings.join(' '), /panel types could not be loaded/);
  // A loaded list is what makes the same setup creatable.
  assert.equal(resolve('room').ready, true);
});

test('a room setup adds a detail page for its light and its blind, where it has one', () => {
  const kitchen = resolve('room');
  const light = kitchen.pages.find((page) => page.id === 'light');
  assert.equal(light.panel.type, 'light');
  assert.equal(light.panel.item.item, 'light.kitchen');
  assert.equal(kitchen.pages.find((page) => page.id === 'cover').panel.item.item, 'cover.kitchen');
  // The bedroom has a light and no blind, so it gets one page and one switch.
  const bedroom = resolve('room', { areaId: 'bedroom' });
  assert.ok(bedroom.pages.some((page) => page.id === 'light'));
  assert.ok(!bedroom.pages.some((page) => page.id === 'cover'));
  const toggles = Object.fromEntries(bedroom.toggles.map((toggle) => [toggle.key, toggle]));
  assert.equal(toggles.light.available, true);
  assert.equal(toggles.cover.available, false);
});

test('the whole-home setup adds a vacuum page for the robot it has', () => {
  const home = resolve('home');
  const vacuum = home.pages.find((page) => page.id === 'vacuum');
  assert.equal(vacuum.panel.type, 'vacuum');
  assert.equal(vacuum.panel.item.item, 'vacuum.robot');
  const robotless = resolve('home', {
    hass: { ...installation(), entities: {}, states: {} },
  });
  assert.ok(!robotless.pages.some((page) => page.id === 'vacuum'));
  assert.equal(robotless.toggles.find((toggle) => toggle.key === 'vacuum').available, false);
});

test('the idle panel shows the area weather and readings it has, without complaints', () => {
  const clock = resolve('room').pages.find((page) => page.role === 'idle').panel;
  assert.equal(clock.item.item, 'weather.home');
  // The area's own temperature is the inside reading; the rest are cards.
  assert.equal(clock.inside_temp_item.item, 'sensor.kitchen_temperature');
  assert.deepEqual(clock.items.map((item) => item.item), ['sensor.kitchen_humidity']);
  // Every card slot is optional, so a room without readings has no warning.
  const bare = resolve('room', {
    hass: { ...installation(), states: {} },
  });
  assert.ok(!bare.warnings.some((warning) => /Clock/.test(warning)));
});

test('a page takes the colours of the theme the device draws in', () => {
  const palette = { background: 0, entity_on: 0xFFFF, header_accent: 0xF800 };
  const themed = resolve('room', { theme: palette });
  const home = themed.pages.find((page) => page.role === 'home');
  // A grid tile's on background and power button are the hub's own theme colours,
  // so a preset stores neither: a stored one would pin the tile to the theme the
  // setup was created in.
  for (const item of home.panel.items) {
    assert.ok(!('back_color' in item), item.item);
    assert.ok(!('power_color' in item), item.item);
  }
  const clockTwo = resolve('home', { theme: palette }).pages.find((page) => page.role === 'idle').panel;
  assert.equal(clockTwo.special_color, '#ff0000');
  // The unlit letters follow the picture the panel is drawn on, so no tone is
  // stored: the theme's muted text tone reads as a lit letter on a light page.
  assert.ok(!('off_color' in clockTwo));
});
