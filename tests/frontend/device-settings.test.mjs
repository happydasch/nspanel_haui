import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';
import {
  SETTINGS_SECTIONS, settingsSection,
} from '../../custom_components/nspanel_haui/frontend/device-settings-sections.js';
import { render } from './support/render.mjs';

/** A settings instance without Lit's update cycle, rendered on demand. */
function settings(props = {}) {
  const events = [];
  const dlg = document.createElement('nspanel-device-settings');
  Object.assign(dlg, {
    requestUpdate() {}, dispatchEvent(event) { events.push(event); return true; },
  }, props);
  return { dlg, events };
}

test('the landing shows one tile per settings group and no field', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const { dlg } = settings({ config, _deviceConfigForm: config });
  const root = render(dlg.render());

  const tiles = [...root.querySelectorAll('[data-settings-tile]')];
  assert.deepEqual(tiles.map((tile) => tile.dataset.settingsTile), SETTINGS_SECTIONS.map((entry) => entry.key));
  // A tile is one button whose name is the group, with what the group holds under it.
  for (const [index, tile] of tiles.entries()) {
    assert.equal(tile.tagName, 'BUTTON');
    const name = SETTINGS_SECTIONS[index].label();
    assert.ok(tile.textContent.includes(name), `${name} tile names its group`);
    assert.ok(tile.textContent.includes(SETTINGS_SECTIONS[index].summary(config, {})), `${name} tile carries a value line`);
  }
  // Only the grid is on the landing: no group's fields are in the form.
  assert.equal(root.querySelector('#device-config-form input, #device-config-form select'), null);
  assert.equal(root.querySelector('#dc-brightness'), null);
});

test('a tile click asks the shell for that group', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const { dlg, events } = settings({ config, _deviceConfigForm: config });
  const root = render(dlg.render());

  root.querySelector('[data-settings-tile="screen"]')
    .dispatchEvent(new Event('click', { bubbles: true }));

  assert.equal(events.at(-1).type, 'section-change');
  assert.deepEqual(events.at(-1).detail, { section: 'screen' });
});

test('a group page renders only its own fields', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const section = (key) => render(settings({ config, _deviceConfigForm: config, section: key }).dlg.render());

  const screen = section('screen');
  assert.ok(screen.querySelector('#dc-brightness'));
  // The schedule is part of Screen: its entries close the group's page.
  assert.ok(screen.querySelector('#panel-schedule_add'));
  assert.equal(screen.querySelector('#panel-gesture_add'), null);
  assert.equal(screen.querySelector('#dc-log_level'), null);
  assert.equal(screen.querySelector('[data-settings-tile]'), null);

  const advanced = section('advanced');
  assert.ok(advanced.querySelector('#dc-log_level'));
  assert.equal(advanced.querySelector('#dc-brightness'), null);

  const gestures = section('gestures');
  assert.ok(gestures.querySelector('#panel-gesture_add'));
  assert.equal(gestures.querySelector('#panel-schedule_add'), null);
});

test('an unknown group is a bug, not a blank page', () => {
  assert.throws(() => settingsSection('nope'), /Unknown device settings section: nope/);
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const { dlg } = settings({ config, _deviceConfigForm: config, section: 'nope' });
  assert.throws(() => dlg.render(), /Unknown device settings section: nope/);
});
test('an untitled panel is named by its type, not by its key', () => {
  const clock = { key: 'clock_0', type: 'clock', items: [] };
  const weather = { key: 'weather_0', type: 'weather', items: [] };
  const panelTypes = [
    { type_key: 'clock', label: 'Clock' },
    { type_key: 'weather', label: 'Weather' },
  ];
  const config = { ...DEVICE_CONFIG_DEFAULTS, home_panel: 'clock_0' };

  // The tile line and the pills both carry the name the hub shows.
  assert.equal(settingsSection('home').summary(config, { panels: [clock, weather], panelTypes }), 'Clock · 0 idle panels');
  const root = render(settings({
    config, _deviceConfigForm: config, section: 'home',
    panels: [clock, weather], panelTypes,
  }).dlg.render());
  const homePill = root.querySelector('.haui-pill');
  assert.equal(homePill.textContent.trim(), 'Clock');
  assert.equal(root.querySelector('#dc-idle-panels option[value="weather_0"]').textContent, 'Weather');
});

test('a device without panels says so instead of drawing an empty picker', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const root = render(settings({ config, _deviceConfigForm: config, section: 'home', panels: [] }).dlg.render());

  // Neither role has anything to offer, and the usual hints talk about a first
  // navigation panel and an idle cycle that do not exist: name what is missing.
  assert.equal(root.querySelector('#dc-home-panel'), null);
  assert.equal(root.querySelector('#dc-idle-panels'), null);
  const notices = [...root.querySelectorAll('.haui-field-hint.is-persistent')].map((hint) => hint.textContent.trim());
  assert.deepEqual(notices, [
    'This device has no panels yet. Add a panel, then set the home panel here.',
    'This device has no panels yet. Add a panel, then set the idle panels here.',
  ]);
  // The tile that opens the group says it too, without an idle count.
  assert.equal(settingsSection('home').summary(config, { panels: [] }), 'No panels yet');
});

test('the General group edits the theme choice in the settings draft', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS };
  const { dlg } = settings({
    config, _deviceConfigForm: config, section: 'general',
    builtinThemes: { dark: {}, light: {}, black: {} },
    customThemes: { evening: { name: 'Evening' } },
  });
  const root = render(dlg.render());

  // The hub's built-in and custom themes are the list's options.
  const theme = root.querySelector('#dc-theme_id');
  assert.deepEqual([...theme.options].map((option) => [option.value, option.textContent.trim()]), [
    ['dark', 'Dark Color'], ['light', 'Light Color'], ['black', 'Black'], ['evening', 'Evening'],
  ]);

  theme.value = 'evening';
  theme.dispatchEvent(new Event('change', { bubbles: true }));
  assert.equal(dlg._deviceConfigForm.theme_id, 'evening');
});

test('the theme select keeps the stored theme while the library is still loading', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, theme_id: 'black' };
  const root = render(settings({ config, _deviceConfigForm: config, section: 'general' }).dlg.render());

  const theme = root.querySelector('#dc-theme_id');
  assert.deepEqual([...theme.options].map((option) => option.value), ['black']);
  assert.equal(theme.value, 'black');
});
test('a layout saved under its old name reads as its current one', () => {
  // `E`/`EEEE` were the weekday layouts before they became translation keys; a panel
  // stored under them has to show its layout, not an empty select.
  for (const [stored, current] of [['E', 'weekday_short'], ['EEEE', 'weekday_full']]) {
    const config = { ...DEVICE_CONFIG_DEFAULTS, date_format_locale: stored };
    const root = render(settings({ config, _deviceConfigForm: config, section: 'general' }).dlg.render());

    const layout = root.querySelector('#dc-date_format_locale');
    // The rendered selection, not `select.value`: happy-dom reports that getter stale.
    const selected = [...layout.options]
      .filter((option) => option.hasAttribute('selected'))
      .map((option) => option.value);
    assert.deepEqual(selected, [current], `${stored} reads as ${current}`);
    assert.ok(![...layout.options].some((option) => option.value === stored), `${stored} is not offered`);
  }
});


test('an empty brightness field names the brightness the panel uses', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, brightness: null, brightness_dim: null };
  const root = render(settings({
    config, _deviceConfigForm: config, section: 'screen',
    deviceBrightness: { full: 62, dimmed: 15 },
  }).dlg.render());

  assert.equal(root.querySelector('#dc-brightness').placeholder, 'Panel: 62');
  assert.equal(root.querySelector('#dc-brightness_dim').placeholder, 'Panel: 15');
});

test('a brightness field without a panel reading has no placeholder', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, brightness: 80, brightness_dim: null };
  const root = render(settings({ config, _deviceConfigForm: config, section: 'screen' }).dlg.render());

  assert.equal(root.querySelector('#dc-brightness').value, '80');
  assert.equal(root.querySelector('#dc-brightness_dim').placeholder, '');
});
