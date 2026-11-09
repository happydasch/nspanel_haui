import './dom-shim.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { rgb565ToHex } from '../../custom_components/nspanel_haui/frontend/color-utils.js';
import { NextionDisplay } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-display.js';
import {
  backgroundStyle,
  formatXFloat,
  renderDisplay,
  textSegments,
} from '../../custom_components/nspanel_haui/frontend/virtual/nextion-view.js';

const LAYOUT = JSON.parse(readFileSync(
  new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
  'utf8',
));

/** Flatten a Lit TemplateResult tree to text. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  return v == null || typeof v === 'symbol' ? '' : String(v);
}

const LIGHTBULB = '';
const BLINDS_HORIZONTAL = '\uFA2A';
const ctx = {
  iconName: ch => (ch === LIGHTBULB ? 'lightbulb' : null),
  pictureUrl: id => `pictures/landscape/${id}.webp`,
};

function display(page) {
  const d = new NextionDisplay(LAYOUT, { scheduler: { every: () => 0, cancel() {} }, onWarn: () => {} });
  d.gotoPage(page);
  return d;
}

test('text splits into plain and icon segments', () => {
  assert.deepEqual(textSegments(`${LIGHTBULB}21°C`, ctx.iconName), [
    { icon: 'lightbulb', char: LIGHTBULB },
    { text: '21°C' },
  ]);
  assert.deepEqual(textSegments('', ctx.iconName), [{ icon: null, char: '' }]);
  assert.deepEqual(textSegments('', ctx.iconName), []);
});

test('icons mapped outside the private-use range still resolve by name', () => {
  assert.deepEqual(textSegments(BLINDS_HORIZONTAL, () => 'blinds-horizontal'), [
    { icon: 'blinds-horizontal', char: BLINDS_HORIZONTAL },
  ]);
});

test('xfloat values use their decimals', () => {
  assert.equal(formatXFloat({ val: 215, vvs0: 0, vvs1: 1 }), '21.5');
  assert.equal(formatXFloat({ val: -5, vvs0: 0, vvs1: 1 }), '-0.5');
  assert.equal(formatXFloat({ val: 7, vvs0: 2, vvs1: 0 }), '07');
});

test('widget fills: cropped picture, solid colour, picture, none', () => {
  const at = { x: 10, y: 20 };
  assert.equal(
    backgroundStyle({ sta: 0, picc: 3 }, at, ctx.pictureUrl),
    'background:url(pictures/landscape/3.webp) -10px -20px no-repeat;',
  );
  assert.equal(backgroundStyle({ sta: 1, bco: 0xffff }, at, ctx.pictureUrl), 'background:#ffffff;');
  assert.equal(
    backgroundStyle({ sta: 2, pic: 12 }, at, ctx.pictureUrl),
    'background:url(pictures/landscape/12.webp) 0 0 no-repeat;',
  );
  assert.equal(backgroundStyle({ sta: 0, picc: 65535 }, at, ctx.pictureUrl), '');
});

test('a grid page renders the hub\'s texts and icons and skips hidden widgets', () => {
  const d = display('grid');
  d.exec([
    'vis g1Btn,1', 'vis g1Icon,1', 'vis g1Name,1',
    'g1Name.txt="Lamp"', `g1Icon.txt="${LIGHTBULB}"`,
  ]);
  const out = flat(renderDisplay(d, ctx));
  assert.match(out, /<span>Lamp<\/span>/);
  assert.match(out, /icon="mdi:lightbulb"/);
  // Tiles 2-6 stay hidden by the page's Preinitialize code.
  assert.doesNotMatch(out, new RegExp(`data-comp=${d.component('g2Name').id}\\b`));
  assert.match(out, /width:450px;height:320px;/);
});

test('the clock page uses the background picture the hub selected', () => {
  const d = new NextionDisplay(LAYOUT, { scheduler: { every: () => 0, cancel() {} }, onWarn: () => {} });
  d.exec('system.vBackground.val=4');
  d.gotoPage('clock');
  d.exec('tTime.txt="12:34"');
  const out = flat(renderDisplay(d, ctx));
  assert.match(out, /class="vp-screen" style="width:450px;height:320px;background:url\(pictures\/landscape\/4\.webp\)/);
  assert.match(out, /<span>12:34<\/span>/);
});

test('a pressed button draws its pressed colours', () => {
  const d = display('cover');
  d.exec('vis bUp,1');
  const btn = d.component('bUp');
  const widget = () => flat(renderDisplay(d, ctx)).split(`data-comp=${btn.id} `)[1].split('>')[0];
  assert.ok(widget().includes(`background:${rgb565ToHex(btn.attrs.bco)};`));
  btn.pressed = true;
  assert.ok(widget().includes(`background:${rgb565ToHex(btn.attrs.bco2)};`));
});

test('drawings render above the widgets', () => {
  const d = display('light');
  d.exec('cirs 100,100,6,63488');
  const out = flat(renderDisplay(d, ctx));
  assert.match(out, /vp-circle" style="left:94px;top:94px;width:12px;height:12px;background:#ff0000;"/);
});
