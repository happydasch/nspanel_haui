// @ts-check
/**
 * NSPanel HAUI - the editor store.
 *
 * One observable store owns the editor's shared state: the hub entry, the
 * devices (config, panels, status), the notification queue and the persisted
 * UI preferences. Only the actions here write it; views read it through the
 * shell or the selectors.
 */

import { DEVICE_CONFIG_DEFAULTS } from '../constants.js';
import { t } from '../localize.js';

/** @typedef {import('../api/types.js').PanelStore} PanelStore */
/** @typedef {import('../api/types.js').DeviceEntry} DeviceEntry */
/** @typedef {import('../api/types.js').DeviceConfig} DeviceConfig */
/** @typedef {import('../api/types.js').PanelConfig} PanelConfig */
/** @typedef {import('../api/types.js').DeviceStatus} DeviceStatus */
/** @typedef {import('../api/types.js').Notification} Notification */
/** @typedef {import('../api/types.js').ColorScheme} ColorScheme */
/** @typedef {import('../api/types.js').PanelTypeDescriptor} PanelTypeDescriptor */
/** @typedef {import('../api/types.js').SystemPanel} SystemPanel */
/** @typedef {import('../api/client.js').ApiClient} ApiClient */

/**
 * @typedef {Object} DeviceState
 * @property {string} friendlyName
 * @property {DeviceConfig} config
 * @property {PanelConfig[]} panels
 * @property {DeviceStatus|null} status
 */

/**
 * @typedef {Object} DevicesState
 * @property {Object<string, DeviceState>} byName
 * @property {string[]} order
 * @property {string|null} selected
 */

/**
 * @typedef {Object} StoreState
 * @property {{ entryId: string|null, loading: boolean, saving: boolean, error: string|null, statusError: string|null, panelTypes: PanelTypeDescriptor[], systemPanels: SystemPanel[], colorSchemes: Object<string, ColorScheme> }} hub
 * @property {DevicesState} devices
 * @property {Notification[]} notifications
 * @property {{ viewMode: "grid"|"list", toast: { message: string, type: string }|null, dialogs: Object<string, any>, menus: Object<string, any>, groupOpen: { system: boolean, popup: boolean, nav: boolean, hidden: boolean } }} ui
 */

/**
 * @typedef {Object} StoreStorage
 * @property {(key: string, fallback: string) => string} read
 * @property {(key: string, value: string|boolean) => void} write
 */

const GROUP_STORAGE = {
  system: 'haui_systemPanelsOpen',
  popup: 'haui_popupPanelsOpen',
  nav: 'haui_navPanelsOpen',
  hidden: 'haui_hiddenPanelsOpen',
};

const DEFAULT_DEVICE_CONFIG = (() => {
  const config = mergeDeviceConfig(undefined);
  return Object.freeze({ ...config, update: Object.freeze(config.update) });
})();

/** @param {DeviceConfig|undefined} config */
export function mergeDeviceConfig(config) {
  const existing = config || {};
  return {
    ...DEVICE_CONFIG_DEFAULTS,
    ...existing,
    // The update block is nested; merge it over its defaults so a partial
    // stored block still shows the shipped defaults in the editor.
    update: { ...DEVICE_CONFIG_DEFAULTS.update, ...(existing.update || {}) },
  };
}

/**
 * Build the state's device map from a panel store payload.
 *
 * @param {PanelStore} payload
 * @param {DevicesState} [previous]
 * @returns {DevicesState}
 */
export function devicesFromStore(payload, previous) {
  /** @type {Object<string, DeviceState>} */
  const byName = {};
  const order = Object.keys(payload.devices || {});
  for (const name of order) {
    const entry = /** @type {DeviceEntry} */ (payload.devices[name] || {});
    byName[name] = {
      friendlyName: entry.friendly_name || name,
      config: mergeDeviceConfig(entry.config),
      panels: entry.panels || [],
      status: previous?.byName[name]?.status ?? null,
    };
  }
  const selected = previous?.selected && byName[previous.selected]
    ? previous.selected
    : order[0] || null;
  return { byName, order, selected };
}

/**
 * The POST body for the current state.
 *
 * @param {StoreState} state
 * @returns {PanelStore}
 */
export function panelStoreFromState(state) {
  /** @type {Object<string, DeviceEntry>} */
  const devices = {};
  for (const name of state.devices.order) {
    const device = state.devices.byName[name];
    devices[name] = {
      friendly_name: device.friendlyName,
      config: device.config,
      panels: device.panels,
    };
  }
  return {
    version: 1,
    color_schemes: state.hub.colorSchemes,
    system_panels: state.hub.systemPanels,
    devices,
  };
}

/**
 * @param {StoreStorage} storage
 * @returns {StoreState}
 */
function createInitialState(storage) {
  const readGroup = (group, fallback) => {
    const raw = storage.read(GROUP_STORAGE[group], '');
    if (raw === '') return fallback;
    return raw !== 'false';
  };
  return {
    hub: {
      entryId: null,
      loading: true,
      saving: false,
      error: null,
      statusError: null,
      panelTypes: [],
      systemPanels: [],
      colorSchemes: {},
    },
    devices: { byName: {}, order: [], selected: null },
    notifications: [],
    ui: {
      viewMode: storage.read('haui_viewMode', 'grid') === 'list' ? 'list' : 'grid',
      toast: null,
      dialogs: {},
      menus: {},
      groupOpen: {
        system: readGroup('system', false),
        popup: readGroup('popup', true),
        nav: readGroup('nav', true),
        hidden: readGroup('hidden', true),
      },
    },
  };
}

/**
 * @param {{ client: ApiClient, storage: StoreStorage, onToast?: (message: string, type: string) => void }} options
 */
export function createStore({ client, storage, onToast }) {
  /** @type {StoreState} */
  let state = createInitialState(storage);
  /** @type {Set<(state: StoreState, previous: StoreState) => void>} */
  const listeners = new Set();

  /** @type {ReturnType<typeof setInterval>|null} */
  let selectedTimer = null;
  /** @type {ReturnType<typeof setInterval>|null} */
  let allTimer = null;
  /** @type {string|null} */
  let polledDevice = null;

  /** @type {(() => void)|null} */
  let notificationUnsubscribe = null;
  /** @type {any} */
  let notificationConnection = null;

  let panelTypesLanguage = null;
  /** @type {Promise<void>|null} */
  let panelTypesPromise = null;
  /** @type {Promise<void>|null} */
  let notificationsPromise = null;

  /**
   * @param {(current: StoreState) => StoreState} updater
   */
  function commit(updater) {
    const previous = state;
    const next = updater(previous);
    if (next === previous) return;
    state = next;
    for (const listener of listeners) listener(state, previous);
  }

  /** @param {any} partial */
  function setState(partial) {
    if (typeof partial === 'function') {
      commit(partial);
      return;
    }
    commit((current) => ({ ...current, ...partial }));
  }

  function showToast(message, type = 'success') {
    if (!message) return;
    const toast = { message, type };
    commit((current) => ({ ...current, ui: { ...current.ui, toast } }));
    onToast?.(message, type);
    const timer = setTimeout(() => {
      if (state.ui.toast !== toast) return;
      commit((current) => ({ ...current, ui: { ...current.ui, toast: null } }));
    }, 3000);
    /** @type {any} */ (timer).unref?.();
  }

  const actions = {
    /** @param {boolean} loading */
    setLoading(loading) {
      commit((current) => ({ ...current, hub: { ...current.hub, loading } }));
    },

    /**
     * Load the hub entry: panel store, panel types, statuses and notifications.
     * The selected device survives a reload when it still exists.
     *
     * @param {string|null} entryId
     */
    async loadHub(entryId) {
      if (!entryId) {
        commit((current) => ({
          ...current,
          hub: { ...current.hub, entryId: null, loading: false },
        }));
        return;
      }
      commit((current) => ({
        ...current,
        hub: { ...current.hub, entryId, loading: true, error: null, statusError: null },
      }));

      const lang = client.language();
      /** @type {PanelStore} */
      let payload;
      try {
        payload = await client.panels.load(entryId, lang);
      } catch (error) {
        const message = /** @type {Error} */ (error).message || t('Failed to load panels');
        commit((current) => ({
          ...current,
          hub: { ...current.hub, loading: false, error: message },
        }));
        showToast(t('Failed to load panels'), 'error');
        return;
      }

      /** @type {Object<string, DeviceStatus>} */
      let statuses = {};
      let statusError = null;
      try {
        statuses = await client.status.getAll(entryId);
      } catch (error) {
        statusError = /** @type {Error} */ (error).message || t('Fetch failed');
      }

      commit((current) => {
        const devices = devicesFromStore(payload, current.devices);
        for (const name of devices.order) {
          const status = statuses[name];
          if (status) devices.byName[name].status = status;
        }
        return {
          ...current,
          hub: {
            ...current.hub,
            entryId,
            loading: false,
            statusError,
            systemPanels: payload.system_panels || [],
            colorSchemes: payload.color_schemes || {},
          },
          devices,
        };
      });

      void actions.loadPanelTypes();
      void actions.loadNotifications();
      const selected = state.devices.selected;
      if (selected) {
        actions.startSelectedStatusPolling({ refresh: !statuses[selected] });
      }
    },

    /**
     * Reload the panel store after a device was added or removed.
     */
    async loadPanels() {
      const entryId = state.hub.entryId;
      if (!entryId) return;
      try {
        const payload = await client.panels.load(entryId, client.language());
        commit((current) => ({
          ...current,
          hub: {
            ...current.hub,
            systemPanels: payload.system_panels || [],
            colorSchemes: payload.color_schemes || {},
          },
          devices: devicesFromStore(payload, current.devices),
        }));
      } catch (error) {
        showToast(t('Failed to load panels'), 'error');
      }
    },

    /**
     * Load the panel type descriptors for the current language.
     * @param {{ force?: boolean }} [options]
     */
    async loadPanelTypes({ force = false } = {}) {
      const lang = client.language();
      if (!force && panelTypesLanguage === lang && state.hub.panelTypes.length) return;
      if (panelTypesPromise) return panelTypesPromise;
      panelTypesPromise = (async () => {
        try {
          const panelTypes = await client.editor.panelTypes(lang);
          panelTypesLanguage = lang;
          commit((current) => ({ ...current, hub: { ...current.hub, panelTypes } }));
        } catch (error) {
          showToast(t('Failed to load panel types'), 'error');
        } finally {
          panelTypesPromise = null;
        }
      })();
      return panelTypesPromise;
    },

    /**
     * Load the notification queue.
     */
    async loadNotifications() {
      const entryId = state.hub.entryId;
      if (!entryId) return;
      if (notificationsPromise) return notificationsPromise;
      notificationsPromise = (async () => {
        try {
          const notifications = await client.notifications.list(entryId);
          commit((current) => ({ ...current, notifications }));
        } catch (error) {
          showToast(t('Failed to load notifications'), 'error');
        } finally {
          notificationsPromise = null;
        }
      })();
      return notificationsPromise;
    },

    /** Subscribe to the hub's live notification events (once per connection). */
    subscribeNotifications() {
      const connection = client.connection();
      if (!connection || notificationConnection === connection) return;
      actions.stopNotifications();
      notificationConnection = connection;
      client.notifications
        .subscribe((notification) => {
          if (!notification?.id || !notification.device) return;
          const key = `${notification.device}:${notification.id}`;
          commit((current) => {
            const remaining = current.notifications.filter(
              (item) => `${item.device}:${item.id}` !== key,
            );
            return {
              ...current,
              notifications:
                notification.state === 'removed' ? remaining : [...remaining, notification],
            };
          });
        })
        .then((unsubscribe) => {
          if (notificationConnection !== connection) unsubscribe();
          else notificationUnsubscribe = unsubscribe;
        })
        .catch((error) => {
          console.error('Failed to subscribe to NSPanel HAUI notifications:', error);
        });
    },

    stopNotifications() {
      notificationUnsubscribe?.();
      notificationUnsubscribe = null;
      notificationConnection = null;
    },

    /**
     * Dismiss one queued notification on the server, then in the store.
     * @param {string} device
     * @param {string} id
     */
    async dismissNotification(device, id) {
      const entryId = state.hub.entryId;
      if (!entryId) return;
      try {
        await client.notifications.dismiss(entryId, device, id);
        commit((current) => ({
          ...current,
          notifications: current.notifications.filter(
            (item) => item.device !== device || item.id !== id,
          ),
        }));
      } catch (error) {
        showToast(t('Failed to dismiss notification'), 'error');
      }
    },

    /**
     * Select a device and start polling its status.
     * @param {string} name
     */
    selectDevice(name) {
      if (!name || !state.devices.byName[name]) return;
      commit((current) => ({
        ...current,
        devices: { ...current.devices, selected: name },
        hub: { ...current.hub, statusError: null },
      }));
      actions.startSelectedStatusPolling();
    },

    /**
     * Start the selected-device status poller. Restarts when the selected
     * device changed; a no-op while the same device is already polled.
     * @param {{ refresh?: boolean }} [options]
     */
    startSelectedStatusPolling({ refresh = true } = {}) {
      const selected = state.devices.selected;
      if (!selected) {
        actions.stopSelectedStatusPolling();
        return;
      }
      if (selectedTimer && polledDevice === selected) return;
      actions.stopSelectedStatusPolling();
      polledDevice = selected;
      if (refresh) void actions.pollSelectedStatus();
      selectedTimer = setInterval(() => {
        void actions.pollSelectedStatus();
      }, 5000);
    },

    stopSelectedStatusPolling() {
      if (selectedTimer) {
        clearInterval(selectedTimer);
        selectedTimer = null;
      }
      polledDevice = null;
    },

    /**
     * Fetch the selected device's status once. A response for a device that is
     * no longer selected is dropped.
     */
    async pollSelectedStatus() {
      const entryId = state.hub.entryId;
      const selected = state.devices.selected;
      if (!entryId) {
        commit((current) => ({
          ...current,
          hub: { ...current.hub, statusError: t('No device selected') },
        }));
        return;
      }
      const requested = selected || '';
      /** @type {DeviceStatus|null} */
      let status = null;
      /** @type {Object<string, DeviceStatus>|null} */
      let statuses = null;
      let error = null;
      try {
        const result = /** @type {any} */ (await client.status.get(entryId, requested));
        if (result?.devices && typeof result.devices === 'object') {
          statuses = result.devices;
        } else {
          status = /** @type {DeviceStatus} */ (result);
        }
      } catch (caught) {
        error = /** @type {Error} */ (caught).message || t('Fetch failed');
      }
      // The user may have switched devices while this request was in flight.
      if (state.devices.selected !== selected) return;

      const selectedStatus = statuses ? statuses[requested] || null : status;
      commit((current) => {
        const byName = { ...current.devices.byName };
        if (statuses) {
          for (const [name, deviceStatus] of Object.entries(statuses)) {
            if (byName[name]) byName[name] = { ...byName[name], status: deviceStatus };
          }
        }
        if (requested && byName[requested]) {
          byName[requested] = { ...byName[requested], status: selectedStatus };
        }
        return {
          ...current,
          devices: { ...current.devices, byName },
          hub: { ...current.hub, statusError: error },
        };
      });
    },

    /** Start the all-device status poller (open Device Manager). */
    startAllStatusPolling() {
      if (allTimer) return;
      const fetchAll = async () => {
        const entryId = state.hub.entryId;
        if (!entryId) return;
        try {
          const statuses = await client.status.getAll(entryId);
          commit((current) => {
            const byName = { ...current.devices.byName };
            for (const [name, status] of Object.entries(statuses)) {
              if (byName[name]) byName[name] = { ...byName[name], status };
            }
            return { ...current, devices: { ...current.devices, byName } };
          });
        } catch (error) {
          // A stale status is harmless; the next tick tries again.
        }
      };
      void fetchAll();
      allTimer = setInterval(fetchAll, 5000);
    },

    stopAllStatusPolling() {
      if (allTimer) {
        clearInterval(allTimer);
        allTimer = null;
      }
    },

    /**
     * Persist the selected (or given) device's panels and config.
     *
     * Each save sends the whole store, so a save started before the previous
     * one returns would be built from stale data: it is refused. State only
     * changes once the server accepts the save.
     *
     * @param {{ panels: PanelConfig[], toastMessage?: string, deviceConfig?: DeviceConfig, deviceName?: string }} payload
     * @returns {Promise<boolean>}
     */
    async savePanels({ panels, toastMessage, deviceConfig, deviceName }) {
      const name = deviceName || state.devices.selected;
      const entryId = state.hub.entryId;
      if (!name || !entryId) return false;
      if (state.devices.byName[name] === undefined) return false;
      if (state.hub.saving) {
        showToast(t('Another save is still in progress'), 'error');
        return false;
      }

      commit((current) => ({ ...current, hub: { ...current.hub, saving: true } }));

      const payload = panelStoreFromState(state);
      const device = payload.devices[name] || (payload.devices[name] = {});
      device.panels = panels;
      const nextConfig = deviceConfig ? mergeDeviceConfig(deviceConfig) : null;
      if (nextConfig) device.config = nextConfig;

      let saved = false;
      try {
        await client.panels.save(entryId, payload);
        commit((current) => {
          const byName = { ...current.devices.byName };
          const currentDevice = byName[name];
          byName[name] = {
            ...currentDevice,
            panels,
            config: nextConfig || currentDevice.config,
          };
          return {
            ...current,
            devices: { ...current.devices, byName },
            hub: { ...current.hub, saving: false, error: null },
          };
        });
        showToast(toastMessage, 'success');
        saved = true;
      } catch (error) {
        const message = /** @type {Error} */ (error).message || t('Network error');
        commit((current) => ({
          ...current,
          hub: { ...current.hub, saving: false, error: message },
        }));
        showToast(message, 'error');
      }
      return saved;
    },

    /**
     * Move a device one position up (-1) or down (1), restoring the order when
     * the save is rejected.
     * @param {string} name
     * @param {number} direction
     */
    async moveDevice(name, direction) {
      const order = state.devices.order;
      const index = order.indexOf(name);
      if (index < 0) return;
      const swapIndex = index + direction;
      if (swapIndex < 0 || swapIndex >= order.length) return;
      const newOrder = [...order];
      [newOrder[index], newOrder[swapIndex]] = [newOrder[swapIndex], newOrder[index]];
      commit((current) => ({ ...current, devices: { ...current.devices, order: newOrder } }));

      const friendly = state.devices.byName[name].friendlyName;
      const message = direction < 0
        ? t('Device "{name}" moved up').replace('{name}', friendly)
        : t('Device "{name}" moved down').replace('{name}', friendly);
      const saved = await actions.savePanels({
        panels: state.devices.byName[name].panels,
        toastMessage: message,
        deviceName: name,
      });
      if (!saved) {
        commit((current) => ({
          ...current,
          devices: { ...current.devices, order },
          hub: { ...current.hub, error: null },
        }));
      }
    },

    /**
     * Enable or disable a device (settings live in its config block).
     * @param {string} name
     */
    async toggleDevice(name) {
      const device = state.devices.byName[name];
      if (!device) return;
      const enabled = device.config.enabled === false;
      const message = `"${device.friendlyName}" ${enabled ? t('enabled') : t('disabled')}`;
      await actions.savePanels({
        panels: device.panels,
        toastMessage: message,
        deviceConfig: { ...device.config, enabled },
        deviceName: name,
      });
    },

    /** @param {"grid"|"list"} mode */
    setViewMode(mode) {
      if (mode !== 'grid' && mode !== 'list') return;
      commit((current) => ({ ...current, ui: { ...current.ui, viewMode: mode } }));
      storage.write('haui_viewMode', mode);
    },

    /**
     * Persist a collapsible panel group's open state.
     * @param {keyof typeof GROUP_STORAGE} group
     * @param {boolean} open
     */
    setGroupOpen(group, open) {
      if (!(group in GROUP_STORAGE)) return;
      commit((current) => ({
        ...current,
        ui: { ...current.ui, groupOpen: { ...current.ui.groupOpen, [group]: open } },
      }));
      storage.write(GROUP_STORAGE[group], open);
    },

    showToast,
  };

  const selectors = {
    /** @returns {StoreState} */
    state() {
      return state;
    },

    /** @returns {string|null} */
    selectedName() {
      return state.devices.selected;
    },

    /** @returns {DeviceState|null} */
    selected() {
      return state.devices.selected ? state.devices.byName[state.devices.selected] || null : null;
    },

    /**
     * @param {string|null} [name]
     * @returns {PanelConfig[]}
     */
    devicePanels(name = state.devices.selected) {
      if (!name) return [];
      return state.devices.byName[name]?.panels || [];
    },

    /**
     * The device's settings with the shipped defaults merged in.
     * @param {string|null} [name]
     * @returns {DeviceConfig}
     */
    configFor(name = state.devices.selected) {
      if (!name) return DEFAULT_DEVICE_CONFIG;
      return state.devices.byName[name]?.config || DEFAULT_DEVICE_CONFIG;
    },

    /** @returns {Object<string, DeviceStatus>} */
    statuses() {
      /** @type {Object<string, DeviceStatus>} */
      const result = {};
      for (const name of state.devices.order) {
        const status = state.devices.byName[name].status;
        if (status) result[name] = status;
      }
      return result;
    },

    /** @returns {DeviceStatus|null} */
    selectedStatus() {
      return selectors.selected()?.status || null;
    },

    /** @returns {Object<string, any>|null} */
    selectedDeviceInfo() {
      return selectors.selectedStatus()?.device_info || null;
    },

    /** @returns {PanelStore} */
    panelStore() {
      return panelStoreFromState(state);
    },
  };

  return {
    getState: () => state,
    subscribe(/** @type {(state: StoreState, previous: StoreState) => void} */ listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setState,
    actions,
    selectors,
  };
}
