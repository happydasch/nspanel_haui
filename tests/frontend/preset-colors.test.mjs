import { test } from 'node:test';
import assert from 'node:assert/strict';

import { hexToRgb565, mixHex, rgb565ToHex } from '../../custom_components/nspanel_haui/frontend/color-utils.js';
import {
  paletteHex, themePalette, tileColors,
} from '../../custom_components/nspanel_haui/frontend/preset-colors.js';

/** A built-in theme library as the hub serves it: RGB565 colours per theme. */
const BUILTINS = {
  dark: { name: 'Dark', colors: { background: 0x0000, entity_on: 0xFFFF, header_accent: 0xF800 } },
  light: { name: 'Light', colors: { background: 0xFFFF, entity_on: 0x07E0 } },
};

test('a theme palette is the device theme, the built-in of its id, or the dark default', () => {
  const custom = { name: 'Mine', colors: { background: 0x001F } };
  assert.equal(themePalette({ mine: custom }, BUILTINS, 'mine'), custom.colors);
  assert.equal(themePalette({}, BUILTINS, 'light'), BUILTINS.light.colors);
  // A device on the default theme draws in dark.
  assert.equal(themePalette({}, BUILTINS, ''), BUILTINS.dark.colors);
  // A theme the library no longer has falls back to the same default.
  assert.equal(themePalette({}, BUILTINS, 'gone'), BUILTINS.dark.colors);
  assert.equal(themePalette({}, {}, 'dark'), null);
});

test('palette entries read as hex colours, whatever the theme stores', () => {
  assert.equal(paletteHex({ header_accent: 0xF800 }, 'header_accent'), '#ff0000');
  assert.equal(paletteHex({ header_accent: '#00ff00' }, 'header_accent'), '#00ff00');
  assert.equal(paletteHex({}, 'header_accent'), '');
  assert.equal(paletteHex(null, 'header_accent'), '');
});

test('a tile is coloured for its active state, and unset without a palette', () => {
  assert.deepEqual(tileColors(null), {});
  // A theme without the colours a tint needs leaves the device defaults alone.
  assert.deepEqual(tileColors({ background: 0x0000 }), {});
  const colors = tileColors(BUILTINS.dark.colors);
  // Off keeps the page background, so only the active states are keyed.
  assert.deepEqual(Object.keys(colors.back_color), ['on', 'playing']);
  assert.equal(colors.back_color.on, colors.back_color.playing);
  assert.equal(colors.power_color, '#ffffff');
  // The tint is the page background lifted towards the theme's on colour.
  assert.notEqual(colors.back_color.on, '#000000');
  assert.notEqual(colors.back_color.on, '#ffffff');
});

test('mixHex blends two colours and refuses anything else', () => {
  assert.equal(mixHex('#000000', '#ffffff', 0), '#000000');
  assert.equal(mixHex('#000000', '#ffffff', 1), '#ffffff');
  assert.equal(mixHex('#000000', '#ffffff', 0.5), '#808080');
  assert.equal(mixHex('red', '#ffffff', 0.5), '');
});

test('an RGB565 colour survives a round trip through hex', () => {
  for (const value of [0x0000, 0xF800, 0x07E0, 0x001F, 0xFFFF]) {
    assert.equal(hexToRgb565(rgb565ToHex(value)), value);
  }
});
