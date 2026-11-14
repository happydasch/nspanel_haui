// @ts-check
import './support/browser.mjs';

import { test } from 'node:test';
import { jsonResponse, makeHass } from './support/hass.mjs';
import { flush } from './support/render.mjs';
import assert from 'node:assert/strict';
import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { makeHost } from './fake-host.mjs';
import { openDeviceConfig, closeDeviceConfig } from '../../custom_components/nspanel_haui/frontend/device-config.js';
import * as Crud from '../../custom_components/nspanel_haui/frontend/crud.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import { SIDEBAR_OVERLAY_KINDS } from '../../custom_components/nspanel_haui/frontend/store/store.js';

function host() {
  return makeHost({ devices: { kitchen: { config: {}, panels: [] } } }, (method, path) => {
    if (method === 'GET' && path === '/api/nspanel_haui/devices/entry1/kitchen') {
      return jsonResponse({ device: 'kitchen', config: {} });
    }
    throw new Error('unexpected request');
  });
}

test('device settings open and close through the ordered overlay stack', async () => {
  const editor = host();
  await openDeviceConfig(editor);
  assert.deepEqual(editor.store.getState().ui.overlays.map(({ kind, subject }) => [kind, subject]), [
    ['device-settings', 'kitchen'],
  ]);
  closeDeviceConfig(editor);
  assert.deepEqual(editor.store.getState().ui.overlays, []);
});

test('choosing a catalog type replaces the catalog overlay with its editor', () => {
  const editor = host();
  editor.store.actions.pushOverlay({
    kind: 'panel-catalog', anchorKey: 'add-panel', subject: 'kitchen', draft: null,
  });
  Crud.openAdd(editor, 'light');
  assert.deepEqual(editor.store.getState().ui.overlays.map(({ kind, subject }) => [kind, subject]), [
    ['panel-editor', 'light_0'],
  ]);
  Crud.closeEdit(editor);
  assert.deepEqual(editor.store.getState().ui.overlays, []);
});

test('Add panel from device Preview switches to Panels before opening the catalog', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor._captureSidebarFocus = () => {};
  const navigations = [];
  editor._router = {
    navigate(route) {
      navigations.push(route);
      editor.store.actions.setRoute(route);
    },
  };
  editor.store.actions.setRoute({ view: 'device', device: 'kitchen', panelView: 'preview' });

  editor._openCatalog();

  assert.deepEqual(navigations, [
    { view: 'device', device: 'kitchen', panelView: 'panels' },
  ]);
  assert.equal(editor.store.getState().ui.route.panelView, 'panels');
  assert.equal(editor.store.getState().ui.overlays.at(-1)?.kind, 'panel-catalog');
});

test('an anchored popover replaces the anchored popover it would stack on', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor.renderRoot = { querySelector: () => ({ focus() {} }) };
  editor._toggleDeviceMenu('kitchen', 'device-menu-row:kitchen');
  assert.deepEqual(editor.store.getState().ui.overlays.map(({ kind }) => kind), ['device-menu']);
  editor._toggleAnchoredPopover('notification-centre', 'notification-centre');
  assert.deepEqual(editor.store.getState().ui.overlays.map(({ kind }) => kind), ['notification-centre']);
  editor._closeAnchoredPopover('notification-centre');
  assert.deepEqual(editor.store.getState().ui.overlays, []);
  editor._toggleDeviceMenu('kitchen', 'device-menu-row:kitchen');
  assert.deepEqual(editor.store.getState().ui.overlays.map(({ kind }) => kind), ['device-menu']);
  editor._toggleDeviceMenu('kitchen', 'device-menu-row:kitchen');
  assert.deepEqual(editor.store.getState().ui.overlays, []);
});

test('the Fleet device menu shows the device without settings or update shortcuts', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor._selectDevice = () => {};
  const navigations = [];
  editor._navigateToDevice = (name) => navigations.push(name);
  editor.store.actions.pushOverlay({
    kind: 'device-menu', anchorKey: 'device-menu:kitchen', subject: 'kitchen', draft: null,
  });

  const model = editor._deviceMenuModel();
  assert.equal(model.key, 'kitchen');
  const items = model.items.filter((item) => item !== 'divider');
  assert.deepEqual(items.map((item) => item.label), ['View', 'Panels', 'Logs', 'Disable', 'Remove']);
  items.find((item) => item.label === 'View').onSelect();
  assert.deepEqual(navigations, ['kitchen']);
  // Removing asks first: the menu only names the device to confirm.
  items.find((item) => item.label === 'Remove').onSelect();
  assert.equal(editor._removeTarget, 'kitchen');
  assert.match(editor._removeDeviceParams.message, /kitchen/);
});

test('Updates and Theme open as sidebars from the device preview', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor.renderRoot = { querySelector: () => null, activeElement: null };
  const kinds = () => editor.store.getState().ui.overlays.map(({ kind }) => kind);

  editor._openUpdates('kitchen');
  assert.deepEqual(kinds(), ['updates']);
  editor._closeSidebar();
  assert.deepEqual(kinds(), []);

  editor._selectedDevice = 'kitchen';
  editor._loadDeviceConfig = () => {};
  editor._deviceConfig = {};
  editor._panels = { devices: { kitchen: { config: { theme_id: 'dark' } } } };
  editor._route = { view: 'device', device: 'kitchen' };
  editor._openTheme();
  assert.deepEqual(kinds(), ['theme']);
  editor._closeSidebar();
  assert.deepEqual(kinds(), []);

  editor._openTheme();
  editor._closeSidebarForRouteChange();
  assert.deepEqual(kinds(), []);
});

test('every sidebar kind has a title in its strip', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._panels = { system_panels: [] };
  editor._editingPanel = null;

  for (const kind of SIDEBAR_OVERLAY_KINDS) {
    const title = editor._sidebarLabel(kind);
    assert.equal(typeof title, 'string', `${kind} has a title`);
    assert.ok(title.length > 0, `${kind} has a title`);
  }
  // A kind that reaches the sidebar without a title is a bug, not a blank strip.
  assert.throws(() => editor._sidebarLabel('not-a-sidebar'), /Unknown sidebar kind/);
});

test('the Schedule and Gestures buttons open their sidebar and closing it drops the draft', () => {  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor._selectedDevice = 'kitchen';
  editor._deviceConfig = {};
  editor._scheduleDraft = { device: 'kitchen', schedule: [] };
  editor._gestureDraft = { device: 'kitchen', gestures: [] };
  editor._route = { view: 'device', device: 'kitchen' };
  editor.renderRoot = { querySelector: () => null, activeElement: null };
  const kinds = () => editor.store.getState().ui.overlays.map(({ kind }) => kind);

  editor._openDeviceOption('schedule');
  assert.deepEqual(kinds(), ['device-schedule']);
  editor._openDeviceOption('gestures');
  assert.deepEqual(kinds(), ['device-schedule', 'device-gestures']);

  // Only the top one closes, and an unsaved draft goes with it.
  editor._closeSidebar();
  assert.deepEqual(kinds(), ['device-schedule']);
  assert.equal(editor._gestureDraft, null);
  editor._closeSidebar();
  assert.deepEqual(kinds(), []);
  assert.equal(editor._scheduleDraft, null);
});

test('Logs opens as a sidebar for one device or every device and closes like the others', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor._selectDevice = () => {};
  editor.renderRoot = { querySelector: () => null, activeElement: null };
  const overlays = () => editor.store.getState().ui.overlays.map(({ kind, subject }) => [kind, subject]);

  editor._openLogs(null);
  assert.deepEqual(overlays(), [['logs', null]]);
  editor._closeSidebar();
  assert.deepEqual(overlays(), []);

  // The Fleet device menu opens that device's logs where it is, without a route change.
  editor.store.actions.pushOverlay({ kind: 'device-menu', anchorKey: 'device-menu:kitchen', subject: 'kitchen', draft: null });
  const model = editor._deviceMenuModel();
  editor._closeAnchoredPopover('device-menu');
  model.items.find((item) => item.label === 'Logs').onSelect();
  assert.deepEqual(overlays(), [['logs', 'kitchen']]);

  // The sidebar's device selector changes the device in place.
  editor._selectLogsDevice('');
  assert.deepEqual(overlays(), [['logs', null]]);
  editor._selectLogsDevice('kitchen');
  assert.deepEqual(overlays(), [['logs', 'kitchen']]);
});

test('a sidebar still stacks above an anchored popover', async () => {
  const editor = host();
  editor.store.actions.pushOverlay({
    kind: 'notification-centre', anchorKey: 'notification-centre', subject: null, draft: null,
  });
  await openDeviceConfig(editor);
  assert.deepEqual(editor.store.getState().ui.overlays.map(({ kind }) => kind), [
    'notification-centre', 'device-settings',
  ]);
});

test('notification centre open and close state comes from the overlay stack', () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor._notifications = [];
  editor.renderRoot = { querySelector: () => ({ focus() {} }) };
  editor._store.actions.loadNotifications = () => {};
  const requestAnimationFrame = globalThis.requestAnimationFrame;
  globalThis.requestAnimationFrame = (callback) => callback();
  try {
    editor._openNotifications();
    assert.equal(editor.store.getState().ui.overlays.at(-1)?.kind, 'notification-centre');
    editor._closeNotifications();
    assert.deepEqual(editor.store.getState().ui.overlays, []);
  } finally {
    if (requestAnimationFrame) globalThis.requestAnimationFrame = requestAnimationFrame;
    else delete globalThis.requestAnimationFrame;
  }
});

test('the editor offers scanned devices the hub does not manage yet and adds them', async () => {
  const editor = host();
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor.entryId = 'entry1';
  const added = [];
  editor.api = {
    devices: {
      scan: async () => ({ devices: [{ name: 'kitchen' }, { name: 'office', friendly_name: 'Office' }] }),
      add: async (_entry, devices) => { added.push(...devices); },
    },
  };
  await editor._scanDevices();
  assert.equal(editor._scanning, false);
  // The configured device is not offered again.
  assert.deepEqual(editor._discoveredDevices().map((device) => device.name), ['office']);

  editor.api.devices.scan = async () => { throw new Error('offline'); };
  await editor._scanDevices();
  assert.equal(editor._scanError, 'offline');
});

/**
 * The editor without Lit's constructor, synced to its store like the real one:
 * the router stub records navigations and applies them as the URL would.
 */
function routedEditor(panels) {
  const fixture = makeHost(panels, () => { throw new Error('unexpected request'); });
  Object.setPrototypeOf(fixture, NSPanelEditor.prototype);
  fixture._store = fixture.store;
  fixture.__lastSelectedDevice = null;
  fixture.navigations = [];
  fixture.replaced = [];
  fixture._router = {
    navigate(route, opts) {
      fixture.navigations.push(route.device || route.view);
      fixture.replaced.push(opts?.replace === true);
      fixture._store.actions.setRoute(route);
    },
  };
  fixture._openEdit = () => {};
  fixture._store.subscribe(() => fixture._syncFromStore());
  return fixture;
}

const TWO_DEVICES = {
  device_order: ['kitchen', 'hall'],
  devices: { kitchen: { config: {}, panels: [{ key: 'k1', type: 'grid' }] }, hall: { config: {}, panels: [{ key: 'h1', type: 'grid' }] } },
};

test('a link to the second device opens it, not the first device the hub selects', async () => {
  const editor = routedEditor(TWO_DEVICES);
  editor._store.setState((current) => ({
    ...current,
    devices: { byName: {}, order: [], selected: null },
    hub: { ...current.hub, loading: true },
    ui: { ...current.ui, route: { view: 'device', device: 'hall', panel: null, panelView: 'preview' } },
  }));
  editor._syncFromStore();
  editor.api.panels.load = async () => TWO_DEVICES;
  editor.api.status.getAll = async () => ({});

  await editor._store.actions.loadHub('entry1');
  editor._store.actions.stopSelectedStatusPolling();

  assert.equal(editor._store.getState().ui.route.device, 'hall');
  assert.equal(editor._store.getState().devices.selected, 'hall');
  assert.deepEqual(editor.navigations, []);
});

test('Back to another device closes the sidebar of the device it leaves', () => {
  const editor = routedEditor(TWO_DEVICES);
  editor._store.actions.setRoute({ view: 'device', device: 'kitchen', panelView: 'preview' });
  editor._store.actions.selectDevice('kitchen');
  editor._store.actions.stopSelectedStatusPolling();
  editor._editingDeviceConfig = true;
  editor._deviceConfigForm = { name: 'kitchen' };
  editor._store.actions.pushOverlay({ kind: 'device-settings', anchorKey: 'device-settings', subject: 'kitchen', draft: null });

  // What the router does on popstate: the URL changed without the editor's own switch.
  editor._store.actions.setRoute({ view: 'device', device: 'hall', panelView: 'preview' });
  editor._store.actions.stopSelectedStatusPolling();

  assert.deepEqual(editor._store.getState().ui.overlays, []);
  assert.equal(editor._deviceConfigForm, null);
  assert.equal(editor._store.getState().devices.selected, 'hall');
});

test('Back to Fleet closes the open sidebar', () => {
  const editor = routedEditor(TWO_DEVICES);
  editor._store.actions.setRoute({ view: 'device', device: 'kitchen', panelView: 'preview' });
  editor._store.actions.stopSelectedStatusPolling();
  editor._store.actions.pushOverlay({ kind: 'updates', anchorKey: 'updates', subject: 'kitchen', draft: null });

  editor._store.actions.setRoute({ view: 'fleet' });

  assert.deepEqual(editor._store.getState().ui.overlays, []);
});

test("Forward into a device closes Fleet's Logs sidebar", () => {
  const editor = routedEditor(TWO_DEVICES);
  editor._store.actions.setRoute({ view: 'fleet' });
  editor._store.actions.pushOverlay({ kind: 'logs', anchorKey: 'logs', subject: null, draft: null });

  editor._store.actions.setRoute({ view: 'device', device: 'kitchen', panelView: 'preview' });
  editor._store.actions.stopSelectedStatusPolling();

  assert.deepEqual(editor._store.getState().ui.overlays, []);
});

test('an editor that Home Assistant attaches again polls its device again', async () => {
  const editor = document.createElement('nspanel-haui-editor');
  editor.hass = makeHass({
    connection: { subscribeEvents: async () => () => {} },
    fetchWithAuth: async (url) => url.includes('/panels/')
      ? jsonResponse({
        version: 1,
        device_order: ['kitchen'],
        devices: { kitchen: { friendly_name: 'Kitchen', config: {}, panels: [] } },
      })
      : url.includes('/status/') ? jsonResponse({ devices: { kitchen: { connected: true } } })
        : jsonResponse([]),
  });
  await editor.store.actions.loadHub('entry1');
  editor.store.actions.stopSelectedStatusPolling();

  const polls = [];
  const { startSelectedStatusPolling, stopSelectedStatusPolling } = editor.store.actions;
  editor.store.actions.startSelectedStatusPolling = (...args) => {
    polls.push('start');
    return startSelectedStatusPolling(...args);
  };
  editor.store.actions.stopSelectedStatusPolling = (...args) => {
    polls.push('stop');
    return stopSelectedStatusPolling(...args);
  };

  document.body.append(editor);
  await flush();
  editor.remove();
  await flush();
  const startsBeforeReattach = polls.filter((entry) => entry === 'start').length;

  document.body.append(editor);
  await flush();
  editor.remove();
  await flush();

  assert.ok(polls.filter((entry) => entry === 'start').length > startsBeforeReattach);
  assert.equal(polls.at(-1), 'stop');
});

test('Settings opened from Fleet add a history entry, so Back returns to Fleet', async () => {
  const editor = routedEditor(TWO_DEVICES);
  editor._store.actions.setRoute({ view: 'fleet' });
  editor._store.actions.selectDevice('hall');
  editor._store.actions.stopSelectedStatusPolling();

  editor.api.devices.settings = async () => ({ config: {} });
  editor._openSettings();
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(editor.navigations, ['hall']);
  assert.deepEqual(editor.replaced, [false]);
  assert.equal(editor._store.getState().ui.overlays.at(-1)?.kind, 'device-settings');

  editor._store.actions.setRoute({ view: 'fleet' });
  assert.deepEqual(editor._store.getState().ui.overlays, []);
});
