import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { NextionDisplay } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-display.js';
import { formatXFloat, renderDisplay, textSegments } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-view.js';
import { render } from './support/render.mjs';

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
test('a fill from a hub draw program renders on the virtual panel', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, {
    scheduler: { every: () => 0, cancel: () => {} },
    onChange: () => {},
    onWarn: () => {},
  });
  display.gotoPage(Number(Object.keys(layout.pages).find(id => layout.pages[id].name === 'grid')));
  display.exec('fill 10,20,20,20,65535');
  const container = render(renderDisplay(display, {
    iconName: () => null,
    pictureUrl: () => '',
  }));
  const fill = container.querySelector('[data-fill="65535"]');
  assert.ok(fill, 'the fill is drawn');
  assert.equal(fill.getAttribute('style').includes('left:10px'), true);
  assert.equal(fill.getAttribute('style').includes('width:20px'), true);
});

