import test from 'node:test';
import assert from 'node:assert/strict';

import { tileBgColor, tileIconColor } from '../../custom_components/nspanel_haui/frontend/previews/utils.js';

test('tile colors resolve state-keyed values', () => {
  const host = { hass: { states: { 'light.lamp': { state: 'on' } } } };
  const item = {
    item: 'light.lamp',
    back_color: { on: '#ff0000', off: '#00ff00' },
    text_color: { on: '#ffffff', off: '#000000' },
  };

  assert.equal(tileBgColor(item, host), '#ff0000');
  assert.equal(tileIconColor(item, host), '#ffffff');
});

test('tile colors fall back to no override for unknown states', () => {
  const host = { hass: { states: { 'light.lamp': { state: 'unavailable' } } } };
  const item = {
    item: 'light.lamp',
    back_color: { on: '#ff0000', off: '#00ff00' },
  };

  assert.equal(tileBgColor(item, host), null);
});
