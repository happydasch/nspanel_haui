import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import { quickStartPresets, quickStartThemes } from '../../custom_components/nspanel_haui/frontend/quick-start-flow.js';
import { jsonResponse, makeHost } from './fake-host.mjs';
import { registryWorld } from './support/hass.mjs';
import { render } from './support/render.mjs';

/** The hub's option descriptors for the types the presets use. */
const PANEL_TYPES = [
  { type_key: 'timer', label: 'Timer', options: [] },
  { type_key: 'grid', label: 'Grid', icon: 'mdi:grid', description: 'Tiles', options: [{ key: 'items', kind: 'item_list' }] },
  { type_key: 'row', label: 'Row', icon: 'mdi:format-list-bulleted', description: 'Rows', options: [{ key: 'items', kind: 'item_list' }] },
  {
    type_key: 'clock',
    label: 'Clock',
    icon: 'mdi:clock-outline',
    description: 'A digital clock',
    options: [
      { key: 'item', kind: 'item', domain: 'weather' },
      { key: 'inside_temp_item', kind: 'item', domain: 'sensor' },
      { key: 'items', kind: 'item_list', max_items: 6 },
    ],
  },
  { type_key: 'clocktwo', label: 'Clock Two', options: [] },
  {
    type_key: 'weather',
    label: 'Weather',
    options: [
      { key: 'item', kind: 'item', domain: 'weather' },
      { key: 'inside_temp_item', kind: 'item', domain: 'sensor' },
      { key: 'info_items', kind: 'item_list', max_items: 2 },
    ],
  },
  { type_key: 'climate', label: 'Climate', options: [{ key: 'item', kind: 'item', domain: 'climate', required: true }] },
  { type_key: 'light', label: 'Light', options: [{ key: 'item', kind: 'item', domain: 'light', required: true }] },
  { type_key: 'cover', label: 'Cover', options: [{ key: 'item', kind: 'item', domain: 'cover', required: true }] },
  {
    type_key: 'qr',
    label: 'QR',
    options: [
      { key: 'essid', kind: 'str', label: 'WiFi SSID', required: true },
      { key: 'password', kind: 'str' },
    ],
  },
];

/** The registry records and states the presets resolve against. */
function world() {
  const entities = [
    { entity_id: 'light.kitchen', area_id: 'kitchen' },
    { entity_id: 'switch.kettle', area_id: 'kitchen' },
    { entity_id: 'cover.kitchen', area_id: 'kitchen' },
    { entity_id: 'climate.kitchen', area_id: 'kitchen' },
    { entity_id: 'sensor.kitchen_temperature', area_id: 'kitchen' },
    { entity_id: 'light.bedroom', area_id: 'bedroom' },
    { entity_id: 'weather.home' },
  ];
  return {
    ...registryWorld({
      areas: [
        { area_id: 'bedroom', name: 'Bedroom' },
        { area_id: 'kitchen', name: 'Kitchen', temperature_entity_id: 'sensor.kitchen_temperature' },
      ],
      entities,
    }),
    states: Object.fromEntries(entities.map((entry) => [entry.entity_id, { state: 'on' }])),
  };
}

/** The built-in colour themes, as the editor's theme library holds them. */
const THEMES = {
  dark: { name: 'Dark', colors: { background: 0x0000, entity_on: 0xffff } },
  ocean: { name: 'Ocean', colors: { background: 0x0010, entity_on: 0x07ff } },
};

/**
 * A host on a device without panels, with the registries and states that fill
 * the presets' entity slots.
 */
function hostFor(respond, { panels = [], config = {} } = {}) {
  const store = { devices: { kitchen: { config: { home_panel: '', idle_panel: '', ...config }, panels } } };
  const host = makeHost(store, respond);
  Object.setPrototypeOf(host, NSPanelEditor.prototype);
  host._store = host.store;
  host._builtinThemes = THEMES;
  host.hass = { ...host.hass, ...world() };
  host.store.setState((state) => ({
    ...state,
    hub: { ...state.hub, panelTypes: PANEL_TYPES },
    devices: {
      ...state.devices,
      byName: {
        ...state.devices.byName,
        kitchen: {
          ...state.devices.byName.kitchen,
          config: { ...state.devices.byName.kitchen.config, ...config },
        },
      },
    },
  }));
  return host;
}

/** Answer the editor's panel and device saves, refusing them when `refuse`. */
function saver({ refuse = null } = {}) {
  return (method, path, opts = {}) => {
    const body = opts.body ? JSON.parse(opts.body) : {};
    if (refuse === 'panels' && method === 'PUT' && path.includes('/panels/')) {
      return jsonResponse({ error: 'Panels refused', field_errors: [] }, 400);
    }
    if (refuse === 'device' && method === 'PUT' && path.includes('/devices/')) {
      return jsonResponse({ error: 'Settings refused', field_errors: [] }, 400);
    }
    // The hub answers with what it stored, which is what the store applies.
    if (method === 'PUT' && path.includes('/panels/')) return jsonResponse({ panels: body.panels || [] });
    if (method === 'PUT' && path.includes('/devices/')) return jsonResponse({ config: body.config || {} });
    return jsonResponse({});
  };
}

/** @param {any} host */
const byKey = (host) => Object.fromEntries((host._quickStartPresets || []).map((entry) => [entry.key, entry]));

test('opening the quick start offers every configuration, resolved with the first area', () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  assert.equal(host._quickStartTarget, 'kitchen');
  assert.deepEqual(Object.keys(byKey(host)), ['room', 'home', 'status', 'security', 'kitchen', 'guest']);
  // The first area is preselected, and the room preset resolves against it.
  assert.equal(host._quickStartChoices.areaId, 'bedroom');
  assert.deepEqual(host._quickStartAreas.map((area) => area.area_id), ['bedroom', 'kitchen']);
  // Every card carries the hub's render of the page it creates.
  assert.ok(byKey(host).room.preview);
});

test('choosing a configuration resolves it with what the user picked', () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  const resolution = host._quickStartResolution;
  assert.equal(resolution.preset, 'room');
  assert.equal(resolution.areaName, 'Kitchen');
  assert.equal(resolution.ready, true);
  // The gallery lists the home screen first, then the idle panel, then the
  // pages reached from the header.
  assert.deepEqual(resolution.pages.map((page) => page.key),
    ['room_kitchen', 'room_kitchen_clock', 'room_kitchen_light', 'room_kitchen_cover',
      'room_kitchen_climate']);
  assert.equal(resolution.config.home_panel, 'room_kitchen');
  assert.equal(resolution.config.idle_panel, 'room_kitchen_clock');
  assert.ok(resolution.preview);
});

test('the setup offers the hub’s themes, preselected with the device’s own', () => {
  const host = hostFor(saver(), { config: { theme_id: 'ocean' } });
  host._openQuickStart('kitchen');
  // The theme the device draws in is what the dialog starts with.
  assert.equal(host._quickStartChoices.themeId, 'ocean');
  assert.deepEqual(quickStartThemes(host).map((option) => option.value), ['dark', 'ocean']);
});

test('a theme the library does not know yet stays selectable', () => {
  const host = hostFor(saver(), { config: { theme_id: 'my-theme' } });
  host._openQuickStart('kitchen');
  // The library may still be loading: the device's own theme is in the list.
  assert.deepEqual(quickStartThemes(host).map((option) => option.value),
    ['dark', 'ocean', 'my-theme']);
});

test('choosing a theme resolves the setup in it and writes it to the device', async () => {
  const host = hostFor(saver(), { config: { theme_id: 'dark' } });
  await host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen', themeId: 'ocean' });

  const resolution = host._quickStartResolution;
  // The device settings carry the new theme; its own theme writes nothing.
  assert.equal(resolution.config.theme_id, 'ocean');
  // The pages are rendered in it, without carrying it themselves.
  const preview = render(resolution.preview).querySelector('nspanel-simulator-frame').panel;
  assert.equal(preview.theme_id, 'ocean');
  assert.equal(resolution.pages[0].panel.theme_id, undefined);

  await host._createFromPreset();
  const saved = host.store.getState().devices.byName.kitchen;
  assert.equal(saved.config.theme_id, 'ocean');
});

test('keeping the device’s theme writes no theme setting', () => {
  const host = hostFor(saver(), { config: { theme_id: 'dark' } });
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  assert.equal(host._quickStartResolution.config.theme_id, undefined);
});

test('every page tells the gallery its render, its role and the panel type behind it', () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  const [home, clock, light] = host._quickStartResolution.pages;
  assert.equal(home.node, 'home');
  assert.equal(clock.node, 'idle');
  // Navigation is off, so the light's page is stacked: the home screen opens it.
  assert.equal(light.node, 'hidden');
  assert.equal(home.typeLabel, 'Grid');
  assert.equal(home.typeDescription, 'Tiles');
  assert.equal(light.typeLabel, 'Light');
  assert.equal(home.entityCount, home.filled);
  assert.equal(light.entityCount, 1);
  assert.ok(home.preview);
  assert.ok(light.preview);
  // A switch for a page the area could never fill is not offered.
  const bedroom = resolveBedroom(host);
  const toggles = Object.fromEntries(bedroom.toggles.map((toggle) => [toggle.key, toggle]));
  assert.equal(toggles.light.available, true);
  assert.equal(toggles.cover.available, false);
});

test('a second idle panel is listed with the idle panels, not with the swiped pages', () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'status' });
  const pages = host._quickStartResolution.pages;
  const weather = pages.find((page) => page.id === 'weather');
  // The automatic page switch cycles the forecast after the idle page: the
  // gallery marks it as an idle panel and it is not reachable by swiping.
  assert.equal(weather.node, 'idle');
  assert.equal(weather.panel.show_in_navigation, false);
  assert.equal(host._quickStartResolution.config.idle_panel_extra, weather.key);
});

/** The room preset resolved against the bedroom, as the dialog would show it. */
function resolveBedroom(host) {
  host._applyQuickStartChoices({ areaId: 'bedroom' });
  const resolution = host._quickStartResolution;
  return resolution;
}

test('choosing another configuration starts from its own switches', () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', toggles: { idle: false } });
  assert.deepEqual(host._quickStartChoices.toggles, { idle: false });
  host._applyQuickStartChoices({ preset: 'guest' });
  assert.deepEqual(host._quickStartChoices.toggles, {});
});

test('creating a setup saves its pages and the settings that make them work', async () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  await host._createFromPreset();
  const saved = host.store.getState().devices.byName.kitchen;
  assert.deepEqual(saved.panels.map((panel) => panel.key),
    ['room_kitchen', 'room_kitchen_light', 'room_kitchen_cover', 'room_kitchen_climate',
      'room_kitchen_clock']);
  assert.equal(saved.panels[0].title, 'Kitchen');
  assert.equal(saved.panels[0].items[0].item, 'light.kitchen');
  // The idle panel is not a navigation page.
  assert.equal(saved.panels.find((panel) => panel.key === 'room_kitchen_clock').show_in_navigation, false);
  assert.equal(saved.config.home_panel, 'room_kitchen');
  assert.equal(saved.config.idle_panel, 'room_kitchen_clock');
  assert.equal(saved.config.use_auto_page, true);
  assert.equal(host._selectedPanelKey, 'room_kitchen');
  // The dialog closes once the setup is saved, and says what it added where.
  assert.equal(host._quickStartTarget, null);
  assert.deepEqual(host._newPanelKeys, saved.panels.map((panel) => panel.key));
  assert.ok(host.toasts.some(([type, message]) => type === 'success' && /Added 5 pages to/.test(message)));
  assert.ok(host.calls.some((call) => call.startsWith('PUT') && call.includes('/panels/')));
  assert.ok(host.calls.some((call) => call.startsWith('PUT') && call.includes('/devices/')));
});

test('a device whose home or idle panel is gone gets them filled in', async () => {
  const host = hostFor(saver(), {
    config: { home_panel: 'clock_9', idle_panel: 'clock_8', use_auto_page: true },
  });
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  await host._createFromPreset();
  const saved = host.store.getState().devices.byName.kitchen;
  // The configured keys name no panel of the device, so it holds neither role.
  assert.equal(saved.config.home_panel, 'room_kitchen');
  assert.equal(saved.config.idle_panel, 'room_kitchen_clock');
  // Auto page is already on, so the settings write leaves it as it is.
  assert.equal(saved.config.use_auto_page, true);
});

test('a refused save leaves the device without the pages or the settings', async () => {
  const host = hostFor(saver({ refuse: 'panels' }));
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  await host._createFromPreset();
  const saved = host.store.getState().devices.byName.kitchen;
  assert.equal(saved.panels.length, 0);
  assert.equal(saved.config.home_panel, '');
  assert.match(host._quickStartError, /panels/i);
  assert.equal(host._quickStartTarget, 'kitchen');
});

test('pages saved but settings refused are kept, and the failure is reported', async () => {
  const host = hostFor(saver({ refuse: 'device' }));
  host._openQuickStart('kitchen');
  host._applyQuickStartChoices({ preset: 'room', areaId: 'kitchen' });
  await host._createFromPreset();
  const saved = host.store.getState().devices.byName.kitchen;
  assert.equal(saved.panels.length, 5);
  assert.equal(saved.config.home_panel, '');
  assert.match(host._quickStartError, /device settings/i);
  assert.equal(host._quickStartTarget, 'kitchen');
});

test('Guest Wi-Fi previews a sample before saving the actual network details', async () => {
  const host = hostFor(saver());
  await host._openQuickStart('kitchen');
  const previewPanel = (preview) => render(preview).querySelector('nspanel-simulator-frame').panel;
  const sample = previewPanel(byKey(host).guest.preview);
  assert.equal(sample.type, 'qr');
  assert.equal(sample.start_big_qr, true);
  assert.equal(sample.key, '');
  assert.ok(!('essid' in sample));
  assert.ok(!('password' in sample));

  host._applyQuickStartChoices({ preset: 'guest' });
  assert.deepEqual(previewPanel(host._quickStartResolution.preview), sample);
  assert.equal(host._quickStartResolution.ready, false);
  await host._createFromPreset();
  assert.equal(host.store.getState().devices.byName.kitchen.panels.length, 0);
  assert.match(host._quickStartError, /not ready/i);
  host._applyQuickStartChoices({ essid: 'MyNet', password: 'test-password' });
  assert.equal(host._quickStartResolution.ready, true);
  assert.deepEqual(previewPanel(byKey(host).guest.preview), sample);
  assert.deepEqual(previewPanel(host._quickStartResolution.preview), sample);
  await host._createFromPreset();
  const saved = host.store.getState().devices.byName.kitchen;
  assert.deepEqual(saved.panels.map(({ type }) => type), ['qr']);
  assert.equal(saved.panels[0].essid, 'MyNet');
  assert.equal(saved.panels[0].password, 'test-password');
  assert.equal(saved.config.home_panel, saved.panels[0].key);
});

test('closing the quick start forgets the device it set up', () => {
  const host = hostFor(saver());
  host._openQuickStart('kitchen');
  host._closeQuickStart();
  assert.equal(host._quickStartTarget, null);
  assert.deepEqual(host._quickStartPresets, []);
  assert.equal(host._quickStartChoices, null);
  assert.equal(host._quickStartResolution, null);
});
test('opening the quick start loads the panel types the presets are filled in with', async () => {
  const respond = (method, path, opts = {}) => (path === '/api/nspanel_haui/panel_types'
    ? jsonResponse(PANEL_TYPES)
    : saver()(method, path, opts));
  const host = hostFor(respond);
  // A reload of the editor has the hub's panels but not its panel types yet.
  host.store.setState((state) => ({ ...state, hub: { ...state.hub, panelTypes: [] } }));

  await host._openQuickStart('kitchen');

  assert.ok(host.calls.includes('GET /api/nspanel_haui/panel_types'));
  // The bedroom's home screen is rendered from them into the card.
  assert.ok(byKey(host).room.preview);
});

test('the chooser lists every configuration even when there is nothing to render', () => {
  const host = hostFor(saver());
  // The device the dialog is for is not in the store (a stale link, a device
  // removed meanwhile): the cards keep their placeholder instead of vanishing.
  host._quickStartTarget = 'gone';
  host._quickStartChoices = { preset: null, areaId: 'kitchen', toggles: {}, essid: '', password: '' };

  const presets = quickStartPresets(host);

  assert.deepEqual(presets.map((entry) => entry.key), ['room', 'home', 'status', 'security', 'kitchen', 'guest']);
  assert.ok(presets.every((entry) => entry.preview === null));
  assert.ok(presets.every((entry) => entry.label));
});
