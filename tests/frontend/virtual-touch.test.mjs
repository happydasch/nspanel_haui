import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { NextionDisplay } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-display.js';
import {
  detectGesture,
  entityAt,
  toDisplayCoords,
  TouchInput,
} from '../../custom_components/nspanel_haui/frontend/virtual/touch-input.js';

const load = o => JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/layout_${o}.json`, import.meta.url),
  'utf8',
));
const LANDSCAPE = load('landscape');
const PORTRAIT = load('portrait');

function setup(page, layout = LANDSCAPE) {
  const display = new NextionDisplay(layout, { scheduler: { every: () => 0, cancel() {} }, onWarn: () => {} });
  display.gotoPage(page);
  const sent = [];
  const touch = new TouchInput(display, (name, value) => sent.push([name, value]));
  return { display, touch, sent };
}

test('a tap on a grid tile reports the overlay hotspot and highlights the tile', () => {
  const { display, touch, sent } = setup('grid');
  display.exec(['vis g1Overlay,1', 'vis g1Btn,1', 'vis g1Name,1']);
  const btn = display.component('g1Btn').attrs;

  touch.press(40, 70);
  assert.equal(display.component('g1Name').attrs.bco, btn.bco2);
  touch.release(40, 70);
  assert.equal(display.component('g1Name').attrs.bco, btn.bco);

  assert.deepEqual(sent, [
    ['esphome.component', '9,11,1'],
    ['esphome.touch_start', '1'],
    ['esphome.touch_start', ''],
    ['esphome.component', '9,11,0'],
    ['esphome.touch_end', '40,70,40,70'],
  ]);
});

test('the topmost widget wins: the power button over the tile overlay', () => {
  const { display, touch, sent } = setup('grid');
  display.exec(['vis g1Overlay,1', 'vis g1Power,1']);
  touch.press(120, 70);
  touch.release(120, 70);
  assert.deepEqual(sent[0], ['esphome.component', '9,12,1']);
});

test('hidden and touch-disabled widgets are skipped', () => {
  const { display, touch, sent } = setup('grid');
  display.exec(['vis g1Overlay,1', 'vis g1Power,0']);
  touch.press(120, 70);
  touch.release(120, 70);
  assert.deepEqual(sent[0], ['esphome.component', '9,11,1']);

  sent.length = 0;
  display.exec('tsw g1Overlay,0');
  touch.press(120, 70);
  touch.release(120, 70);
  // Nothing else under the finger sends its id: only the raw touch is reported.
  assert.deepEqual(sent.map(([name]) => name), ['esphome.touch_start', 'esphome.touch_end']);
});

test('a widget without Send Component ID sends only the raw touch', () => {
  const { touch, sent } = setup('grid');
  touch.press(300, 300);
  touch.release(300, 300);
  assert.deepEqual(sent, [
    ['esphome.touch_start', ''],
    ['esphome.touch_end', '300,300,300,300'],
  ]);
});

test('a vertical slider follows the finger and its value is readable', () => {
  const { display, touch, sent } = setup('light');
  display.exec('vis hBrightness,1');
  const s = display.component('hBrightness').attrs;
  touch.press(s.x + 10, s.y + s.h - 1);
  touch.move(s.x + 10, s.y + s.h / 2);
  assert.equal(s.val, 51);
  touch.move(s.x + 10, s.y - 50);
  assert.equal(s.val, s.maxval);
  touch.release(s.x + 10, s.y - 50);
  assert.deepEqual(sent.filter(([n]) => n === 'esphome.component'), [
    ['esphome.component', `13,${display.component('hBrightness').id},1`],
    ['esphome.component', `13,${display.component('hBrightness').id},0`],
  ]);
  assert.equal(JSON.parse(display.readResponse('val', 'hBrightness')).value, 100);
});

test('a dual-state button toggles on press', () => {
  const { display, touch } = setup('row');
  display.exec(['vis r1Toggle,1', 'r1Toggle.val=0']);
  const t = display.component('r1Toggle').attrs;
  touch.press(t.x + 5, t.y + 5);
  touch.release(t.x + 5, t.y + 5);
  assert.equal(t.val, 1);
});

test('live touch reports physical button input without simulating local display changes', () => {
  const { display, sent } = setup('grid');
  display.exec(['vis g1Power,1', 'g1Power.val=0']);
  const component = display.component('g1Power');
  const before = component.attrs.val;
  const touch = new TouchInput(display, (name, value) => sent.push([name, value]), () => false);

  touch.press(component.attrs.x + 5, component.attrs.y + 5);
  touch.release(component.attrs.x + 5, component.attrs.y + 5);

  assert.equal(component.attrs.val, before);
  assert.deepEqual(sent.filter(([name]) => name === 'esphome.component'), [
    ['esphome.component', `9,${component.id},1`],
    ['esphome.component', `9,${component.id},0`],
  ]);
});

test('live slider drags send the selected value without simulating the display', () => {
  const display = new NextionDisplay(LANDSCAPE, {
    scheduler: { every: () => 0, cancel() {} },
    onWarn: () => {},
  });
  display.gotoPage('light');
  display.exec(['vis hBrightness,1', 'hBrightness.val=37']);
  const component = display.component('hBrightness');
  const sent = [];
  const touch = new TouchInput(
    display,
    (name, value) => sent.push([name, value]),
    () => false,
    (...args) => sent.push(['slider', ...args]),
  );

  touch.press(component.attrs.x + 10, component.attrs.y + component.attrs.h - 1);
  touch.move(component.attrs.x + 10, component.attrs.y + 5);
  touch.release(component.attrs.x + 10, component.attrs.y + 5);

  assert.equal(component.attrs.val, 98);
  assert.deepEqual(sent.filter(([name]) => name === 'slider'), [
    ['slider', 13, component.id, 98],
  ]);
  assert.deepEqual(sent.filter(([name]) => name === 'esphome.component'), [
    ['esphome.component', `13,${component.id},1`],
  ]);
});

test('live slider input stays disabled when no live slider handler is provided', () => {
  const display = new NextionDisplay(LANDSCAPE, {
    scheduler: { every: () => 0, cancel() {} },
    onWarn: () => {},
  });
  display.gotoPage('light');
  display.exec(['vis hBrightness,1', 'hBrightness.val=37']);
  const component = display.component('hBrightness');
  const before = component.attrs.val;
  const sent = [];
  const touch = new TouchInput(display, (name, value) => sent.push([name, value]), () => false);

  touch.press(component.attrs.x + 10, component.attrs.y + component.attrs.h - 1);
  touch.move(component.attrs.x + 10, component.attrs.y + 5);
  touch.release(component.attrs.x + 10, component.attrs.y + 5);

  assert.equal(component.attrs.val, before);
  assert.deepEqual(sent, []);
});

test('a swipe from the left edge reports swipe_right after the touch', () => {
  const { touch, sent } = setup('grid');
  touch.press(10, 200);
  touch.move(150, 205);
  touch.release(300, 210);
  assert.deepEqual(sent.slice(-2), [
    ['esphome.touch_end', '10,200,300,210'],
    ['esphome.gesture', 'swipe_right'],
  ]);
});

test('a cancelled pointer ends the touch without producing a swipe', () => {
  const { touch, sent } = setup('grid');
  touch.press(10, 200);
  touch.move(150, 205);
  touch.cancel();

  assert.equal(touch._touch, null);
  assert.ok(sent.some(([name]) => name === 'esphome.touch_end'));
  assert.equal(sent.some(([name]) => name === 'esphome.gesture'), false);
});

test('swipe detection follows the firmware thresholds', () => {
  // must start near an edge
  assert.equal(detectGesture(100, 160, 400, 160, LANDSCAPE), null);
  // horizontal needs 200 px, vertical 150 px
  assert.equal(detectGesture(10, 160, 190, 160, LANDSCAPE), null);
  assert.equal(detectGesture(200, 10, 200, 170, LANDSCAPE), 'swipe_down');
  // the right edge margin is measured from the visible width (450 landscape)
  assert.equal(detectGesture(420, 160, 200, 160, LANDSCAPE), 'swipe_left');
  assert.equal(detectGesture(270, 160, 20, 160, PORTRAIT), null);
  assert.equal(detectGesture(290, 160, 40, 160, PORTRAIT), 'swipe_left');
  // too steep for a horizontal swipe
  assert.equal(detectGesture(10, 100, 260, 230, LANDSCAPE), null);
  assert.equal(detectGesture(160, 470, 160, 200, PORTRAIT), 'swipe_up');
  assert.equal(detectGesture(0, 160, 300, 160, LANDSCAPE), null);
});

test('pointer positions map to display coordinates and never to 0', () => {
  const rect = { left: 100, top: 50, width: 900, height: 640 };
  assert.deepEqual(toDisplayCoords(550, 370, rect, LANDSCAPE), { x: 225, y: 160 });
  assert.deepEqual(toDisplayCoords(90, 40, rect, LANDSCAPE), { x: 1, y: 1 });
});

test('a new press first releases a touch that never ended', () => {
  const { touch, sent } = setup('grid');
  touch.press(300, 300);
  touch.press(310, 300);
  assert.deepEqual(sent.map(([n]) => n), [
    'esphome.touch_start', 'esphome.touch_end', 'esphome.touch_start',
  ]);
});

test('the entity under the mouse: the topmost linked widget, else the page entity', () => {
  const { display } = setup('grid');
  display.exec(['vis g1Overlay,1', 'vis g1Name,1', 'vis g1Power,1']);
  const map = { g1Overlay: 'light.lamp', '#page': 'sensor.page' };
  // over the tile's name: the overlay above it links the entity
  assert.equal(entityAt(display, map, 40, 150), 'light.lamp');
  // over the power button, which links nothing itself: still the tile below
  assert.equal(entityAt(display, map, 120, 70), 'light.lamp');
  // elsewhere on the page: the page's own entity
  assert.equal(entityAt(display, map, 300, 300), 'sensor.page');
  assert.equal(entityAt(display, {}, 300, 300), null);
  // hidden widgets link nothing
  display.exec('vis g1Overlay,0');
  assert.equal(entityAt(display, { g1Overlay: 'light.lamp' }, 40, 150), null);
});
