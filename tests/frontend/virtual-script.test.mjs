import test from 'node:test';
import assert from 'node:assert/strict';

import { evaluate, runScript } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-script.js';

/** A minimal host: `widgets` maps "name" or "page.name" to attribute objects. */
function makeHost(widgets = {}, globals = {}) {
  const host = {
    widgets,
    globals: { sys0: 0, sys1: 0, sys2: 0, ...globals },
    commands: [],
    warnings: [],
    _target(ref) {
      const key = ref.page ? `${ref.page}.${ref.comp}` : String(ref.comp);
      if (!(key in widgets)) throw new Error(`unknown widget ${key}`);
      return widgets[key];
    },
    getAttr(ref) {
      return ref.global !== undefined ? host.globals[ref.global] : host._target(ref)[ref.attr];
    },
    setAttr(ref, value) {
      if (ref.global !== undefined) host.globals[ref.global] = value;
      else host._target(ref)[ref.attr] = value;
    },
    command(name, args) { host.commands.push([name, ...args]); },
    warn(msg) { host.warnings.push(msg); },
  };
  return host;
}

test('arithmetic is integer and strictly left to right', () => {
  const host = makeHost();
  assert.equal(evaluate('2+3*4', host), 20);
  assert.equal(evaluate('7/2', host), 3);
  assert.equal(evaluate('-7/2', host), -3);
  assert.equal(evaluate('17%5', host), 2);
  assert.equal(evaluate('5/0', host), 0);
});

test('string concatenation and comparison', () => {
  const host = makeHost({ t: { txt: 'a' } });
  assert.equal(evaluate('"x"+t.txt+"y"', host), 'xay');
  assert.equal(evaluate('t.txt==""', host), 0);
  assert.equal(evaluate('t.txt!=""', host), 1);
});

test('compound assignments, as in the system spinner timer', () => {
  const host = makeHost({ vFrame: { val: 47 }, vPosX: { val: 0 }, vPosY: { val: 0 } });
  runScript(
    [
      'vPosX.val=vFrame.val%30',
      'vPosX.val%=10',
      'vPosX.val*=140',
      'vPosY.val=vFrame.val%30',
      'vPosY.val/=10',
      'vPosY.val*=140',
    ].join('\n'),
    host,
  );
  assert.equal(host.widgets.vPosX.val, 980);
  assert.equal(host.widgets.vPosY.val, 140);
  assert.deepEqual(host.warnings, []);
});

test('if / }else blocks', () => {
  const code = [
    'if(vFrame.val<30)',
    '{',
    '  xpic 1,2,3,4,5,6,10',
    '}else',
    '{',
    '  xpic 1,2,3,4,5,6,11',
    '}',
  ].join('\n');
  const low = makeHost({ vFrame: { val: 3 } });
  runScript(code, low);
  assert.deepEqual(low.commands, [['xpic', 1, 2, 3, 4, 5, 6, 10]]);
  const high = makeHost({ vFrame: { val: 40 } });
  runScript(code, high);
  assert.deepEqual(high.commands, [['xpic', 1, 2, 3, 4, 5, 6, 11]]);
});

test('for loops over indexed widgets, as in the clocktwo page', () => {
  const widgets = { 2: { picc: 0 }, 3: { picc: 0 }, 4: { picc: 0 } };
  const host = makeHost(widgets, { sys1: 7 });
  runScript('for(sys0=2;sys0<=4;sys0++)\n{\n  b[sys0].picc=sys1\n}', host);
  assert.deepEqual(Object.values(widgets).map(w => w.picc), [7, 7, 7]);
  assert.equal(host.globals.sys0, 5);
});

test('a runaway loop is stopped and reported', () => {
  const host = makeHost();
  runScript('for(sys0=0;sys0>=0;sys0+=0)\n{\n  sys1+=1\n}', host);
  assert.ok(host.warnings.some(w => w.includes('loop limit')));
});

test('page-qualified references and comments', () => {
  const host = makeHost({ 'system.firstRun': { txt: '1' }, tMsg2: { txt: '' } });
  runScript('tMsg2.txt="v: "+system.firstRun.txt // a comment', host);
  assert.equal(host.widgets.tMsg2.txt, 'v: 1');
});

test('hub text writes keep their text verbatim, with \\r as a line break', () => {
  const host = makeHost({ tText: { txt: '' } });
  runScript('tText.txt="50% // not a comment\\rnext line"', host);
  assert.equal(host.widgets.tText.txt, '50% // not a comment\nnext line');
});

test('hub text writes decode escaped quotes and backslashes like the display', () => {
  const host = makeHost({ tText: { txt: '' } });
  // The hub escapes " and \ (haui_base.set_component_text).
  runScript('tText.txt="He said \\"hi\\" // still text"', host);
  assert.equal(host.widgets.tText.txt, 'He said "hi" // still text');

  runScript('tText.txt="C:\\\\"', host);
  assert.equal(host.widgets.tText.txt, 'C:\\');

  // An escaped backslash before r is a backslash and an r, not a line break.
  runScript('tText.txt="a\\\\rb"', host);
  assert.equal(host.widgets.tText.txt, 'a\\rb');
});

test('commands evaluate their value arguments', () => {
  const host = makeHost({ hSpinner: { x: 155, y: 80 } });
  runScript('vis tMsg1,1\nclick g1Btn,0\nxpic hSpinner.x,hSpinner.y,140,140,0,0,10', host);
  assert.deepEqual(host.commands, [
    ['vis', 'tMsg1', 1],
    ['click', 'g1Btn', 0],
    ['xpic', 155, 80, 140, 140, 0, 0, 10],
  ]);
});

test('covx converts a number to text', () => {
  const host = makeHost({ hBrght: { val: 42 }, tBrghtPct: { txt: '' } });
  runScript('covx hBrght.val,tBrghtPct.txt,0,0\ntBrghtPct.txt+="%"', host);
  assert.equal(host.widgets.tBrghtPct.txt, '42%');
});

test('unsupported statements are reported, not skipped silently', () => {
  const host = makeHost({ t: { txt: '' } });
  runScript('spstr t.txt,t.txt,"x",0\nt.txt="ok"', host);
  assert.equal(host.warnings.length, 1);
  assert.match(host.warnings[0], /spstr/);
  assert.equal(host.widgets.t.txt, 'ok');
});

test('an unknown widget is reported and the rest still runs', () => {
  const host = makeHost({ t: { val: 0 } });
  runScript('nope.val=1\nt.val=2', host);
  assert.equal(host.warnings.length, 1);
  assert.equal(host.widgets.t.val, 2);
});
