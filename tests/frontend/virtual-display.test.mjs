import './support/browser.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { NextionDisplay } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-display.js';

const LAYOUT_DIR = new URL('../../custom_components/nspanel_haui/frontend/virtual/', import.meta.url);
const ORIENTATIONS = ['landscape', 'portrait'];

function loadLayout(orientation) {
  return JSON.parse(readFileSync(new URL(`layout_${orientation}.json`, LAYOUT_DIR), 'utf8'));
}

function fakeScheduler() {
  const timers = new Map();
  let next = 1;
  return {
    timers,
    every(ms, fn) { timers.set(next, fn); return next++; },
    cancel(handle) { timers.delete(handle); },
    tick(times = 1) { for (let i = 0; i < times; i++) for (const fn of [...timers.values()]) fn(); },
  };
}

function makeDisplay(orientation = 'landscape') {
  const scheduler = fakeScheduler();
  let changes = 0;
  const display = new NextionDisplay(loadLayout(orientation), {
    scheduler,
    onChange: () => { changes++; },
    onWarn: () => {},
  });
  return { display, scheduler, changes: () => changes };
}

for (const orientation of ORIENTATIONS) {
  test(`every ${orientation} page's event code runs`, () => {
    const { display, scheduler } = makeDisplay(orientation);
    for (const id of Object.keys(display.layout.pages)) {
      display.gotoPage(Number(id));
      assert.equal(display.pageId, Number(id));
      for (const comp of display.components.values()) {
        if (comp.events.down) display.command('click', [comp.name, 1]);
        if (comp.events.up) display.command('click', [comp.name, 0]);
      }
      scheduler.tick(70);
    }
    assert.deepEqual(display.warnings, [], 'setup code may not touch a missing attribute');
  });
}

test('a picture page takes its background from the global set before the page loads', () => {
  const { display } = makeDisplay();
  // The hub sets the page's global background variable, then switches page
  // (clock_common.background_commands).
  display.exec('system.vBackground.val=5');
  display.gotoPage('clock');
  assert.equal(display.component('clock').attrs.pic, 5);
  assert.equal(display.component('tTime').attrs.picc, 5);
  assert.equal(display.component('pGrid').hidden, true);
});

test('a solid page loads in the theme set before the page switch', () => {
  const { display } = makeDisplay();
  // HAUIPage.prepare_page_load sends the theme globals, then the page switches;
  // the page's Preinitialize code paints itself with them before it is drawn.
  display.exec(['thmBg=4479', 'thmHdrBg=4228', 'thmPressed=6463']);
  display.gotoPage('grid');
  assert.equal(display.component('grid').attrs.bco, 4479);
  assert.equal(display.component('g1Name').attrs.bco, 4479);
  assert.equal(display.component('g1Btn').attrs.bco2, 6463);
  assert.equal(display.component('tHeader').attrs.bco, 4228);
});

test('an assignment to an undeclared variable is refused, as on the display', () => {
  const warnings = [];
  const display = new NextionDisplay(loadLayout('landscape'), {
    scheduler: fakeScheduler(),
    onWarn: (message) => warnings.push(message),
  });
  display.exec('noSuchVar=1');
  assert.equal('noSuchVar' in display.globals, false);
  assert.equal(warnings.length, 1);
  assert.match(warnings[0], /unknown variable noSuchVar/);
});

test('global-scope widgets keep their values across page changes', () => {
  const { display } = makeDisplay();
  display.gotoPage('system');
  display.exec('system.vBackground.val=4');
  display.gotoPage('grid');
  assert.equal(display.getAttr({ page: 'system', comp: 'vBackground', attr: 'val' }), 4);
  display.gotoPage('system');
  assert.equal(display.component('vBackground').attrs.val, 4);
});

test('a page\'s own setup code still runs over global-scope values', () => {
  const { display } = makeDisplay();
  display.gotoPage('settings');
  display.exec('hBrght.val=80');
  display.gotoPage('grid');
  display.gotoPage('settings');
  // settings' Preinitialize code sets hBrght.val=0; the hub then sends the real value.
  assert.equal(display.component('hBrght').attrs.val, 0);
});

test('local widgets are reset when their page loads again', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  display.exec('g1Name.txt="Lamp"');
  display.gotoPage('clock');
  display.gotoPage('grid');
  assert.equal(display.component('g1Name').attrs.txt, '');
});

test('hub command batches redraw once', () => {
  const { display, changes } = makeDisplay();
  display.gotoPage('grid');
  const before = changes();
  display.exec(['g1Name.txt="Lamp"', 'g1Icon.pco=65535', 'vis g1Btn,1']);
  assert.equal(changes() - before, 1);
  assert.equal(display.component('g1Name').attrs.txt, 'Lamp');
  assert.equal(display.component('g1Btn').hidden, false);
});

test('click runs the HMI press code: grid tiles highlight their parts', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  const btn = display.component('g1Btn').attrs;
  display.command('click', ['g1Overlay', 1]);
  assert.equal(display.component('g1Name').attrs.bco, btn.bco2);
  display.command('click', ['g1Overlay', 0]);
  assert.equal(display.component('g1Name').attrs.bco, btn.bco);
});

test('the system page spinner animates and shows its messages after five loops', () => {
  const { display, scheduler } = makeDisplay();
  display.gotoPage('system');
  display.exec('tmSpinner.en=1');
  scheduler.tick(1);
  assert.equal(display.drawings.length, 1);
  assert.equal(display.drawings[0].kind, 'xpic');
  scheduler.tick(60 * 5);
  assert.equal(display.component('tMsg1').hidden, false);
  // Re-drawing the same spot replaces the previous frame.
  assert.equal(display.drawings.length, 1);
});

test('timers stop when the page changes', () => {
  const { display, scheduler } = makeDisplay();
  display.gotoPage('system');
  display.exec('tmSpinner.en=1');
  assert.equal(scheduler.timers.size, 1);
  display.gotoPage('grid');
  assert.equal(scheduler.timers.size, 0);
});

test('a hub draw program paints fills and a repeated rectangle replaces itself', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  // `fill x,y,w,h,color` — width/height, as the Nextion instruction set defines it.
  display.exec('fill 10,20,20,20,65535');
  assert.deepEqual(display.drawings.map(d => d.kind), ['fill']);
  const drawn = display.drawings[0];
  assert.deepEqual([drawn.x, drawn.y, drawn.w, drawn.h, drawn.color], [10, 20, 20, 20, 65535]);
  // The progressive pass paints the same cells again at the same geometry.
  display.exec('fill 10,20,20,20,65535');
  assert.equal(display.drawings.length, 1);
  // A different rectangle is a second fill, not a replacement.
  display.exec('fill 30,20,20,20,2016');
  assert.equal(display.drawings.length, 2);
});

test('a clear that covers the picture replaces it instead of stacking on it', () => {
  const { display } = makeDisplay();
  display.gotoPage('info');
  // A picture is its clear fill plus details; the frames after it only cover what
  // moved. A clear of the rectangle therefore covers every fill already there,
  // and the log starts again from it - the picture a second pass paints must not
  // leave the previous one under it, or every frame would repaint thousands of
  // rectangles nothing can see.
  const details = [];
  for (let i = 0; i < 20; i += 1) details.push(`fill ${i * 4},60,4,4,${i}`);
  display.exec(['fill 0,52,480,268,4226', ...details]);
  assert.equal(display.drawings.length, 21);
  display.exec('fill 0,52,480,268,2016');
  assert.deepEqual(display.drawings.map(d => [d.x, d.y, d.w, d.h]), [[0, 52, 480, 268]]);
  // A frame of the stream after it is appended to the picture, not a new one.
  display.exec('fill 0,52,4,4,65535');
  assert.equal(display.drawings.length, 2);
});

test('a widget repaint keeps the image outside its rectangle', () => {
  const { display } = makeDisplay();
  display.gotoPage('clock');
  const time = display.component('tTime').attrs;
  // The image covers the whole screen; the clock's text update repaints only
  // the widget's own rectangle, so the picture survives around it - and a
  // viewer that attaches late must see the same thing the panel shows.
  display.exec(['fill 0,0,480,320,4226', 'tTime.txt="12:00"']);
  assert.ok(display.drawings.length > 0, 'the image outside the widget survives');
  for (const d of display.drawings) {
    const overlaps = d.x < time.x + time.w && d.x + d.w > time.x
      && d.y < time.y + time.h && d.y + d.h > time.y;
    assert.equal(overlaps, false, 'the widget paints its rectangle over the image');
  }
  display.gotoPage('grid');
  assert.equal(display.drawings.length, 0);
});

test('a touch paints only when the widget has a pressed look', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  display.exec('fill 0,0,480,320,4226');
  // A text keeps the same colours while touched, so the panel repaints nothing
  // and the image must stay whole.
  display.touchEvent(display.component('tHeader'), 'down');
  display.touchEvent(display.component('tHeader'), 'up');
  assert.deepEqual(
    display.drawings.map(d => [d.x, d.y, d.w, d.h]),
    [[0, 0, 480, 320]],
    'a text has no pressed look, so it does not cut the image',
  );
  // A button's pressed background differs, so its rectangle paints over the
  // image; the picture outside it survives. The bare HMI page hides the grid
  // controls until the hub reveals them, so show it before the image goes down.
  display.exec('vis g1Btn,1');
  display.exec('fill 0,0,480,320,4226');
  const button = display.component('g1Btn');
  const { x, y, w, h } = button.attrs;
  display.touchEvent(button, 'down');
  assert.ok(display.drawings.length > 0, 'the image outside the button survives');
  for (const d of display.drawings) {
    const overlaps = d.x < x + w && d.x + d.w > x && d.y < y + h && d.y + d.h > y;
    assert.equal(overlaps, false, 'the pressed button paints its rectangle');
  }
});

test('a button whose press changes no colour keeps the image', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  display.exec('vis g1Btn,1');
  const button = display.component('g1Btn');
  button.attrs.bco2 = button.attrs.bco;
  button.attrs.pco2 = button.attrs.pco;
  button.attrs.pic2 = button.attrs.pic;
  button.attrs.picc2 = button.attrs.picc;
  display.exec('fill 0,0,480,320,4226');
  display.touchEvent(button, 'down');
  assert.deepEqual(
    display.drawings.map(d => [d.x, d.y, d.w, d.h]),
    [[0, 0, 480, 320]],
    'the pressed look is the normal one, so nothing is painted',
  );
});

test('ref clears shapes drawn over a widget', () => {
  const { display } = makeDisplay();
  display.gotoPage('light');
  const wheel = display.component('pColorWheel');
  display.exec(`vis ${wheel.name},1`);
  display.exec(`cirs ${wheel.attrs.x + 10},${wheel.attrs.y + 10},6,65535`);
  assert.equal(display.drawings.length, 1);
  display.exec(`ref ${wheel.id}`);
  assert.equal(display.drawings.length, 0);
});

test('a hidden widget, a hotspot and a timer do not cut the image', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  display.exec(['fill 0,0,480,320,4226', 'vis tHeader,0', 'tHeader.txt="x"']);
  display.exec('vis g1Overlay,1');
  assert.deepEqual(
    display.drawings.map(d => [d.x, d.y, d.w, d.h]),
    [[0, 0, 480, 320]],
    'a hidden text and a hotspot paint nothing',
  );
  display.gotoPage('system');
  display.exec(['fill 0,0,480,320,4226', 'tmSpinner.en=1', 'vPosX.val=3']);
  assert.deepEqual(
    display.drawings.map(d => [d.x, d.y, d.w, d.h]),
    [[0, 0, 480, 320]],
    'a timer and a variable paint nothing',
  );
});

test('read requests are answered like the firmware does', () => {
  const { display } = makeDisplay();
  display.gotoPage('light');
  display.exec('hBrightness.val=42');
  assert.deepEqual(JSON.parse(display.readResponse('val', 'hBrightness')), {
    name: 'hBrightness',
    type: 'number',
    value: 42,
  });
});

test('both layouts hold the same widgets on every page', () => {
  const landscape = loadLayout('landscape');
  const portrait = loadLayout('portrait');
  assert.deepEqual(Object.keys(portrait.pages), Object.keys(landscape.pages));
  for (const [id, page] of Object.entries(landscape.pages)) {
    const names = p => p.components.map(c => `${c.id}:${c.name}`);
    assert.deepEqual(names(portrait.pages[id]), names(page), `page ${page.name}`);
  }
  assert.equal(landscape.width, 480);
  assert.equal(portrait.width, 320);
});

test('replacing an image does not erase a disjoint colour-wheel marker', () => {
  const { display } = makeDisplay('landscape');
  display.gotoPage('light');
  display.exec(['vis pColorWheel,1', 'cirs 150,130,6,65535', 'fill 10,10,10,10,0']);
  display.exec('fill 10,10,10,10,16');
  assert.deepEqual(display.drawings.filter(d => d.kind === 'cirs' || d.kind === 'fill'), [
    { kind: 'cirs', x: 150, y: 130, r: 6, color: 65535 },
    { kind: 'fill', x: 10, y: 10, w: 10, h: 10, color: 16 },
  ]);
});

test('old colours do not accumulate indefinitely in a long-running picture', () => {
  const { display } = makeDisplay('landscape');
  display.gotoPage('grid');
  display.exec(['fill 0,52,320,200,0', 'fill 20,60,10,10,65535']);
  const updates = Array.from({ length: 20000 }, (_, i) => 'fill 0,52,10,10,' + i);
  display.exec(updates);
  assert.deepEqual(display.drawings.filter(d => d.kind === 'fill').map(d => d.color), [0, 65535, 19999]);
});
