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

// The clocktwo page's setup loop writes .picc to b[112], its `background`
// variable; the Nextion rejects that write and carries on, and so does the
// virtual panel.
const KNOWN_HMI_QUIRK = /^112 has no attribute picc/;

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
    assert.deepEqual(display.warnings.filter(w => !KNOWN_HMI_QUIRK.test(w)), []);
  });
}

test('a picture page takes its background from the global set before the page loads', () => {
  const { display } = makeDisplay();
  // The hub sets the page's global background variable, then switches page
  // (clock_common.apply_background).
  display.exec('clock.background.val=5');
  display.gotoPage('clock');
  assert.equal(display.component('clock').attrs.pic, 5);
  assert.equal(display.component('tTime').attrs.picc, 5);
  assert.equal(display.component('pGrid').hidden, true);
});

test('global-scope widgets keep their values across page changes', () => {
  const { display } = makeDisplay();
  display.gotoPage('clock');
  display.exec('background.val=4');
  display.gotoPage('grid');
  assert.equal(display.getAttr({ page: 'clock', comp: 'background', attr: 'val' }), 4);
  display.gotoPage('clock');
  assert.equal(display.component('background').attrs.val, 4);
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

test('ref clears shapes drawn over a widget', () => {
  const { display } = makeDisplay();
  display.gotoPage('light');
  const wheel = display.component('pColorWheel').attrs;
  display.exec(`cirs ${wheel.x + 10},${wheel.y + 10},6,65535`);
  assert.equal(display.drawings.length, 1);
  display.exec(`ref ${display.component('pColorWheel').id}`);
  assert.equal(display.drawings.length, 0);
});

test('cls sets the page fill', () => {
  const { display } = makeDisplay();
  display.gotoPage('grid');
  display.exec('cls 4226');
  assert.equal(display.fill, 4226);
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
