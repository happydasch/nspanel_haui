import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatXFloat, textSegments } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-view.js';

test('text splits into plain and icon segments', () => {
  const iconCharacter = '';
  const iconName = (character) => character === iconCharacter ? 'lightbulb' : null;
  assert.deepEqual(textSegments(iconCharacter + '21°C', iconName), [
    { icon: 'lightbulb', char: iconCharacter },
    { text: '21°C' },
  ]);
  assert.deepEqual(textSegments('', iconName), [{ icon: null, char: '' }]);
  assert.deepEqual(textSegments('', iconName), []);
});

test('icons mapped outside the private-use range still resolve by name', () => {
  const horizontalBlinds = String.fromCharCode(0xFA2A);
  assert.deepEqual(textSegments(horizontalBlinds, () => 'blinds-horizontal'), [
    { icon: 'blinds-horizontal', char: horizontalBlinds },
  ]);
});

test('xfloat values use their decimals', () => {
  assert.equal(formatXFloat({ val: 215, vvs0: 0, vvs1: 1 }), '21.5');
  assert.equal(formatXFloat({ val: -5, vvs0: 0, vvs1: 1 }), '-0.5');
  assert.equal(formatXFloat({ val: 7, vvs0: 2, vvs1: 0 }), '07');
});
