import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { NextionDisplay } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-display.js';
import { color, formatXFloat, renderDisplay, textSegments } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-view.js';
import { paintedFills } from './support/canvas.mjs';
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
  // A lone fill is a box: a canvas per rectangle would cost more than the box.
  const fill = container.querySelector('.vp-widget[style*="left:10px"]');
  assert.ok(fill, 'the fill is drawn');
  assert.match(fill.getAttribute('style'), /top:20px/);
  assert.match(fill.getAttribute('style'), /background:#ffffff/);
});

test('a run of fills becomes one canvas, placed over the runs own box', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, {
    scheduler: { every: () => 0, cancel: () => {} },
    onChange: () => {},
    onWarn: () => {},
  });
  display.gotoPage('grid');
  // A picture is thousands of adjacent runs: one node, painted at display pixels.
  display.exec(['fill 10,10,4,4,65535', 'fill 14,10,4,4,0', 'fill 10,14,4,4,0',
    'fill 14,14,4,4,65535', 'fill 18,10,4,4,0', 'fill 18,14,4,4,0',
    'fill 22,10,4,4,0', 'fill 22,14,4,4,0']);
  const container = render(renderDisplay(display, {
    iconName: () => null,
    pictureUrl: () => '',
  }));
  const layer = container.querySelector('canvas.vp-drawing-layer');
  assert.ok(layer, 'the run is one canvas');
  assert.equal(layer.width, 16, 'the canvas covers the runs, not the whole screen');
  assert.equal(layer.height, 8);
  assert.match(layer.getAttribute('style'), /left: ?10px/);
  // The first fill is the run's own origin, so it paints at 0,0 of the canvas.
  assert.deepEqual(paintedFills(layer)[0], { x: 0, y: 0, w: 4, h: 4, fill: color(65535) });
  assert.deepEqual(paintedFills(layer)[1], { x: 4, y: 0, w: 4, h: 4, fill: color(0) });
});

test('a picture is repainted only when the fills changed', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, {
    scheduler: { every: () => 0, cancel: () => {} },
    onChange: () => {},
    onWarn: () => {},
  });
  display.gotoPage('grid');
  const runs = [];
  for (let i = 0; i < 12; i += 1) runs.push(`fill ${10 + i * 2},10,2,2,65535`);
  display.exec(runs);
  const container = render(renderDisplay(display, { iconName: () => null, pictureUrl: () => '' }));
  const layer = container.querySelector('canvas.vp-drawing-layer');
  const before = paintedFills(layer);

  // A widget update elsewhere re-renders the screen but leaves the picture alone.
  display.exec('bUp.vis=0');
  render(renderDisplay(display, { iconName: () => null, pictureUrl: () => '' }), container);

  assert.deepEqual(paintedFills(layer), before, 'the same picture is not repainted');
});

test('a frame that only adds fills paints them into the canvas that is there', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, {
    scheduler: { every: () => 0, cancel: () => {} },
    onChange: () => {},
    onWarn: () => {},
  });
  display.gotoPage('grid');
  const runs = [];
  for (let i = 0; i < 12; i += 1) runs.push(`fill ${10 + i * 2},10,2,2,65535`);
  display.exec(runs);
  const container = render(renderDisplay(display, { iconName: () => null, pictureUrl: () => '' }));
  const layer = container.querySelector('canvas.vp-drawing-layer');
  assert.equal(paintedFills(layer).length, 12);

  // A camera stream sends only what moved, and the picture stays on its canvas:
  // the frame's rectangles are painted into it, the rest of the picture is not.
  display.exec('fill 10,11,2,1,0');
  render(renderDisplay(display, { iconName: () => null, pictureUrl: () => '' }), container);

  assert.equal(container.querySelector('canvas.vp-drawing-layer'), layer, 'the canvas is kept');
  const painted = paintedFills(layer);
  assert.equal(painted.length, 13, 'only the fill the frame added is painted');
  assert.deepEqual(painted.at(-1), { x: 0, y: 1, w: 2, h: 1, fill: color(0) });
});

test('a clearing fill replaces the picture under it instead of stacking on it', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, {
    scheduler: { every: () => 0, cancel: () => {} },
    onChange: () => {},
    onWarn: () => {},
  });
  display.gotoPage('grid');
  // An image is its clear fill plus details; a later clear over the same
  // rectangle leaves nothing of the old picture to draw or to keep.
  const details = [];
  for (let i = 1; i < 9; i += 1) details.push(`fill ${10 + i},12,1,1,0`);
  display.exec(['fill 10,10,20,20,65535', ...details, 'fill 10,10,20,20,4226']);
  const container = render(renderDisplay(display, {
    iconName: () => null,
    pictureUrl: () => '',
  }));
  assert.equal(display.drawings.length, 1, 'the log is the new clear alone');
  // One fill is a box, not a canvas: the cleared rectangle is one colour.
  const fill = container.querySelector('.vp-widget[style*="left:10px"]');
  assert.match(fill.getAttribute('style'), /width:20px/);
  assert.match(fill.getAttribute('style'), new RegExp(`background:${color(4226)}`));
  assert.equal(container.querySelector('canvas.vp-drawing-layer'), null);
});

test('a widget update renders over the image and leaves the image around it', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, {
    scheduler: { every: () => 0, cancel: () => {} },
    onChange: () => {},
    onWarn: () => {},
  });
  display.gotoPage('clock');
  const time = display.component('tTime').attrs;
  const runs = ['fill 0,0,480,320,65535'];
  for (let i = 1; i < 12; i += 1) runs.push(`fill ${i * 4},0,4,4,65535`);
  display.exec([...runs, 'tTime.txt="12:00"']);
  const container = render(renderDisplay(display, {
    iconName: () => null,
    pictureUrl: () => '',
  }));
  const layers = [...container.querySelectorAll('canvas.vp-drawing-layer')];
  assert.ok(layers.length > 0, 'the image outside the widget survives');
  for (const layer of layers) {
    const left = Number(/left: ?(-?\d+)px/.exec(layer.getAttribute('style'))[1]);
    const top = Number(/top: ?(-?\d+)px/.exec(layer.getAttribute('style'))[1]);
    for (const fill of paintedFills(layer)) {
      const x = left + fill.x;
      const y = top + fill.y;
      const overlaps = x < time.x + time.w && x + fill.w > time.x
        && y < time.y + time.h && y + fill.h > time.y;
      assert.equal(overlaps, false, 'the fill does not cover the repainted widget');
    }
  }
  assert.ok(container.textContent.includes('12:00'), 'the widget itself is rendered');
});

test('repainting a widget between fill runs keeps the surviving canvas pixels', () => {
  const layout = JSON.parse(readFileSync(
    new URL('../../custom_components/nspanel_haui/frontend/virtual/layout_landscape.json', import.meta.url),
    'utf8',
  ));
  const display = new NextionDisplay(layout, { scheduler: { every: () => 0, cancel: () => {} } });
  display.gotoPage('grid');
  display.exec(Array.from({ length: 7 }, (_, i) => 'fill ' + (101 + i) + ',100,1,1,2016'));
  display.exec('cirs 10,10,2,65535');
  display.exec(Array.from({ length: 8 }, (_, i) => i % 2 ? 'fill 100,100,1,1,63488' : 'fill 108,100,1,1,63488'));
  const frame = () => renderDisplay(display, { iconName: () => null, pictureUrl: () => '' });
  const container = render(frame());

  display.exec('ref tHeader');
  render(frame(), container);

  const painted = paintedFills(container.querySelector('canvas.vp-drawing-layer'));
  assert.equal(painted.findLast(r => r.x === 3 && r.y === 0)?.fill, color(2016));
  assert.equal(painted.findLast(r => r.x === 8 && r.y === 0)?.fill, color(63488));
});
