import { test } from 'node:test';
import assert from 'node:assert/strict';

import { createStore } from '../../custom_components/nspanel_haui/frontend/store/store.js';

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    values,
    read: (key, fallback) => values.get(key) ?? fallback,
    write: (key, value) => values.set(key, String(value)),
  };
}

function client(overrides = {}) {
  const saves = [];
  return {
    saves,
    language: () => 'en',
    connection: () => null,
    panels: {
      load: async () => ({ devices: {} }),
      save: async (entryId, payload) => {
        saves.push(payload);
        return { status: 'ok' };
      },
    },
    status: {
      get: async () => ({}),
      getAll: async () => ({}),
    },
    notifications: {
      list: async () => [],
      dismiss: async () => ({ status: 'ok' }),
      subscribe: async () => () => {},
    },
    editor: { panelTypes: async () => [] },
    ...overrides,
  };
}

/** Await a store action that resolves after the fake backend answered. */
const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

function seededStore(options = {}) {
  const store = createStore({
    client: client(options.client),
    storage: memoryStorage(options.storage),
    onToast: options.onToast,
  });
  store.setState((state) => ({
    ...state,
    hub: {
      ...state.hub,
      entryId: 'entry1',
      loading: false,
      systemPanels: [{ key: 'sys_settings', editable: false }],
    },
    devices: {
      byName: {
        kitchen: { friendlyName: 'Kitchen', config: {}, panels: [{ key: 'a', type: 'clock' }], status: null },
        office: { friendlyName: 'Office', config: {}, panels: [], status: null },
      },
      order: ['kitchen', 'office'],
      selected: 'kitchen',
    },
  }));
  return store;
}

test('one save in flight refuses the next one and only commits the accepted panels', async () => {
  let release;
  const saves = [];
  const store = seededStore({
    client: {
      panels: {
        load: async () => ({ devices: {} }),
        save: async (entryId, payload) => {
          saves.push(payload);
          return new Promise((resolve) => { release = () => resolve({ status: 'ok' }); });
        },
      },
    },
  });

  const first = store.actions.savePanels({
    panels: [{ key: 'a', type: 'clock' }],
    toastMessage: 'first',
  });
  const second = await store.actions.savePanels({ panels: [], toastMessage: 'second' });

  assert.equal(second, false);
  assert.equal(saves.length, 1);
  release();
  assert.equal(await first, true);
  assert.deepEqual(store.getState().devices.byName.kitchen.panels, [{ key: 'a', type: 'clock' }]);
});

test('a rejected save leaves the state unchanged and reports the server message', async () => {
  const store = seededStore({
    client: {
      panels: {
        load: async () => ({ devices: {} }),
        save: async () => { throw new Error('Invalid panel config'); },
      },
    },
  });

  const saved = await store.actions.savePanels({
    panels: [],
    toastMessage: 'save',
    deviceConfig: { enabled: false },
    deviceName: 'kitchen',
  });

  assert.equal(saved, false);
  assert.equal(store.getState().hub.saving, false);
  assert.equal(store.getState().hub.error, 'Invalid panel config');
  assert.deepEqual(store.getState().devices.byName.kitchen.panels, [{ key: 'a', type: 'clock' }]);
  assert.deepEqual(store.getState().devices.byName.kitchen.config, {});
});

test('a status response for the previously selected device is dropped', async () => {
  let release;
  const store = seededStore({
    client: {
      status: {
        get: () => new Promise((resolve) => { release = resolve; }),
        getAll: async () => ({}),
      },
    },
  });

  const request = store.actions.pollSelectedStatus();
  store.setState((state) => ({
    ...state,
    devices: { ...state.devices, selected: 'office' },
  }));
  release({ connected: true, ip: '10.0.0.1' });
  await request;

  assert.equal(store.selectors.selectedStatus(), null);
  store.actions.stopSelectedStatusPolling();
});

test('a failed all-device poll reports its error until a poll succeeds again', async () => {
  let fail = true;
  const store = seededStore({
    client: {
      status: {
        get: async () => ({}),
        getAll: async () => {
          if (fail) throw new Error('offline');
          return { kitchen: { connected: true } };
        },
      },
    },
  });
  const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

  store.actions.startAllStatusPolling();
  await settle();
  store.actions.stopAllStatusPolling();
  assert.equal(store.getState().hub.statusError, 'offline');

  fail = false;
  store.actions.startAllStatusPolling();
  await settle();
  store.actions.stopAllStatusPolling();
  assert.equal(store.getState().hub.statusError, null);
  assert.equal(store.getState().devices.byName.kitchen.status.connected, true);
});

test('selecting a device shows only its cached status while fetching the new one', async () => {
  let resolveRequest;
  const store = seededStore({
    client: {
      status: {
        get: () => new Promise((resolve) => { resolveRequest = resolve; }),
        getAll: async () => ({}),
      },
    },
  });
  store.setState((state) => ({
    ...state,
    devices: {
      ...state.devices,
      byName: {
        ...state.devices.byName,
        kitchen: { ...state.devices.byName.kitchen, status: { connected: true, ip: '10.0.0.1' } },
        office: { ...state.devices.byName.office, status: { connected: true, ip: '10.0.0.2' } },
      },
    },
  }));

  assert.equal(store.selectors.selectedStatus().ip, '10.0.0.1');
  store.actions.selectDevice('office');
  assert.equal(store.selectors.selectedStatus().ip, '10.0.0.2');
  resolveRequest({ connected: true, ip: '10.0.0.3' });
  await settle();
  assert.equal(store.selectors.selectedStatus().ip, '10.0.0.3');
  store.actions.stopSelectedStatusPolling();
});

test('loadHub keeps the selected device and loads statuses before loading ends', async () => {
  let releaseStatuses;
  const store = createStore({
    client: client({
      panels: {
        load: async () => ({
          devices: {
            kitchen: { friendly_name: 'Kitchen', config: {}, panels: [] },
            office: { friendly_name: 'Office', config: {}, panels: [] },
          },
        }),
      },
      status: {
        get: async () => ({}),
        getAll: () => new Promise((resolve) => { releaseStatuses = resolve; }),
      },
    }),
    storage: memoryStorage(),
  });
  store.setState((state) => ({
    ...state,
    devices: {
      byName: {},
      order: ['kitchen', 'office'],
      selected: 'office',
    },
  }));

  const loading = store.actions.loadHub('entry1');
  await settle();
  assert.equal(store.getState().hub.loading, true);
  assert.equal(store.getState().devices.selected, 'office');

  releaseStatuses({ kitchen: { connected: true }, office: { connected: true, ip: '10.0.0.2' } });
  await loading;
  await settle();
  assert.equal(store.getState().hub.loading, false);
  assert.equal(store.selectors.selectedStatus().ip, '10.0.0.2');
  store.actions.stopSelectedStatusPolling();
});

test('device order round-trips in the panel store and can be reordered atomically', async () => {
  const saved = [];
  const store = seededStore({
    client: {
      panels: {
        load: async () => ({ devices: {} }),
        save: async (entryId, payload) => { saved.push(payload); return { status: 'ok' }; },
      },
    },
  });

  assert.equal(await store.actions.reorderDevices(['office', 'kitchen']), true);
  assert.deepEqual(store.getState().devices.order, ['office', 'kitchen']);
  assert.deepEqual(saved[0].device_order, ['office', 'kitchen']);
});

test('failed device reorder restores the prior order', async () => {
  const store = seededStore({
    client: { panels: { load: async () => ({ devices: {} }), save: async () => { throw new Error('save failed'); } } },
  });

  assert.equal(await store.actions.reorderDevices(['office', 'kitchen']), false);
  assert.deepEqual(store.getState().devices.order, ['kitchen', 'office']);
});

test('route and overlays update shared UI state; Escape can close overlays in stack order', () => {
  const store = seededStore();
  store.actions.setRoute({ view: 'device', device: 'office', panel: 'popup_notify', panelView: 'panels' });
  store.actions.pushOverlay({ kind: 'sidebar', anchorKey: 'configure', subject: 'device', draft: null });
  store.actions.pushOverlay({ kind: 'menu', anchorKey: 'panel-menu', subject: 'clock', draft: null });

  assert.equal(store.getState().ui.route.device, 'office');
  assert.deepEqual(store.getState().ui.overlays.map(({ kind }) => kind), ['sidebar', 'menu']);
  store.actions.closeTopOverlay();
  assert.deepEqual(store.getState().ui.overlays.map(({ kind }) => kind), ['sidebar']);
  store.actions.closeOverlay('sidebar', 'wrong-anchor');
  assert.deepEqual(store.getState().ui.overlays.map(({ kind }) => kind), ['sidebar']);
  store.actions.pushOverlay({ kind: 'menu', anchorKey: 'another-menu', subject: null, draft: null });
  store.actions.closeOverlay('menu', 'another-menu');
  assert.deepEqual(store.getState().ui.overlays.map(({ kind }) => kind), ['sidebar']);
});
