import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  buildPreviewDisplay,
  loadPanelRender,
  previewRenderKey,
} from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';
import {
  loadIconMap,
  loadLayout,
  renderSimulatorScreen,
} from '../../custom_components/nspanel_haui/frontend/previews/simulator.js';

function layout(orientation) {
  return JSON.parse(readFileSync(
    new URL(`../../custom_components/nspanel_haui/frontend/virtual/layout_${orientation}.json`, import.meta.url),
    'utf8',
  ));
}

/** Flatten a Lit TemplateResult tree to text. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  return v == null || typeof v === 'symbol' ? '' : String(v);
}

test('every physical page id maps onto a layout page in both orientations', () => {
  for (const orientation of ['landscape', 'portrait']) {
    const json = layout(orientation);
    for (const idStr of Object.keys(json.pages)) {
      const d = buildPreviewDisplay(json, Number(idStr));
      assert.equal(d.page.id, Number(idStr), `${orientation} page ${idStr}`);
      const out = flat(renderSimulatorScreen(d, {
        scale: 0.5, iconName: () => null, pictureUrl: (id) => `p/${id}.webp`,
      }));
      assert.match(out, /vp-screen/);
    }
  }
});

test('renderSimulatorScreen preserves the device aspect ratio and applies scale', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9);
  const out = flat(renderSimulatorScreen(d, { scale: 0.5, iconName: () => null, pictureUrl: (id) => `p/${id}.webp` }));
  assert.match(out, /vp-screen" style="width:450px;height:320px/);
  assert.match(out, /pg-sim-scaler" style="width:450px;height:320px;transform:scale\(0.5\)/);
  assert.match(out, /aspect-ratio:450\/320/);
});

test('loadLayout and loadIconMap use an injected loader', () => {
  const loader = (url) => Promise.resolve({ url: String(url) });
  return Promise.all([
    loadLayout('landscape', loader).then((r) => assert.match(r.url, /layout_landscape\.json$/)),
    loadIconMap(loader).then((r) => assert.match(r.url, /icon_map\.json$/)),
  ]);
});

// hub output replay

test('a hub render is replayed in the device order: before, page switch, page', () => {
  const render = {
    page: 7,
    before: ['system.vBackground.val=4'],
    commands: ['tTime.txt="12:34"', 'vis tTime,1'],
  };
  const d = buildPreviewDisplay(layout('landscape'), 7, { render });
  assert.equal(d.page.name, 'clock');
  // The page's Preinitialize code read the background before the page loaded.
  assert.equal(d.component('tTime').attrs.picc, 4);
  assert.equal(d.component('tTime').attrs.txt, '12:34');
});

test('a hub render picks its own page', () => {
  const render = { page: 13, before: [], commands: ['tTitle.txt="Desk lamp"'] };
  const d = buildPreviewDisplay(layout('landscape'), 9, { render });
  assert.equal(d.page.name, 'light');
  assert.equal(d.component('tTitle').attrs.txt, 'Desk lamp');
});

test('the hub reveals the controls the bare HMI page hides', () => {
  // Pages hide their controls in their Preinitialize code; the hub shows them.
  const blank = buildPreviewDisplay(layout('landscape'), 18);
  const render = { page: 18, before: [], commands: ['vis bUp,1', 'vis hVertPos,1'] };
  const rendered = buildPreviewDisplay(layout('landscape'), 18, { render });
  for (const name of ['bUp', 'hVertPos']) {
    assert.equal(blank.component(name).hidden, true, `${name} starts hidden`);
    assert.equal(rendered.component(name).hidden, false, `${name} is revealed`);
  }
});

// render requests

function editorHost(reply) {
  const sent = [];
  return {
    sent,
    entryId: 'entry1',
    _selectedDevice: 'kitchen',
    _deviceConfig: { home_panel: 'rooms' },
    _devicePanels: () => [{ key: 'rooms', type: 'grid' }],
    hass: {
      connection: {
        sendMessagePromise: async (msg) => {
          sent.push(msg);
          return reply(msg);
        },
      },
    },
  };
}

test('a user card asks the hub to render its config, a system card its key', async () => {
  const host = editorHost(() => ({ page: 9, before: [], commands: [] }));
  const panel = { key: 'rooms', type: 'grid', title: 'Unsaved title' };

  await loadPanelRender(host, panel, false);
  await loadPanelRender(host, { key: 'popup_notify', type: 'notify', label: 'Notification' }, true);

  assert.deepEqual(host.sent, [
    {
      type: 'nspanel_haui/virtual_panel/render', entry_id: 'entry1', device: 'kitchen', panel,
    },
    {
      type: 'nspanel_haui/virtual_panel/render', entry_id: 'entry1', device: 'kitchen', key: 'popup_notify',
    },
  ]);
});

test('a re-mounted card reuses its render until the device settings change', async () => {
  const host = editorHost(() => ({ page: 9, before: [], commands: [] }));
  const panel = { key: 'rooms', type: 'grid' };

  await loadPanelRender(host, { ...panel, title: 'Memo' }, false);
  await loadPanelRender(host, { ...panel, title: 'Memo' }, false);
  assert.equal(host.sent.length, 1);

  const before = previewRenderKey(host);
  host._deviceConfig = { home_panel: 'rooms', locale: 'de_DE' };
  assert.notEqual(previewRenderKey(host), before);
  await loadPanelRender(host, { ...panel, title: 'Memo' }, false);
  assert.equal(host.sent.length, 2);
});

test('an expired render is dropped and asked for again', async (t) => {
  t.mock.timers.enable({ apis: ['Date'], now: Date.now() });
  const host = editorHost(() => ({ page: 9, before: [], commands: [] }));
  const panel = { key: 'rooms', type: 'grid', title: 'Expiry' };

  await loadPanelRender(host, panel, false);
  t.mock.timers.tick(29_000);
  await loadPanelRender(host, panel, false);
  assert.equal(host.sent.length, 1);
  t.mock.timers.tick(1_000);
  await loadPanelRender(host, panel, false);
  assert.equal(host.sent.length, 2);
});

test('without a Home Assistant connection a card has no render', async () => {
  assert.equal(await loadPanelRender({ entryId: 'entry1', _selectedDevice: 'kitchen' }, { type: 'grid' }, false), null);
});

test('a failed render rejects with the hub error and is not kept', async () => {
  let fail = true;
  const host = editorHost(() => {
    if (fail) throw { code: 'invalid_panel', message: "Unknown panel type: 'bogus'" };
    return { page: 9, before: [], commands: [] };
  });
  const panel = { key: 'x', type: 'bogus' };

  await assert.rejects(loadPanelRender(host, panel, false), /Unknown panel type/);
  fail = false;
  assert.equal((await loadPanelRender(host, panel, false)).page, 9);
});
