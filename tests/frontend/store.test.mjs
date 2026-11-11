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

test('view mode and group open state persist to storage', () => {
  const storage = memoryStorage();
  const store = createStore({ client: client(), storage });

  store.actions.setViewMode('list');
  store.actions.setGroupOpen('nav', false);
  store.actions.setGroupOpen('system', true);

  assert.equal(store.getState().ui.viewMode, 'list');
  assert.equal(store.getState().ui.groupOpen.nav, false);
  assert.equal(store.getState().ui.groupOpen.system, true);
  assert.equal(storage.values.get('haui_viewMode'), 'list');
  assert.equal(storage.values.get('haui_navPanelsOpen'), 'false');
  assert.equal(storage.values.get('haui_systemPanelsOpen'), 'true');
});
