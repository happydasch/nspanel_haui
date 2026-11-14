import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  buildPreviewDisplay,
  loadPanelRender,
  previewRenderKey,
} from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { loadIconMap, loadLayout } from '../../custom_components/nspanel_haui/frontend/previews/simulator.js';
import { layout } from './support/fixtures.mjs';

test('every physical page id maps to a preview model in both orientations', () => {
  for (const orientation of ['landscape', 'portrait']) {
    const displayLayout = layout(orientation);
    for (const id of Object.keys(displayLayout.pages).map(Number)) {
      const preview = buildPreviewDisplay(displayLayout, id);
      assert.equal(preview.page.id, id, `${orientation} page ${id}`);
    }
  }
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
  const hass = {
    connection: {
      sendMessagePromise: async (msg) => {
        sent.push(msg);
        return reply(msg);
      },
    },
  };
  return {
    sent,
    entryId: 'entry1',
    device: 'kitchen',
    deviceConfig: { home_panel: 'rooms' },
    panels: [{ key: 'rooms', type: 'grid' }],
    deviceInfo: null,
    api: createApiClient(() => hass),
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

test('a preview with sample context sends it along and renders apart from the card', async () => {
  const host = editorHost(() => ({ page: 13, before: [], commands: [] }));
  const popup = { key: 'popup_light', type: 'light' };
  const kwargs = { item: 'light.desk', item_id: 'light.desk' };

  await loadPanelRender(host, popup, true);
  await loadPanelRender({ ...host, kwargs }, popup, true);
  await loadPanelRender({ ...host, kwargs }, popup, true);

  assert.deepEqual(host.sent.map(({ key, kwargs: sent }) => [key, sent]), [
    ['popup_light', undefined],
    ['popup_light', kwargs],
  ]);
  assert.notEqual(previewRenderKey({ ...host, kwargs }), previewRenderKey(host));
});

test('a re-mounted card reuses its render until the device settings change', async () => {
  const host = editorHost(() => ({ page: 9, before: [], commands: [] }));
  const panel = { key: 'rooms', type: 'grid' };

  await loadPanelRender(host, { ...panel, title: 'Memo' }, false);
  await loadPanelRender(host, { ...panel, title: 'Memo' }, false);
  assert.equal(host.sent.length, 1);

  const before = previewRenderKey(host);
  host.deviceConfig = { home_panel: 'rooms', locale: 'de_DE' };
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
  assert.equal(await loadPanelRender({ entryId: 'entry1', device: 'kitchen' }, { type: 'grid' }, false), null);
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

test('a card keeps its last render across reloads until the frontend changes', async (t) => {
  const values = new Map();
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
    },
  });
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const render = { page: 9, before: [], commands: ['tTitle.txt="Kept"'] };
  const host = editorHost(() => render);
  const panel = { key: 'kept', type: 'grid' };

  await loadPanelRender(host, panel, false);
  t.mock.timers.tick(500);

  const previewer = '../../custom_components/nspanel_haui/frontend/previews/previewer.js';
  const reloaded = await import(`${previewer}?reload`);
  // Edits and settings changes keep a card's identity; its key and kind do not.
  assert.deepEqual(reloaded.lastPanelRender(host, { ...panel, title: 'Edited' }, false), render);
  assert.equal(reloaded.lastPanelRender({ ...host, device: 'hall' }, panel, false), null);
  assert.equal(reloaded.lastPanelRender(host, panel, true), null);
  assert.equal(reloaded.lastPanelRender(host, { type: 'grid' }, false), null);

  const stored = JSON.parse(values.get('haui_lastCardRenders'));
  values.set('haui_lastCardRenders', JSON.stringify({ ...stored, assets: 'https://ha.local/old/' }));
  const updated = await import(`${previewer}?update`);
  assert.equal(updated.lastPanelRender(host, panel, false), null);
});
