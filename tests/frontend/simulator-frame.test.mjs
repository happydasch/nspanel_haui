import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { readFileSync } from 'node:fs';

import {
  SimulatorFrameElement,
  setPanelRenderSource,
} from '../../custom_components/nspanel_haui/frontend/previews/simulator-frame.js';
import { loadIconMap, loadLayout } from '../../custom_components/nspanel_haui/frontend/virtual/assets.js';

const asset = (name) => JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/${name}`, import.meta.url),
  'utf8',
));

// The assets are memoised: load them once from the files, as fetch would.
loadLayout('landscape', () => asset('layout_landscape.json'));
loadIconMap(() => asset('icon_map.json'));

test('simulator frame recalculates scale when its container width changes', () => {
  let width = 450;
  let updates = 0;
  const frame = Object.create(SimulatorFrameElement.prototype);
  frame._containerWidth = null;
  frame._display = { layout: { visible_width: 450 } };
  frame._scale = null;
  frame.getBoundingClientRect = () => ({ width });
  frame.requestUpdate = () => { updates += 1; };

  frame._measure();
  assert.equal(frame._scale, 1);

  width = 300;
  frame._measure();
  assert.equal(frame._containerWidth, 300);
  assert.equal(frame._scale, 2 / 3);
  assert.equal(updates, 2);
});

test('portrait previews stop growing once they reach the height cap', () => {
  let width = 640;
  const frame = Object.create(SimulatorFrameElement.prototype);
  Object.assign(frame, {
    portrait: true,
    _containerWidth: null,
    _display: { layout: { visible_width: 320, height: 480 } },
    _scale: null,
    getBoundingClientRect: () => ({ width }),
    requestUpdate() {},
  });

  frame._measure();
  assert.equal(frame._containerWidth, 640);
  assert.equal(frame._scale, 1);

  width = 160;
  frame._measure();
  assert.equal(frame._scale, 0.5);
});

test('simulator frame keeps the last usable size while its container is hidden', () => {
  let width = 450;
  const frame = Object.create(SimulatorFrameElement.prototype);
  frame._containerWidth = null;
  frame._display = { layout: { visible_width: 450 } };
  frame._scale = null;
  frame.getBoundingClientRect = () => ({ width });
  frame.requestUpdate = () => {};

  frame._measure();
  width = 0;
  frame._measure();

  assert.equal(frame._containerWidth, 450);
  assert.equal(frame._scale, 1);
});

test('simulator frame rebuilds when what the hub renders with changes', () => {
  const frame = Object.create(SimulatorFrameElement.prototype);
  const rebuilds = [];
  frame._started = true;
  frame._start = (force) => rebuilds.push(force);

  frame.updated(new Map([['renderKey', '[]']]));
  frame.updated(new Map([['byKey', false]]));
  assert.deepEqual(rebuilds, [true, true]);

  frame.updated(new Map([['_scale', null]]));
  assert.deepEqual(rebuilds, [true, true]);
});

function frameWith(render) {
  setPanelRenderSource(render);
  const frame = Object.create(SimulatorFrameElement.prototype);
  Object.assign(frame, {
    panel: { type: 'weather', key: 'weather_0' },
    portrait: false,
    byKey: false,
    host: {},
    _started: false,
    _seq: 0,
    _measure() {},
    requestUpdate() {},
  });
  return frame;
}

test('simulator frame shows the hub render its loader returned', async () => {
  const frame = frameWith(() => ({
    page: 6, before: [], commands: ['f1Name.txt="Tue"', 'vis f1Name,1'],
  }));
  try {
    await frame._start();
    assert.equal(frame._error, null);
    assert.equal(frame._display.page.name, 'weather');
    assert.equal(frame._display.component('f1Name').attrs.txt, 'Tue');
  } finally {
    setPanelRenderSource(null);
  }
});

test('simulator frame shows the placeholder until it has a hub render', async () => {
  const frame = frameWith(() => null);
  try {
    await frame._start();
    assert.equal(frame._error, null);
    assert.equal(frame._display, null);
  } finally {
    setPanelRenderSource(null);
  }
});

test('simulator frame shows the hub error instead of a stale preview', async () => {
  const frame = frameWith(() => Promise.reject(new Error("Unknown panel type: 'bogus'")));
  try {
    await frame._start();
    assert.equal(frame._error, "Unknown panel type: 'bogus'");
  } finally {
    setPanelRenderSource(null);
  }
});

test('a slower older render never replaces a newer one', async () => {
  let resolveOld;
  const renders = [
    new Promise((resolve) => { resolveOld = resolve; }),
    { page: 6, before: [], commands: ['f1Name.txt="New"', 'vis f1Name,1'] },
  ];
  const frame = frameWith(() => renders.shift());
  try {
    const first = frame._start();
    await frame._start(true);
    resolveOld({ page: 6, before: [], commands: ['f1Name.txt="Old"', 'vis f1Name,1'] });
    await first;
    assert.equal(frame._display.component('f1Name').attrs.txt, 'New');
  } finally {
    setPanelRenderSource(null);
  }
});
