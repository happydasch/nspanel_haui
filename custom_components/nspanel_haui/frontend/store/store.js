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
/** @typedef {import('../api/types.js').Theme} Theme */
/** @typedef {import('../api/types.js').PanelTypeDescriptor} PanelTypeDescriptor */
/** @typedef {import('../api/types.js').PanelTemplate} PanelTemplate */
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
 * Overlay kinds rendered as anchored popovers. Only one is open at a time: a
 * new one closes the previous, while sidebars stack on top of it.
 */
const ANCHORED_OVERLAY_KINDS = Object.freeze([
  'panel-menu', 'device-menu', 'notification-centre',
]);

/** @param {string|null|undefined} kind */
export function isAnchoredOverlayKind(kind) {
  return typeof kind === 'string' && ANCHORED_OVERLAY_KINDS.includes(kind);
}

/**
 * Overlay kinds shown in the Device screen's modal sidebar (Logs also on
 * Fleet: its subject is a device, or null for every device). The topmost one is
 * shown; one opened from another covers it as a layer.
 */
export const SIDEBAR_OVERLAY_KINDS = Object.freeze([
  'device-settings', 'device-schedule', 'device-gestures',
  'panel-catalog', 'panel-editor', 'firmware', 'theme', 'logs',
]);

/** @param {string|null|undefined} kind */
export function isSidebarOverlayKind(kind) {
  return typeof kind === 'string' && SIDEBAR_OVERLAY_KINDS.includes(kind);
}

/**
 * The Preview view's device option sidebars — one editor each for the device's
 * schedule and gestures, opened from the Manage this device card. The theme has
 * no sidebar of its own: its button opens the shared theme editor.
 */
const DEVICE_OPTION_OVERLAY_KINDS = Object.freeze([
  'device-schedule', 'device-gestures',
]);

/** @param {string|null|undefined} kind */
export function isDeviceOptionOverlayKind(kind) {
  return typeof kind === 'string' && DEVICE_OPTION_OVERLAY_KINDS.includes(kind);
}

/**
 * @typedef {Object} DevicesState
 * @property {Object<string, DeviceState>} byName
 * @property {string[]} order
 * @property {string|null} selected
 */

/**
 * @typedef {{ view: 'fleet'|'device', device: string|null, panel: string|null, panelView: 'preview'|'panels' }} Route
 * @typedef {{ kind: string, anchorKey: string|null, subject: string|null, draft: any }} Overlay
 *
 * @typedef {Object} StoreState
 * @property {{ entryId: string|null, loading: boolean, saving: boolean, error: string|null, fieldErrors: Array<{ panel: string, field: string, kind: string, message: string }>, statusError: string|null, panelTypes: PanelTypeDescriptor[], panelTemplates: PanelTemplate[], rollout: Record<string, any>|null, systemPanels: SystemPanel[], themes: Object<string, Theme> }} hub
 * @property {DevicesState} devices
 * @property {Notification[]} notifications
 * @property {{ route: Route, overlays: Overlay[], toast: { message: string, type: string }|null, dialogs: Object<string, any>, menus: Object<string, any>, preview: { mode: 'simulated'|'live', idle: boolean, showEntities: boolean } }} ui
 */

/**
 * @typedef {Object} StoreStorage
 * @property {(key: string, fallback: string) => string} read
 * @property {(key: string, value: string|boolean) => void} write
 */

const DEFAULT_DEVICE_CONFIG = (() => {
  const config = mergeDeviceConfig(undefined);
  return Object.freeze({ ...config, update: Object.freeze(config.update) });
})();

/** @param {DeviceConfig|undefined} config */
function mergeDeviceConfig(config) {
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
  const payloadOrder = Array.isArray(payload.device_order) ? payload.device_order : [];
  const names = Object.keys(payload.devices || {});
  const order = [...new Set(payloadOrder.filter((name) => names.includes(name))),
    ...names.filter((name) => !payloadOrder.includes(name))];
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

/** Nobody sees a status poll's result while the browser tab is in the background. */
function pageHidden() {
  return globalThis.document?.hidden === true;
}

/**
 * The device map with the polled statuses, or the same map while every device
 * reports what it reported before: a poll that changes nothing must not
 * re-render the editor.
 *
 * @param {Object<string, DeviceState>} byName
 * @param {Object<string, DeviceStatus|null>} statuses
 * @returns {Object<string, DeviceState>}
 */
function withStatuses(byName, statuses) {
  let next = byName;
  for (const [name, status] of Object.entries(statuses)) {
    const device = byName[name];
    if (!device || JSON.stringify(device.status) === JSON.stringify(status)) continue;
    if (next === byName) next = { ...byName };
    next[name] = { ...device, status };
  }
  return next;
}

/**
 * @param {StoreStorage} storage
 * @returns {StoreState}
 */
function createInitialState(storage) {
  return {
    hub: {
      entryId: null,
      loading: true,
      saving: false,
      error: null,
      // The fields the hub named when it refused the last panel save.
      fieldErrors: [],
      statusError: null,
      panelTypes: [],
      // The starter templates of the Add panel catalog.
      panelTemplates: [],
      // Fleet's one-at-a-time update rollout; null until read.
      rollout: null,
      systemPanels: [],
      themes: {},
    },
    devices: { byName: {}, order: [], selected: null },
    notifications: [],
    ui: {
      route: { view: 'fleet', device: null, panel: null, panelView: 'preview' },
      overlays: [],
      toast: null,
      dialogs: {},
      menus: {},
      preview: { mode: 'simulated', idle: false, showEntities: false },
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
            themes: payload.themes || {},
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
            themes: payload.themes || {},
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
          // The catalog works without its starter templates; panel types never wait on them.
          const templates = client.editor.panelTemplates(lang).catch(() => {
            showToast(t('Failed to load panel templates'), 'error');
            return [];
          });
          const panelTypes = await client.editor.panelTypes(lang);
          const panelTemplates = await templates;
          panelTypesLanguage = lang;
          commit((current) => ({ ...current, hub: { ...current.hub, panelTypes, panelTemplates } }));
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
        // The all-device poller already reports this device.
        if (allTimer || pageHidden()) return;
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
        const byName = withStatuses(current.devices.byName, {
          ...statuses,
          ...(requested ? { [requested]: selectedStatus } : {}),
        });
        if (byName === current.devices.byName && current.hub.statusError === error) return current;
        return {
          ...current,
          devices: { ...current.devices, byName },
          hub: { ...current.hub, statusError: error },
        };
      });
    },

    /** Start the all-device status poller (the Fleet screen shows every device). */
    startAllStatusPolling() {
      if (allTimer) return;
      const fetchAll = async () => {
        const entryId = state.hub.entryId;
        if (!entryId || pageHidden()) return;
        /** @type {Object<string, DeviceStatus>|null} */
        let statuses = null;
        let error = null;
        try {
          statuses = await client.status.getAll(entryId);
        } catch (caught) {
          // The statuses shown are now stale: say so until a poll succeeds again.
          error = /** @type {Error} */ (caught).message || t('Fetch failed');
        }
        commit((current) => {
          const byName = statuses ? withStatuses(current.devices.byName, statuses) : current.devices.byName;
          if (byName === current.devices.byName && current.hub.statusError === error) return current;
          return {
            ...current,
            devices: { ...current.devices, byName },
            hub: { ...current.hub, statusError: error },
          };
        });
        // A running rollout changes every tick; an idle one only when started.
        if (!state.hub.rollout || state.hub.rollout.state === 'running') {
          try {
            const rollout = await client.updates.rollout(entryId);
            commit((current) => ({ ...current, hub: { ...current.hub, rollout } }));
          } catch (caught) {
            commit((current) => ({
              ...current,
              hub: { ...current.hub, statusError: /** @type {Error} */ (caught).message || t('Fetch failed') },
            }));
          }
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
     * Save one device's panels without touching its settings or other devices.
     *
     * @param {{ panels: PanelConfig[], toastMessage?: string, deviceName?: string }} payload
     * @returns {Promise<boolean>}
     */
    async savePanels({ panels, toastMessage, deviceName }) {
      const name = deviceName || state.devices.selected;
      const entryId = state.hub.entryId;
      if (!name || !entryId || state.devices.byName[name] === undefined) return false;
      if (state.hub.saving) {
        showToast(t('Another save is still in progress'), 'error');
        return false;
      }

      commit((current) => ({ ...current, hub: { ...current.hub, saving: true } }));
      let saved = false;
      try {
        await client.panels.saveDevice(entryId, name, panels);
        commit((current) => {
          const byName = { ...current.devices.byName };
          byName[name] = { ...byName[name], panels };
          return {
            ...current,
            devices: { ...current.devices, byName },
            hub: { ...current.hub, saving: false, error: null, fieldErrors: [] },
          };
        });
        showToast(toastMessage, 'success');
        saved = true;
      } catch (error) {
        const message = /** @type {Error} */ (error).message || t('Network error');
        const fieldErrors = /** @type {any} */ (error).errors || [];
        commit((current) => ({
          ...current,
          hub: { ...current.hub, saving: false, error: message, fieldErrors },
        }));
        showToast(message, 'error');
      }
      return saved;
    },

    /** Read the hub's update rollout into the store. */
    async loadRollout() {
      const entryId = state.hub.entryId;
      if (!entryId) return;
      try {
        const rollout = await client.updates.rollout(entryId);
        commit((current) => ({ ...current, hub: { ...current.hub, rollout } }));
      } catch (error) {
        showToast(/** @type {Error} */ (error).message || t('Fetch failed'), 'error');
      }
    },

    /**
     * Install every offered update one device at a time on the hub.
     * @returns {Promise<boolean>} whether the rollout started
     */
    async startRollout() {
      const entryId = state.hub.entryId;
      if (!entryId) return false;
      try {
        const rollout = await client.updates.startRollout(entryId);
        commit((current) => ({ ...current, hub: { ...current.hub, rollout } }));
        return true;
      } catch (error) {
        showToast(/** @type {Error} */ (error).message || t('Failed to start the update rollout'), 'error');
        return false;
      }
    },

    /**
     * Cancel one queued device of the rollout, or every queued device.
     * @param {string|null} [device]
     */
    async cancelRollout(device = null) {
      const entryId = state.hub.entryId;
      if (!entryId) return;
      try {
        const rollout = await client.updates.cancelRollout(entryId, device || undefined);
        commit((current) => ({ ...current, hub: { ...current.hub, rollout } }));
      } catch (error) {
        showToast(/** @type {Error} */ (error).message || t('Failed to cancel the update rollout'), 'error');
      }
    },

    /**
     * Start, defer or skip a device's scheduled automatic firmware install.
     * @param {string} device
     * @param {'install_now'|'defer'|'skip'} action
     * @param {number} [seconds]
     * @returns {Promise<boolean>} whether the hub accepted it
     */
    async controlUpdate(device, action, seconds) {
      const entryId = state.hub.entryId;
      if (!entryId) return false;
      try {
        await client.updates.control(entryId, device, action, seconds);
        return true;
      } catch (error) {
        showToast(/** @type {Error} */ (error).message || t('Failed to change the scheduled update'), 'error');
        return false;
      }
    },

    /** Replace the current device's settings with the server-accepted config. */
    /**
     * @param {{ deviceConfig: DeviceConfig, toastMessage?: string, deviceName?: string }} payload
     */
    async saveDeviceConfig({ deviceConfig, toastMessage, deviceName }) {
      const name = deviceName || state.devices.selected;
      const entryId = state.hub.entryId;
      if (!name || !entryId || state.devices.byName[name] === undefined) return false;
      if (state.hub.saving) {
        showToast(t('Another save is still in progress'), 'error');
        return false;
      }

      const config = mergeDeviceConfig(deviceConfig);
      commit((current) => ({ ...current, hub: { ...current.hub, saving: true } }));
      let saved = false;
      try {
        const body = await client.devices.saveSettings(entryId, name, config);
        commit((current) => {
          const byName = { ...current.devices.byName };
          byName[name] = { ...byName[name], config: mergeDeviceConfig(body.config) };
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

    /** Load fresh settings before opening the device settings editor. @param {string} name */
    async loadDeviceConfig(name) {
      const entryId = state.hub.entryId;
      if (!name || !entryId || state.devices.byName[name] === undefined) return false;
      try {
        const body = await client.devices.settings(entryId, name);
        commit((current) => {
          const byName = { ...current.devices.byName };
          byName[name] = { ...byName[name], config: mergeDeviceConfig(body.config) };
          return { ...current, devices: { ...current.devices, byName } };
        });
        return true;
      } catch (error) {
        const message = /** @type {Error} */ (error).message || t('Network error');
        commit((current) => ({ ...current, hub: { ...current.hub, error: message } }));
        showToast(message, 'error');
        return false;
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
      const message = '"' + device.friendlyName + '" ' + (enabled ? t('enabled') : t('disabled'));
      await actions.saveDeviceConfig({
        deviceConfig: { ...device.config, enabled },
        toastMessage: message,
        deviceName: name,
      });
    },

    /** @param {Route} route */
    setRoute(route) {
      /** @type {Route} */
      const normalized = route?.view === 'device' && route.device
        ? {
            view: 'device',
            device: String(route.device),
            panel: route.panel ? String(route.panel) : null,
            panelView: route.panelView === 'panels' || route.panel ? 'panels' : 'preview',
          }
        : { view: 'fleet', device: null, panel: null, panelView: 'preview' };
      commit((current) => ({ ...current, ui: { ...current.ui, route: normalized } }));
    },

    /**
     * Push an overlay onto the ordered stack, replacing a duplicate kind/anchor.
     * An anchored popover also replaces the anchored popover it would sit on.
     *
     * @param {Overlay} overlay
     */
    pushOverlay(overlay) {
      commit((current) => {
        const overlays = current.ui.overlays.filter((entry) =>
          entry.kind !== overlay.kind || entry.anchorKey !== overlay.anchorKey);
        const anchored = isAnchoredOverlayKind(overlay.kind)
          ? overlays.filter((entry) => !isAnchoredOverlayKind(entry.kind))
          : overlays;
        return { ...current, ui: { ...current.ui, overlays: [...anchored, overlay] } };
      });
    },

    /** Replace the top overlay without changing the stack depth. @param {Overlay} overlay */
    replaceTopOverlay(overlay) {
      commit((current) => ({
        ...current,
        ui: { ...current.ui, overlays: [...current.ui.overlays.slice(0, -1), overlay] },
      }));
    },

    /** Close the most recent overlay matching its kind and optional anchor. */
    closeOverlay(kind, anchorKey = null) {
      let index = -1;
      for (let i = state.ui.overlays.length - 1; i >= 0; i--) {
        const entry = state.ui.overlays[i];
        if (entry.kind === kind && (anchorKey === null || entry.anchorKey === anchorKey)) {
          index = i;
          break;
        }
      }
      if (index < 0) return;
      commit((current) => ({
        ...current,
        ui: { ...current.ui, overlays: current.ui.overlays.filter((_, i) => i !== index) },
      }));
    },

    closeTopOverlay() {
      if (!state.ui.overlays.length) return;
      commit((current) => ({ ...current, ui: { ...current.ui, overlays: current.ui.overlays.slice(0, -1) } }));
    },

    /** The preview mode the user chose: the workspace follows it. @param {'simulated'|'live'} mode */
    setPreviewMode(mode) {
      const next = mode === 'live' ? 'live' : 'simulated';
      if (state.ui.preview.mode === next) return;
      commit((current) => ({
        ...current,
        ui: { ...current.ui, preview: { ...current.ui.preview, mode: next } },
      }));
    },

    /** Whether the idle page is showing; the workspace reports the session truth. @param {boolean} idle */
    setPreviewIdle(idle) {
      if (state.ui.preview.idle === idle) return;
      commit((current) => ({
        ...current,
        ui: { ...current.ui, preview: { ...current.ui.preview, idle: Boolean(idle) } },
      }));
    },

    /** @param {boolean} showEntities */
    setPreviewEntities(showEntities) {
      commit((current) => ({
        ...current,
        ui: { ...current.ui, preview: { ...current.ui.preview, showEntities } },
      }));
    },

    /** Persist a complete drag-reordered device order optimistically. @param {string[]} requestedOrder */
    async reorderDevices(requestedOrder) {
      const entryId = state.hub.entryId;
      if (!entryId || state.hub.saving) {
        if (state.hub.saving) showToast(t('Another save is still in progress'), 'error');
        return false;
      }
      const existing = state.devices.order;
      const wanted = [...new Set(requestedOrder.filter((name) => existing.includes(name)))];
      const nextOrder = [...wanted, ...existing.filter((name) => !wanted.includes(name))];
      if (nextOrder.length !== existing.length || nextOrder.every((name, index) => name === existing[index])) return false;
      const previousOrder = [...existing];
      commit((current) => ({
        ...current,
        devices: { ...current.devices, order: nextOrder },
        hub: { ...current.hub, saving: true },
      }));
      try {
        const body = await client.devices.reorder(entryId, nextOrder);
        commit((current) => ({
          ...current,
          devices: { ...current.devices, order: body.device_order },
          hub: { ...current.hub, saving: false, error: null },
        }));
        showToast(t('Device order saved'), 'success');
        return true;
      } catch (error) {
        const message = /** @type {Error} */ (error).message || t('Network error');
        commit((current) => ({
          ...current,
          devices: { ...current.devices, order: previousOrder },
          hub: { ...current.hub, saving: false, error: message },
        }));
        showToast(message, 'error');
        return false;
      }
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
