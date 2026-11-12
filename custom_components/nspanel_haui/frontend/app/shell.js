/**
 * NSPanel HAUI - the editor shell.
 *
 * The custom element and its render code. Shared state lives in
 * `store/store.js`; the shell mirrors it into Lit properties for the existing
 * render modules and delegates every action to the store or the API client.
 */
import '../iconset.js';

import { LitElement, html, nothing } from '../lit-import.js';
import { clone, isPortraitModel } from '../constants.js';
import { fetchTranslations, t, getLanguage } from '../localize.js';
import { haStyle, haStyleDialog, editorContainerStyles, editorStyles } from '../styles.js';
import { createApiClient } from '../api/client.js';
import { createStore } from '../store/store.js';
import { StoreController } from '../store/controller.js';
import { createRouter } from './router.js';
import { renderFleetView } from '../views/fleet.js';
import { renderDeviceView } from '../views/device.js';
import { modalSidebar } from '../ui/sidebar.js';
import { railOverflows } from '../ui/device-rail.js';
import { deviceDetails } from '../ui/device-details.js';
import { diagnosticsReport } from '../ui/device-diagnostics.js';
import { eventsByTime } from '../ui/event-list.js';
import { panelActions, panelManager } from '../ui/panel-manager.js';
import { deviceActions } from '../ui/device-actions.js';
import { idlePanelConfig, idlePanelKeys, panelKeys } from '../ui/panel-pills.js';
import { renderSimulatorPreview } from '../previews/simulator-frame.js';
import { previewRenderKey } from '../previews/previewer.js';
import * as Crud from '../crud.js';
import * as DeviceConfig from '../device-config.js';
import * as Toast from '../toast.js';

// Register dialog custom elements
import '../views/panel-editor.js';
import '../dialogs/confirm.js';
import '../views/device-settings.js';
import '../dialogs/firmware.js';
import '../dialogs/logs.js';
import '../dialogs/theme.js';
import '../views/workspace.js';

import { copyText, readStorage, writeStorage } from '../dom-helpers.js';
import { anchorElement, focusAnchor, focusMenu, overlayAnchor, placeOpenPopovers, popoverSurface } from '../ui/popover.js';
import { isAnchoredOverlayKind, isSidebarOverlayKind } from '../store/store.js';
import { selectDevice, importDeviceYaml, exportDeviceYaml } from '../device-yaml.js';
import { deviceBrightness, hasUpdateAvailable } from '../device-status.js';
import { groupPanels, panelRoleMarkers } from '../panel-utils.js';
import { renderPanelList } from '../views/panel-list.js';
import { notificationsView } from '../views/notifications.js';
import { panelCatalog } from '../views/panel-catalog.js';
import { renderTitleHeader, renderFooter } from '../toolbar.js';
import { HA_ELEMENTS_TIMEOUT_MS, undefinedHaElements, whenHaElementsDefined } from '../ha-elements.js';

import * as SystemPanels from '../system-panels.js';
import * as ThemeEditor from '../theme-editor.js';
import * as DeviceEvents from '../device-events.js';

/* ── component ───────────────────────────────────────────────────────────── */

// Whether the Connection & device card lists its facts and the Diagnostics card
// shows its tiles; per-browser preferences.
const DETAILS_EXPANDED_KEY = 'haui_deviceDetailsExpanded';
const DIAGNOSTICS_EXPANDED_KEY = 'haui_diagnosticsExpanded';
// The device side-stack cards the user expanded (comma-separated card ids); the rest stay collapsed.
const PANEL_CARDS_EXPANDED_KEY = 'haui_panelCardsExpanded';

/** @type {import("../store/store.js").StoreStorage} */
const STORAGE = {
  read: (key, fallback) => readStorage(key, fallback),
  write: (key, value) => writeStorage(key, value),
};
/** Build the common input shared by the shell's hub-rendered panel previews. */
function buildPreviewContext(entryId, deviceName, device, status, api, themes) {
  return {
    entryId,
    device: deviceName,
    deviceConfig: device.config,
    panels: device.panels,
    theme: themes?.[device.config?.theme_id] || null,
    deviceInfo: status?.device_info || null,
    api,
  };
}


class NSPanelEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
      entryId: { type: String, state: true },
      _panels: { type: Object, state: true },
      _route: { type: Object, state: true },
      _loading: { type: Boolean, state: true },
      _entriesError: { type: String, state: true },
      _selectedDevice: { type: String, state: true },
      _panelTypes: { type: Array, state: true },
      _editingPanel: { type: Object, state: true },
      _editingPanelType: { type: String, state: true },
      _panelCatalogOpen: { type: Boolean, state: true },
      _panelCatalogSearch: { type: String, state: true },
      _saving: { type: Boolean, state: true },
      _error: { type: String, state: true },
      _toast: { type: Object, state: true },
      _deleteTarget: { type: Number, state: true },
      _tftInstallTarget: { type: String, state: true },
      _deviceConfig: { type: Object, state: true },
      _editingDeviceConfig: { type: Boolean, state: true },
      _deviceConfigForm: { type: Object, state: true },
      _scheduleDraft: { type: Object, state: true },
      _gestureDraft: { type: Object, state: true },
      _deviceStatus: { type: Object, state: true },
      _deviceStatuses: { type: Object, state: true },
      _deviceStatusError: { type: String, state: true },
      _notifications: { type: Array, state: true },
      _discovered: { type: Array, state: true },
      _scanning: { type: Boolean, state: true },
      _scanError: { type: String, state: true },
      _removeTarget: { type: String, state: true },
      _confirmBulkUpdate: { type: Boolean, state: true },
      _panelSearch: { type: String, state: true },
      _railCollapsed: { type: Boolean, state: true },
      _detailsExpanded: { type: Boolean, state: true },
      _diagnosticsExpanded: { type: Boolean, state: true },
      _panelCardsExpanded: { type: Array, state: true },
      _themeVariant: { type: String, state: true },

      _dialogVersion: { type: Number, state: true },
      _haElementsReady: { type: Boolean, state: true },
      _haElementsSlow: { type: Boolean, state: true },
      _haElementsForced: { type: Boolean, state: true },

    };
  }

  static styles = [haStyle, haStyleDialog, editorContainerStyles, editorStyles];

  constructor() {
    super();
    this.api = createApiClient(() => this.hass);
    this._store = createStore({ client: this.api, storage: STORAGE });
    this._router = null;
    this.__lastSelectedDevice = null;
    this.store = this._store;
    this.addController(new StoreController(this, this._store, () => this._syncFromStore()));

    this._panels = { version: 1, devices: {} };
    this._loading = true;
    this._entriesError = null;
    this._selectedDevice = null;
    this.entryId = null;
    this._panelTypes = [];
    this._editingPanel = null;
    this._editingPanelType = null;
    this._panelCatalogOpen = false;
    this._panelCatalogSearch = '';
    this._saving = false;
    this.__pendingUpdateSettings = null;
    this.__savingUpdateSettings = false;
    this._error = null;
    this._toast = null;
    this._deleteTarget = null;
    this._tftInstallTarget = null;

    this._deviceConfig = null;
    this._editingDeviceConfig = false;
    this._deviceConfigForm = null;
    this._scheduleDraft = null;
    this._gestureDraft = null;
    this._itemListData = {};
    this._dialogVersion = 0;

    this._deviceStatus = null;
    this._deviceStatuses = {};
    this._deviceStatusError = null;
    this._notifications = [];
    this._discovered = [];
    this._scanning = false;
    this._scanError = '';
    this._removeTarget = null;
    this._confirmBulkUpdate = false;
    this._panelSearch = '';
    this._railCollapsed = false;
    this._detailsExpanded = readStorage(DETAILS_EXPANDED_KEY, '1') === '1';
    this._diagnosticsExpanded = readStorage(DIAGNOSTICS_EXPANDED_KEY, '0') === '1';
    this._panelCardsExpanded = readStorage(PANEL_CARDS_EXPANDED_KEY, '').split(',').filter(Boolean);
    this._themeVariant = "dark";
    this._haElementsForced = false;
    this._syncFromStore();
    this._waitForHaElements();
  }

  /** Mirror the store into the Lit properties the render modules read. */
  _syncFromStore() {
    // The sidebars belong to the device on screen: leaving it by any route
    // (Back/Forward, a pasted link) closes them like the editor's own device
    // switch does. Each close commits and syncs again with the new state.
    const route = this._store.getState().ui.route;
    const routeDevice = route?.view === 'device' ? route.device : null;
    if (routeDevice !== this.__routeDevice) {
      const left = this.__routeDevice;
      this.__routeDevice = routeDevice;
      // Fleet's Logs sidebar belongs to Fleet: Forward into a device closes it too.
      if ((left || this._isOverlayOpen('logs')) && this._closeSidebarForRouteChange()) return;
    }
    const state = this._store.getState();
    // Status polls commit a new `byName` every 5 s; only rebuild the panel
    // store when the panel-relevant slices actually changed.
    const panelsKey = JSON.stringify([
      state.hub.themes,
      state.hub.systemPanels,
      state.devices.order,
      state.devices.order.map((name) => {
        const device = state.devices.byName[name];
        return [device.friendlyName, device.config, device.panels];
      }),
    ]);
    if (panelsKey !== this.__panelsKey) {
      this.__panelsKey = panelsKey;
      /** @type {Object<string, any>} */
      const devices = {};
      for (const name of state.devices.order) {
        const device = state.devices.byName[name];
        devices[name] = {
          friendly_name: device.friendlyName,
          config: device.config,
          panels: device.panels,
        };
      }
      this._panels = {
        version: 1,
        themes: state.hub.themes,
        system_panels: state.hub.systemPanels,
        devices,
      };
    }
    this._selectedDevice = state.devices.selected;
    if (this._scheduleDraft?.device !== state.devices.selected) this._scheduleDraft = null;
    if (this._gestureDraft?.device !== state.devices.selected) this._gestureDraft = null;
    this._deviceConfig = state.devices.selected
      ? this._store.selectors.configFor(state.devices.selected)
      : null;
    this._deviceStatus = this._store.selectors.selectedStatus();
    this._deviceStatuses = this._store.selectors.statuses();
    this._deviceStatusError = state.hub.statusError;
    this._panelTypes = state.hub.panelTypes;
    this._notifications = state.notifications;
    this._saving = state.hub.saving;
    this._toast = state.ui.toast;
    this._loading = state.hub.loading;
    this.entryId = state.hub.entryId;
    this._route = state.ui.route;
    const selectedName = state.devices.selected;
    // The first selection comes from loading the hub (its first device), not
    // from the user: a linked device wins over it.
    const selectionChanged = Boolean(this.__lastSelectedDevice) && selectedName !== this.__lastSelectedDevice;
    if (route?.view === 'device' && route.device) {
      if (state.devices.byName[route.device]) {
        if (selectedName !== route.device) {
          if (selectionChanged && selectedName) {
            this._router?.navigate({ view: 'device', device: selectedName, panelView: 'preview' }, { replace: true });
          } else {
            this._store.actions.selectDevice(route.device);
          }
        }
        const routedDevice = state.devices.byName[route.device];
        if (selectedName === route.device && routedDevice.panels.length === 0 && route.panelView !== 'panels') {
          this._router?.navigate({ view: 'device', device: route.device, panelView: 'panels' }, { replace: true });
        }
        if (selectedName === route.device && route.panel) {
          const routedPanelKey = `${route.device}:${route.panel}`;
          const index = routedDevice.panels.findIndex((panel) => panel.key === route.panel);
          const systemPanel = state.hub.systemPanels.find((panel) => panel.key === route.panel);
          if (index >= 0 && this.__openedRoutePanel !== routedPanelKey) {
            this.__openedRoutePanel = routedPanelKey;
            this._openEdit(index);
          } else if (index < 0 && systemPanel?.editable && this.__openedRoutePanel !== routedPanelKey) {
            this.__openedRoutePanel = routedPanelKey;
            this._openSysPanelEdit(systemPanel);
          } else if (index < 0 && !systemPanel) {
            // A panel that was open and is gone was renamed or removed by a save:
            // only a link to a panel that never existed is an error.
            const wasOpen = this.__openedRoutePanel === routedPanelKey;
            this.__openedRoutePanel = null;
            this._router?.navigate({ view: 'device', device: route.device, panelView: 'panels' }, { replace: true });
            if (!wasOpen) this._store.actions.showToast(t('The requested panel is unavailable'), 'error');
          } else if (index < 0 && systemPanel && !systemPanel.editable) {
            this._router?.navigate({ view: 'device', device: route.device, panelView: 'panels' }, { replace: true });
          }
        } else if (!route.panel && this.__openedRoutePanel) {
          this.__openedRoutePanel = null;
          this._closeEdit();
        }
      } else if (!state.hub.loading && state.hub.entryId) {
        this._router?.navigate({ view: 'fleet' }, { replace: true });
        this._store.actions.showToast(t('The requested device is unavailable'), 'error');
      }
    }
    this.__lastSelectedDevice = selectedName;
  }

  /* ── lifecycle ────────────────────────────────────────────────────────── */

  connectedCallback() {
    super.connectedCallback();
    this._router = createRouter(this._store);
    this.__onDocMouseDown = (e) => {
      const top = this._store.getState().ui.overlays.at(-1);
      if (!isAnchoredOverlayKind(top?.kind)) return;
      const path = e.composedPath();
      const surface = popoverSurface(this.renderRoot);
      const anchor = anchorElement(this.renderRoot, top.anchorKey);
      if (!path.includes(surface) && !path.includes(anchor)) this._closeAnchoredPopover(top.kind);
    };
    document.addEventListener('mousedown', this.__onDocMouseDown, true);
    this.__onDocKeyDown = (event) => {
      if (event.key !== 'Escape') return;
      const overlayKind = this._store.getState().ui.overlays.at(-1)?.kind;
      if (isAnchoredOverlayKind(overlayKind)) {
        event.preventDefault();
        this._closeAnchoredPopover(overlayKind, true);
        return;
      }
    };
    document.addEventListener('keydown', this.__onDocKeyDown, true);
    // Bubble phase: a control inside the sidebar form that handles Escape itself
    // (an open picker or dropdown) keeps it, instead of losing the whole editor.
    this.__onDocEscape = (event) => {
      if (event.key !== 'Escape' || event.defaultPrevented) return;
      const overlayKind = this._store.getState().ui.overlays.at(-1)?.kind;
      if (!isSidebarOverlayKind(overlayKind)) return;
      if (event.composedPath().some((node) => node?.tagName?.toLowerCase() === 'ha-dialog')) return;
      event.preventDefault();
      this._closeSidebar();
    };
    document.addEventListener('keydown', this.__onDocEscape);
    // A popover is placed once, with a fixed position: follow its trigger when
    // the window resizes (into or out of the bottom sheet) or the page scrolls.
    this.__onViewportChange = () => {
      if (isAnchoredOverlayKind(this._store.getState().ui.overlays.at(-1)?.kind)) placeOpenPopovers(this.renderRoot);
    };
    window.addEventListener('resize', this.__onViewportChange);
    window.addEventListener('scroll', this.__onViewportChange, true);
    this.renderRoot?.addEventListener?.('scroll', this.__onViewportChange, true);
    // Home Assistant keeps the editor element while another panel is shown and
    // attaches it again on return: poll the device the disconnect stopped.
    if (this._selectedDevice && !this._loading) this._store.actions.startSelectedStatusPolling();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._router?.destroy();
    this._router = null;
    this._lockPageScroll(false);
    this.__railObserver?.disconnect();
    this.__railObserver = null;
    this.__railHead = null;
    if (this.__onDocMouseDown) {
      document.removeEventListener('mousedown', this.__onDocMouseDown, true);
      this.__onDocMouseDown = null;
    }
    if (this.__onDocKeyDown) {
      document.removeEventListener('keydown', this.__onDocKeyDown, true);
      this.__onDocKeyDown = null;
    }
    if (this.__onDocEscape) {
      document.removeEventListener('keydown', this.__onDocEscape);
      this.__onDocEscape = null;
    }
    if (this.__onViewportChange) {
      window.removeEventListener('resize', this.__onViewportChange);
      window.removeEventListener('scroll', this.__onViewportChange, true);
      this.renderRoot?.removeEventListener?.('scroll', this.__onViewportChange, true);
      this.__onViewportChange = null;
    }
    this._store.actions.stopSelectedStatusPolling();
    this._store.actions.stopAllStatusPolling();
    this._store.actions.stopNotifications();
    this._clearHaElementsTimer();
  }

  updated(changed) {
    // A sidebar that opens, or shows again when the one over it closes, takes the focus.
    const sidebarKind = this._store.getState().ui.overlays.at(-1)?.kind;
    const sidebarShown = isSidebarOverlayKind(sidebarKind) && sidebarKind !== this.__shownSidebarKind;
    this.__shownSidebarKind = isSidebarOverlayKind(sidebarKind) ? sidebarKind : null;
    if (sidebarShown || (['_editingPanel', '_panelCatalogOpen', '_editingDeviceConfig'].some((key) => changed.has(key))
        && (this._editingPanel || this._panelCatalogOpen || this._editingDeviceConfig))) {
      this.updateComplete.then(() => this.renderRoot.querySelector('.haui-modal-sidebar')?.focus());
    }
    // hass is replaced on every state change, so each load runs once (per
    // language) rather than on every push while it is still pending.
    if (changed.has("hass") && this.hass) {
      this._store.actions.subscribeNotifications();
      if (!this.__entriesRequested) {
        this.__entriesRequested = true;
        this._loadEntries();
      }
      const lang = getLanguage(this.hass);
      if (lang !== this.__language) {
        this.__language = lang;
        this._loadLanguage(lang);
      }
    }
    if (changed.has("entryId") && this.entryId) {
      if (this.__notificationsFor !== this.entryId) {
        this.__notificationsFor = this.entryId;
        this._store.actions.loadNotifications();
      }
    }
    if (changed.has("_selectedDevice") && this._selectedDevice && !this._loading) {
      this._store.actions.startSelectedStatusPolling();
    }
    const top = this._store.getState().ui.overlays.at(-1);
    if (isAnchoredOverlayKind(top?.kind)) {
      this.updateComplete.then(() => {
        placeOpenPopovers(this.renderRoot);
        focusMenu(this.renderRoot);
      });
    }
    this._lockPageScroll(isSidebarOverlayKind(top?.kind));
    this._watchDeviceRail();
    // Fleet shows every device, and so do the Device screen's device chips;
    // with a single device the selected-device poller already covers it.
    const deviceCount = Object.keys(this._store.getState().devices.byName).length;
    if (this.entryId && !this._loading && (this._route?.view !== 'device' || deviceCount > 1)) {
      this._store.actions.startAllStatusPolling();
    } else {
      this._store.actions.stopAllStatusPolling();
    }
  }

  /**
   * Show the device chips as a dropdown while they do not fit beside the title.
   * Measured after every render and whenever the head changes its width.
   */
  _watchDeviceRail() {
    const head = this.renderRoot?.querySelector?.('.haui-device-head');
    if (head !== this.__railHead) {
      this.__railObserver?.disconnect();
      this.__railObserver = null;
      this.__railHead = head || null;
      if (head && typeof ResizeObserver === 'function') {
        this.__railObserver = new ResizeObserver(() => this._measureDeviceRail());
        this.__railObserver.observe(head);
      }
    }
    this._measureDeviceRail();
  }

  _measureDeviceRail() {
    const overflows = railOverflows(this.renderRoot);
    if (overflows !== null && overflows !== this._railCollapsed) this._railCollapsed = overflows;
  }

  /**
   * Keep the page behind the modal sidebar from scrolling, as a dialog does.
   * @param {boolean} locked
   */
  _lockPageScroll(locked) {
    if (locked === Boolean(this.__pageScrollLocked)) return;
    const root = globalThis.document?.documentElement;
    if (!root?.style) return;
    this.__pageScrollLocked = locked;
    if (locked) {
      this.__pageOverflow = root.style.overflow;
      root.style.overflow = 'hidden';
    } else {
      root.style.overflow = this.__pageOverflow || '';
    }
  }

  /** Hold rendering until HA has defined the elements in ha-elements.js. */
  _waitForHaElements() {
    this._haElementsReady = undefinedHaElements().length === 0;
    this._haElementsSlow = false;
    if (this._haElementsReady) return;
    this.__haElementsTimer = setTimeout(() => {
      this._haElementsSlow = true;
    }, HA_ELEMENTS_TIMEOUT_MS);
    whenHaElementsDefined().then(() => {
      this._clearHaElementsTimer();
      this._haElementsReady = true;
    });
  }

  _clearHaElementsTimer() {
    if (this.__haElementsTimer) {
      clearTimeout(this.__haElementsTimer);
      this.__haElementsTimer = null;
    }
  }

  /**
   * Escape hatch: render the editor although HA elements are still missing.
   * Without it, an HA build that never defines one of them leaves the editor
   * stuck on the loading screen with no way forward.
   */
  _forceRenderWithoutHaElements() {
    this._clearHaElementsTimer();
    this._haElementsForced = true;
    this.requestUpdate();
  }

  _reloadPage() {
    window.location?.reload?.();
  }

  /* ── data loading ─────────────────────────────────────────────────────── */

  async _loadEntries() {
    if (!this.hass) return;
    try {
      const entries = await this.api.entries.list();
      this._entriesError = null;
      if (entries.length && !this.entryId) {
        const entryId = entries[0].entry_id;
        this.__notificationsFor = entryId;
        await this._load(entryId);
        // Not awaited: Fleet shows what it finds when the scan returns.
        this._scanDevices();
      } else if (!entries.length) {
        this._store.actions.setLoading(false);
      }
    } catch (error) {
      console.error("Failed to load NSPanel HAUI integration list:", error);
      this._entriesError = error.message || t("Failed to load the integration list");
      this._store.actions.setLoading(false);
    }
  }

  async _load(entryId = this.entryId) {
    await this._store.actions.loadHub(entryId);
  }

  async _loadPanelTypes() {
    return this._store.actions.loadPanelTypes({ force: true });
  }

  async _loadDeviceConfig(name) {
    DeviceConfig.loadDeviceConfig(this, name);
  }

  /* ── CRUD actions ─────────────────────────────────────────────────────── */

  _captureSidebarFocus() {
    let active = this.renderRoot?.activeElement || document.activeElement;
    while (active?.shadowRoot?.activeElement) active = active.shadowRoot.activeElement;
    this.__sidebarReturnFocus = active;
  }

  _restoreSidebarFocus() {
    const target = this.__sidebarReturnFocus;
    this.__sidebarReturnFocus = null;
    const restore = () => {
      if (target?.isConnected) target.focus?.();
      else this.renderRoot?.querySelector('.haui-device-lead .haui-button')?.focus();
    };
    if (typeof globalThis.requestAnimationFrame === 'function') globalThis.requestAnimationFrame(restore);
    else restore();
  }

  _closeSidebar() {
    const kind = this._store.getState().ui.overlays.at(-1)?.kind;
    this._closeSidebarKind(kind);
  }

  /**
   * Close one sidebar overlay, with route-change cleanup kept distinct from a user close.
   * @param {string} kind
   * @param {{ routeChange?: boolean }} [options]
   */
  _closeSidebarKind(kind, { routeChange = false } = {}) {
    if (kind === 'device-settings') this._closeDeviceConfig();
    else if (kind === 'panel-editor') {
      if (routeChange) {
        this.__openedRoutePanel = null;
        this._closeEdit();
      } else {
        const route = this._store.getState().ui.route;
        this._closeEdit();
        if (route.panel) this._router?.navigate({ view: 'device', device: route.device, panelView: 'panels' }, { replace: true });
      }
    } else if (kind === 'panel-catalog') this._closeCatalog();
    else if (kind === 'firmware') this._closeFirmware();
    else if (kind === 'theme') this._closeThemeSidebar();
    else if (kind === 'logs') this._closeLogs();
  }

  /**
   * Close every sidebar layer: they all belong to the device being left.
   * @returns {boolean} whether any layer was open
   */
  _closeSidebarForRouteChange() {
    const kinds = this._store.getState().ui.overlays.map((overlay) => overlay.kind).filter(isSidebarOverlayKind);
    for (const kind of kinds.reverse()) this._closeSidebarKind(kind, { routeChange: true });
    return kinds.length > 0;
  }

  _isOverlayOpen(kind) {
    return this._store?.getState?.().ui?.overlays?.at(-1)?.kind === kind;
  }

  /**
   * Close an anchored popover and, optionally, return focus to its trigger.
   * @param {string} kind
   * @param {boolean} [restoreFocus]
   */
  _closeAnchoredPopover(kind, restoreFocus = false) {
    const overlay = this._store.getState().ui.overlays.find((entry) => entry.kind === kind);
    this._store.actions.closeOverlay(kind);
    if (!restoreFocus) return;
    const restore = () => focusAnchor(this.renderRoot, overlay?.anchorKey);
    if (typeof globalThis.requestAnimationFrame === 'function') globalThis.requestAnimationFrame(restore);
    else restore();
  }

  /**
   * Open or close an anchored popover; returns whether it is now open.
   * @param {string} kind
   * @param {string} anchorKey
   * @param {string|null} [subject]
   */
  _toggleAnchoredPopover(kind, anchorKey, subject = null) {
    if (this._isOverlayOpen(kind)) {
      this._closeAnchoredPopover(kind, true);
      return false;
    }
    this._store.actions.pushOverlay({ kind, anchorKey, subject, draft: null });
    return true;
  }

  _openAdd(type) {
    this._panelCatalogOpen = false;
    Crud.openAdd(this, type);
  }
  /** Open the editor for a new panel copied from an existing one. @param {any} source */
  _openAddFrom(source) {
    this._panelCatalogOpen = false;
    Crud.openAddFrom(this, source);
  }

  /** Every user panel of the hub, as something a new panel can be copied from; the catalog groups them by device. */
  _panelTemplates() {
    const state = this._store.getState();
    const systemKeys = new Set(state.hub.systemPanels.map((entry) => entry.key));
    return state.devices.order.flatMap((deviceName) => {
      const device = state.devices.byName[deviceName];
      return device.panels.filter((panel) => !systemKeys.has(panel.key)).map((panel) => {
        const type = this._panelTypes.find((entry) => entry.type_key === panel.type);
        return {
          id: `${deviceName}:${panel.key}`,
          device: deviceName,
          deviceLabel: device.friendlyName || deviceName,
          label: panel.title || type?.label || panel.key,
          detail: type?.label || panel.type,
          icon: type?.icon,
          panel,
        };
      });
    });
  }

  _openCatalog() {
    this._captureSidebarFocus();
    const route = this._store.getState().ui.route;
    if (route?.view === 'device' && route.panelView === 'preview') {
      this._router?.navigate({ view: 'device', device: route.device, panelView: 'panels' });
    }
    this._panelCatalogSearch = '';
    this._panelCatalogOpen = true;
    this._store.actions.pushOverlay({
      kind: 'panel-catalog',
      anchorKey: 'add-panel',
      subject: this._selectedDevice,
      draft: null,
    });
  }
  _closeCatalog() {
    this._panelCatalogOpen = false;
    this._store.actions.closeOverlay('panel-catalog', 'add-panel');
    this._restoreSidebarFocus();
  }
  _openEdit(i) { this._captureSidebarFocus(); Crud.openEdit(this, i); }
  _closeEdit() {
    Crud.closeEdit(this);
    this._restoreSidebarFocus();
  }
  _toggleNavVisibility(key) { Crud.toggleNavVisibility(this, key); }
  async _setSpecialPanel(field, panelKey) {
    const idleKeys = field === 'idle_panels' ? panelKeys(panelKey) : [];
    const dc = field === 'idle_panels'
      ? { ...this._deviceConfig, ...idlePanelConfig(idleKeys) }
      : { ...this._deviceConfig, [field]: panelKey };
    const role = field === 'home_panel' ? t('Home panel')
      : field === 'idle_panels' ? t('Idle panels')
        : field === 'idle_panel_extra' ? t('Extra idle panels') : t('Idle panel');
    const selectedKeys = field === 'idle_panels' || field === 'idle_panel_extra'
      ? panelKeys(panelKey) : panelKey ? [panelKey] : [];
    const panelTitles = new Map(this._devicePanels().map((panel) => [panel.key, panel.title || panel.key]));
    const titles = selectedKeys.map((key) => panelTitles.get(key) || key).join(', ');
    const message = selectedKeys.length
      ? t('{role} set to "{panel}"').replace('{role}', role).replace('{panel}', titles)
      : t('{role} cleared').replace('{role}', role);
    await this._savePanels(this._devicePanels(), message, dc);
  }
  _changeGestures(draft) {
    if (!this._selectedDevice || !this._deviceConfig || this._saving) return;
    this._gestureDraft = {
      device: this._selectedDevice,
      gestures: clone(draft.gestures),
      expandedEntryIndex: draft.expandedEntryIndex,
    };
  }
  _onGestureEntryToggle(index, isOpen) {
    if (isOpen || this._gestureDraft?.expandedEntryIndex !== index) return;
    this._gestureDraft = { ...this._gestureDraft, expandedEntryIndex: null };
  }
  async _saveGestures() {
    const draft = this._gestureDraft;
    if (!draft || draft.device !== this._selectedDevice || this._saving) return;
    const config = { ...this._deviceConfig, gestures: clone(draft.gestures) };
    if (await this._savePanels(this._devicePanels(), t('Device configuration saved'), config)) {
      this._gestureDraft = null;
    }
    this.requestUpdate();
  }
  _changeSchedule(draft) {
    if (!this._selectedDevice || !this._deviceConfig || this._saving) return;
    this._scheduleDraft = {
      device: this._selectedDevice,
      schedule: clone(draft.schedule),
      brightness: draft.brightness,
      brightness_dim: draft.brightness_dim,
      sound_on_notification: draft.sound_on_notification,
      timeout_dimming: draft.timeout_dimming,
      duration_dimming: draft.duration_dimming,
      use_auto_display_off: draft.use_auto_display_off,
      timeout_display_off: draft.timeout_display_off,
      expandedEntryIndex: draft.expandedEntryIndex,
    };
  }

  _onScheduleEntryToggle(index, isOpen) {
    if (isOpen || this._scheduleDraft?.expandedEntryIndex !== index) return;
    this._scheduleDraft = { ...this._scheduleDraft, expandedEntryIndex: null };
  }
  async _saveSchedule() {
    const draft = this._scheduleDraft;
    if (!draft || draft.device !== this._selectedDevice || this._saving) return;
    const config = {
      ...this._deviceConfig,
      schedule: clone(draft.schedule),
      brightness: draft.brightness,
      brightness_dim: draft.brightness_dim,
      sound_on_notification: draft.sound_on_notification,
      timeout_dimming: draft.timeout_dimming,
      duration_dimming: draft.duration_dimming,
      use_auto_display_off: draft.use_auto_display_off,
      timeout_display_off: draft.timeout_display_off,
    };
    if (await this._savePanels(this._devicePanels(), t('Device configuration saved'), config)) {
      this._scheduleDraft = null;
    }
    this.requestUpdate();
  }
  _confirmDelete(i)        { Crud.confirmDelete(this, i); }
  _cancelDelete()          { Crud.cancelDelete(this); }
  async _doDelete()        { return Crud.doDelete(this); }

  _openSysPanelEdit(sysPanel) { this._captureSidebarFocus(); return SystemPanels.openSysPanelEdit(this, sysPanel); }
  /** Open a built-in popup from the catalog; the editor takes the catalog's place. @param {any} sysPanel */
  _openSysPanelFromCatalog(sysPanel) {
    this._panelCatalogOpen = false;
    SystemPanels.openSysPanelEdit(this, sysPanel);
  }
  _resetSysPanelOverride(key)             { return SystemPanels.resetSysPanelOverride(this, key); }

  /* ── save ─────────────────────────────────────────────────────────────── */

  async _save(e) {
    // Receive serialized form data from nspanel-panel-editor via event detail.
    if (!e?.detail?.panel) return;
    // Sync item list data from dialog so saveFromData can read it
    if (e.detail.itemListData) {
      this._itemListData = e.detail.itemListData;
    }
    await Crud.saveFromData(this, e.detail.panel, e.detail.index);
    // A saved editor that a link opened leaves its route, so a reload does not reopen it.
    const route = this._store.getState().ui.route;
    if (!this._editingPanel && route.panel) {
      this.__openedRoutePanel = null;
      this._router?.navigate({ view: 'device', device: route.device, panelView: 'panels' }, { replace: true });
    }
  }
  async _savePanels(p, m, c) { return Crud.savePanels(this, p, m, c); }

  /* ── device actions ───────────────────────────────────────────────────── */

  _navigateToDevice(name) {
    this._closeSidebarForRouteChange();
    this._panelSearch = '';
    this._router?.navigate({ view: 'device', device: name, panelView: 'preview' });
  }

  _navigateToFleet() {
    this._closeSidebarForRouteChange();
    this._router?.navigate({ view: 'fleet' });
  }

  async _selectDevice(name) { selectDevice(this, name); }

  _openDeviceConfig() {
    this._captureSidebarFocus();
    DeviceConfig.openDeviceConfig(this);
    this.requestUpdate();
  }
  _closeDeviceConfig() {
    DeviceConfig.closeDeviceConfig(this);
    this.requestUpdate();
    this._restoreSidebarFocus();
  }

  /* ── device settings and YAML ─────────────────────────────────────── */

  /** Open the selected device's settings in the sidebar, on its Device screen. */
  _openSettings() {
    const name = this._selectedDevice;
    if (!name) return;
    // A new history entry: Back returns to Fleet, where the sidebar was opened.
    if (this._route?.view !== 'device' || this._route.device !== name) {
      this._router?.navigate({ view: 'device', device: name, panelView: 'preview' });
    }
    this._loadDeviceConfig(name);
    this._openDeviceConfig();
    this.requestUpdate();
  }

  _importYaml() { importDeviceYaml(this); }

  _exportYaml() { exportDeviceYaml(this); }

  /* ── device discovery, enabling and removal ───────────────────────── */

  /**
   * Look for HAUI devices the hub does not manage yet. Runs once the editor has
   * loaded and on request from Fleet; the result is what Fleet offers to add.
   */
  async _scanDevices() {
    if (!this.entryId || this._scanning) return;
    this._scanning = true;
    this._scanError = '';
    try {
      const result = await this.api.devices.scan(this.entryId);
      this._discovered = result.devices || [];
    } catch (error) {
      this._scanError = error.message || t('Scan failed');
    }
    this._scanning = false;
  }

  /** Devices found by the scan that are not configured (anymore). */
  _discoveredDevices() {
    const known = this._store.getState().devices.byName;
    return (this._discovered || []).filter((device) => !known[device.name || device.friendly_name]);
  }

  /** @param {Array<any>} devices */
  async _addDevices(devices) {
    await DeviceEvents.addDevices(this, devices);
  }

  /** Connected devices with an offered update the hub may install. */
  _updatableDevices() {
    const state = this._store.getState();
    return state.devices.order.filter((name) => {
      const status = state.devices.byName[name].status;
      const update = status?.update;
      return status?.connected === true && update && update.enabled !== false
        && !update.firmware_installing
        && hasUpdateAvailable(update);
    });
  }

  get _bulkUpdateParams() {
    return {
      title: t('Install all offered updates?'),
      message: t('Install the offered firmware and display updates on {count} device(s)? A display cannot be used while it updates, and a firmware update restarts the panel.')
        .replace('{count}', String(this._updatableDevices().length)),
      confirmText: t('Install'),
      cancelText: t('Cancel'),
      confirmVariant: 'brand',
    };
  }

  /**
   * Install what each device is offered. Firmware goes first: the display the
   * new firmware needs follows on its own after the panel restarts.
   */
  async _installOfferedUpdates() {
    this._confirmBulkUpdate = false;
    const state = this._store.getState();
    for (const name of this._updatableDevices()) {
      const update = state.devices.byName[name].status.update;
      if (update.firmware_update_available) {
        await DeviceEvents.installFirmware(this, { detail: { name } });
      } else {
        await DeviceEvents.installTft(this, { detail: { name } });
      }
    }
  }

  get _removeDeviceParams() {
    const name = this._removeTarget;
    if (!name) return null;
    return {
      title: t('Remove device?'),
      message: t('Remove {name} from the hub? Its settings and panels are deleted. This cannot be undone.')
        .replace('{name}', this._panels.devices?.[name]?.friendly_name || name),
      confirmText: t('Remove'),
      cancelText: t('Cancel'),
    };
  }

  async _confirmRemoveDevice() {
    const name = this._removeTarget;
    this._removeTarget = null;
    if (!name) return;
    await DeviceEvents.removeDevice(this, name);
    // A removed device is discoverable again.
    this._scanDevices();
  }


  /* ── toast ────────────────────────────────────────────────────────────── */

  _showToast(m, kind)      { this._store.actions.showToast(m, kind); }

  /* ── localization ─────────────────────────────────────────────────────── */


  /** Load the UI translations and the localized panel types for `lang`. */
  async _loadLanguage(lang) {
    // Translations first: panel types carry translated labels, and a failed
    // load is reported through t(), which is only translated once this resolves.
    await fetchTranslations(this.api, lang);
    await this._loadPanelTypes();
    // t() reads a module-level map, so Lit does not know the text changed.
    this.requestUpdate();
  }

  /* ── render ───────────────────────────────────────────────────────────── */

  _renderFleetScreen() {
    const state = this._store.getState();
    const devices = state.devices.order.map((name) => {
      const device = state.devices.byName[name];
      const status = device.status;
      const configuredKey = device.config.home_panel;
      const configuredIndex = device.panels.findIndex((panel) => panel.key === configuredKey);
      const fallbackIndex = device.panels.findIndex((panel) => panel.show_in_navigation !== false);
      const panelIndex = configuredIndex >= 0 ? configuredIndex : fallbackIndex;
      const panel = panelIndex >= 0
        ? device.panels[panelIndex]
        : state.hub.systemPanels.find((entry) => entry.key === configuredKey);
      const context = buildPreviewContext(state.hub.entryId, name, device, status, this.api, state.hub.themes);
      return {
        name,
        device,
        status,
        disabled: device.config.enabled === false,
        updates: hasUpdateAvailable(status?.update),
        preview: panel ? renderSimulatorPreview(context, panel, panelIndex < 0 ? -1 : panelIndex) : null,
      };
    });
    const events = devices.flatMap(({ name, status }) => (status?.logs || []).map((line) => ({
      deviceName: state.devices.byName[name].friendlyName,
      line,
    })));
    const versions = [...new Set(devices.map(({ status }) => status?.haui_version).filter(Boolean))];
    const hubVersion = versions.length === 1 ? versions[0] : versions.length > 1 ? t('Mixed versions') : t('Unknown');
    // Logs is Fleet's one sidebar: every device's lines, or one device's from its menu.
    const logs = state.ui.overlays.find((overlay) => overlay.kind === 'logs');
    return html`<div class="container">
      ${renderTitleHeader(this)}
      ${renderFleetView({
        devices,
        events,
        version: hubVersion,
        statusPending: devices.some(({ status }) => !status),
        carousel: this.__carousel || { atStart: true, atEnd: false },
        onCarouselScroll: (edges) => {
          const previous = this.__carousel;
          if (previous && previous.atStart === edges.atStart && previous.atEnd === edges.atEnd) return;
          this.__carousel = edges;
          this.requestUpdate();
        },
        menu: this._deviceMenuModel(),
        onMenu: (name, anchorKey) => this._toggleDeviceMenu(name, anchorKey),
        onCloseMenu: () => this._closeAnchoredPopover('device-menu'),
        onOpenDevice: (name) => this._navigateToDevice(name),
        onDeviceSettings: (name) => {
          this._selectDevice(name);
          this._openSettings();
        },
        onReorderDevices: (order) => this._store.actions.reorderDevices(order),
        discovered: this._discoveredDevices(),
        scanning: this._scanning,
        scanError: this._scanError,
        statusError: state.hub.statusError,
        installable: this._updatableDevices().length,
        onInstallUpdates: () => { this._confirmBulkUpdate = true; },
        onScan: () => this._scanDevices(),
        onAddDevices: (found) => this._addDevices(found),
        onOpenLogs: () => this._openLogs(null),
      })}
      ${this._renderNotificationsView()}
      <nspanel-dialog-confirm
        .hass=${this.hass} .open=${this._removeTarget !== null}
        .params=${this._removeDeviceParams}
        @dialog-closed=${() => { this._removeTarget = null; }}
        @dialog-confirmed=${this._confirmRemoveDevice}
      ></nspanel-dialog-confirm>
      <nspanel-dialog-confirm
        .hass=${this.hass} .open=${this._confirmBulkUpdate === true}
        .params=${this._confirmBulkUpdate ? this._bulkUpdateParams : null}
        @dialog-closed=${() => { this._confirmBulkUpdate = false; }}
        @dialog-confirmed=${this._installOfferedUpdates}
      ></nspanel-dialog-confirm>
      ${logs ? modalSidebar({
        label: logs.subject
          ? `${t('Logs')} · ${state.devices.byName[logs.subject]?.friendlyName || logs.subject}`
          : t('Logs'),
        body: this._renderLogs(logs.subject
          ? state.devices.byName[logs.subject]?.status?.logs || []
          : eventsByTime(events)),
        onClose: () => this._closeLogs(),
      }) : nothing}
      ${this._toast ? Toast.renderToast(this) : ''}
      ${renderFooter(this)}
    </div>`;
  }

  _renderDeviceScreen() {
    const state = this._store.getState();
    const route = state.ui.route;
    const name = route.device;
    const device = name ? state.devices.byName[name] : null;
    if (!name || !device) return this._renderFleetScreen();
    const status = device.status;
    const railDevices = state.devices.order.map((deviceName) => {
      const entry = state.devices.byName[deviceName];
      return {
        name: deviceName,
        device: entry,
        status: entry.status,
        updates: hasUpdateAvailable(entry.status?.update),
      };
    });
    const preview = state.ui.preview;
    const previewState = this.__previewState || {};
    const interactiveSession = html`<nspanel-preview-workspace class="haui-inline-live-preview"
      .hass=${this.hass} .active=${true} .entryId=${this.entryId} .device=${name}
      .mode=${preview.mode} .showEntities=${preview.showEntities}
      @preview-state=${(event) => this._onPreviewState(event)}
      @preview-notice=${(event) => this._showToast(event.detail.message, event.detail.type)}
    ></nspanel-preview-workspace>`;
    // Only the Panels view pays for the list: the Preview view renders on every
    // Home Assistant state change and would build every card for nothing.
    const workspace = route.panelView === 'panels'
      ? renderPanelList(this._panelListModel(device, status))
      : interactiveSession;
    // Every open sidebar stays rendered and the topmost one is shown, so a nested
    // editor keeps the draft below it.
    const sidebarKinds = state.ui.overlays.map((overlay) => overlay.kind).filter(isSidebarOverlayKind);
    const sidebarKind = sidebarKinds.at(-1);
    const panelEditor = sidebarKinds.includes('panel-editor') && this._editingPanel ? html`<nspanel-panel-editor
      .hass=${this.hass} .api=${this.api} .open=${true} .inline=${true}
      .panel=${this._editingPanel} .panelTypes=${this._panelTypes}
      .devicePanels=${this._devicePanels()} .systemPanels=${this._panels?.system_panels || []}
      .saving=${this._saving} .error=${this._error} .entryId=${this.entryId}
      .dialogVersion=${this._dialogVersion}
      .previewContext=${buildPreviewContext(this.entryId, name, device, status, this.api, state.hub.themes)}
      @dialog-closed=${() => {
        this.__openedRoutePanel = null;
        this._closeEdit();
        if (state.ui.route.panel) this._router?.navigate({ view: 'device', device: name, panelView: 'panels' }, { replace: true });
      }} @dialog-save=${this._save}
    ></nspanel-panel-editor>` : null;
    const deviceSettings = html`<nspanel-device-settings
      .hass=${this.hass} .open=${true} .inline=${true}
      .config=${this._deviceConfigForm}
      .saving=${this._saving}
      .api=${this.api} .entryId=${this.entryId}
      @dialog-closed=${this._closeDeviceConfig}
      @dialog-save=${this._onDeviceConfigSave}
    ></nspanel-device-settings>`;
    const catalog = () => panelCatalog({
      panelTypes: this._panelTypes,
      query: this._panelCatalogSearch,
      onQuery: (query) => { this._panelCatalogSearch = query; },
      onSelect: (type) => this._openAdd(type),
      templates: this._panelTemplates(),
      onSelectTemplate: (panel) => this._openAddFrom(panel),
      popups: groupPanels(device.panels, state.hub.systemPanels || []).defaults,
      onSelectPopup: (entry) => this._openSysPanelFromCatalog(entry),
      preview: (panel, byKey = false) => renderSimulatorPreview(
        buildPreviewContext(this.entryId, name, device, status, this.api, state.hub.themes), panel, byKey ? -1 : 0),
      portrait: isPortraitModel(device.config.display_model),
    });
    const firmware = () => html`<nspanel-firmware-popover
      .hass=${this.hass} .api=${this.api} .open=${true}
      .deviceStatus=${device.status} .deviceName=${name} .entryId=${this.entryId}
      .config=${device.config}
      @dialog-closed=${() => this._closeFirmware()}
      @update-check=${() => this._store.actions.pollSelectedStatus()}
      @save-update-settings=${(event) => this._saveUpdateSettings(event)}
      @update-tft=${(event) => DeviceEvents.installTft(this, event)}
      @update-firmware=${(event) => DeviceEvents.installFirmware(this, event)}
    ></nspanel-firmware-popover>`;
    const theme = () => html`<nspanel-theme-sidebar
      .hass=${this.hass} .api=${this.api} .open=${true}
      .entryId=${this.entryId} .panels=${this._devicePanels()}
      .themeId=${this._themeId || 'dark'}
      .themeVariant=${this._themeVariant}
      @dialog-closed=${this._closeThemeSidebar} @dialog-save=${this._onThemeSave}
    ></nspanel-theme-sidebar>`;
    /** @param {string} kind @param {() => unknown} content */
    const layer = (kind, content) => (sidebarKinds.includes(kind)
      ? html`<div class="haui-sidebar-layer" ?hidden=${kind !== sidebarKind}>${content()}</div>`
      : nothing);
    // The modal sidebar opens over the page; the side stack below it stays as it is.
    const sidebarContent = sidebarKind ? html`${layer('device-settings', () => deviceSettings)}${
      layer('panel-catalog', catalog)}${layer('panel-editor', () => panelEditor)}${
      layer('firmware', firmware)}${layer('theme', theme)}${
      layer('logs', () => this._renderLogs(status?.logs || []))}` : null;
    const leadContent = route.panelView === 'panels'
      ? panelActions({
          panels: device.panels,
          onAdd: () => this._openCatalog(),
          onSettings: () => this._openSettings(),
        })
      : deviceActions({
          status,
          onSettings: () => this._openSettings(),
          onFirmware: () => this._openFirmware(name),
          onAdd: () => this._openCatalog(),
          onTheme: () => this._openTheme(),
        });
    const sideContent = route.panelView === 'panels'
      ? panelManager({
          panels: device.panels,
          systemPanels: state.hub.systemPanels || [],
          config: device.config,
          saving: state.hub.saving,
          scheduleDraft: this._scheduleDraft?.device === name ? this._scheduleDraft : null,
          deviceBrightness: deviceBrightness(status, this.hass),
          onScheduleChange: (draft) => this._changeSchedule(draft),
          onScheduleEntryToggle: (index, isOpen) => this._onScheduleEntryToggle(index, isOpen),
          onScheduleSave: () => this._saveSchedule(),
          onSetRole: (field, panelKey) => this._setSpecialPanel(field, panelKey),
          gestureDraft: this._gestureDraft?.device === name ? this._gestureDraft : null,
          onGestureChange: (draft) => this._changeGestures(draft),
          onGestureEntryToggle: (index, isOpen) => this._onGestureEntryToggle(index, isOpen),
          onGestureSave: () => this._saveGestures(),
          expanded: this._panelCardsExpanded,
          onToggle: (card) => this._togglePanelCard(card),
        })
        : deviceDetails({
            name,
            status,
            hass: this.hass,
            onLogs: () => this._openLogs(name),
            onFirmware: () => this._openFirmware(name),
            onCopyReport: () => this._copyDiagnostics(name, status),
            detailsExpanded: this._detailsExpanded,
            onToggleDetails: () => this._toggleDetails(),
            diagnosticsExpanded: this._diagnosticsExpanded,
            onToggleDiagnostics: () => this._toggleDiagnostics(),
            yamlExpanded: this._panelCardsExpanded.includes('yaml'),
            onToggleYaml: () => this._togglePanelCard('yaml'),
            onYamlImport: () => this._importYaml(),
            onYamlExport: () => this._exportYaml(),
            showEntities: preview.showEntities,
            onShowEntities: (show) => this._store.actions.setPreviewEntities(show),
            // Live already shows the device's page; only the simulated preview follows a click.
            onOpenPage: (previewState.mode || preview.mode) !== 'live' && previewState.ready && status?.current_panel
              ? () => this._callPreviewWorkspace(
                'openPanel', status.current_panel, status.idle_page?.state === 'active',
              )
              : null,
            previewTools: {
              live: (previewState.mode || preview.mode) === 'live',
              ready: Boolean(previewState.ready),
              canInteract: Boolean(previewState.canInteract),
              sandboxChanged: Boolean(previewState.sandboxChanged),
              onReset: () => this._callPreviewWorkspace('resetSession'),
              onRedraw: () => this._redrawDisplay(name),
            },
          });

    return html`<div class="container">
      ${renderTitleHeader(this)}
      ${renderDeviceView({
        devices: railDevices,
        selectedName: name,
        title: device.friendlyName || name,
        onBack: () => this._navigateToFleet(),
        panelCount: device.panels.length,
        panelView: route.panelView,
        panelSearch: { query: this._panelSearch, onQuery: (value) => { this._panelSearch = value; } },
        railCollapsed: this._railCollapsed,
        workspace,
        leadContent,
        sideContent,
        sidebarContent,
        preview: {
          mode: previewState.mode || preview.mode,
          idle: Boolean(previewState.idle),
          canInteract: Boolean(previewState.canInteract),
        },
        sidebarOpen: Boolean(sidebarContent),
        sidebarLabel: sidebarKind === 'device-settings' ? t('Device settings')
          : sidebarKind === 'panel-editor' ? this._panelEditorLabel()
            : sidebarKind === 'firmware' ? t('Updates')
              : sidebarKind === 'theme' ? t('Theme')
                : sidebarKind === 'logs' ? t('Logs') : t('Add panel'),
        onCloseSide: () => this._closeSidebar(),
        onSelectDevice: (deviceName) => this._navigateToDevice(deviceName),
        onSwitchView: (panelView) => this._router?.navigate(
          { view: 'device', device: name, panelView }, { replace: true },
        ),
        onMode: (mode) => {
          this._store.actions.setPreviewMode(mode);
          // Also when the store already holds this mode: a Live session that failed
          // to start must still switch back to Simulated.
          this._callPreviewWorkspace('setLive', mode === 'live');
        },
        onIdle: () => this._onPreviewIdle(device.config, previewState),
      })}
      <nspanel-dialog-confirm
        .hass=${this.hass} .open=${this._deleteTarget !== null}
        .params=${this._deleteTarget !== null ? this._confirmDialogParams : null}
        @dialog-closed=${this._cancelDelete} @dialog-confirmed=${this._doDelete}
      ></nspanel-dialog-confirm>
      <nspanel-dialog-confirm
        .hass=${this.hass} .open=${this._tftInstallTarget !== null}
        .params=${this._tftInstallTarget !== null ? this._tftInstallParams : null}
        @dialog-closed=${this._cancelTftInstall} @dialog-confirmed=${this._confirmTftInstall}
      ></nspanel-dialog-confirm>
      ${this._renderNotificationsView()}
      ${this._toast ? Toast.renderToast(this) : ''}
      ${renderFooter(this)}
    </div>`;
  }

  /** The sidebar strip's title for the panel editor: a new panel, or an existing one. */
  _panelEditorLabel() {
    const editing = this._editingPanel;
    const system = (this._panels?.system_panels || []).some((entry) => entry.key === editing?.data?.key);
    // A system panel's first edit has no index yet, but it is not a new panel.
    return editing && editing.index < 0 && !system ? t('Add Panel') : t('Edit Panel');
  }

  /** The Fleet device menu: the actions the overview can reach without a route change. */
  _deviceMenuModel() {
    const top = this._store.getState().ui.overlays.at(-1);
    if (top?.kind !== 'device-menu') return null;
    const name = top.subject;
    const enabled = this._store.getState().devices.byName[name]?.config.enabled !== false;
    const at = (action) => () => {
      this._selectDevice(name);
      action();
    };
    return {
      key: name,
      anchorKey: top.anchorKey,
      label: t('Actions for {name}').replace('{name}', this._panels.devices?.[name]?.friendly_name || name),
      items: [
        { label: t('View'), iconName: 'mdi:monitor', onSelect: at(() => this._navigateToDevice(name)) },
        { label: t('Panels'), iconName: 'mdi:view-dashboard-outline', onSelect: at(() => this._router?.navigate({ view: 'device', device: name, panelView: 'panels' })) },
        'divider',
        { label: t('Logs'), iconName: 'mdi:text-box-outline', onSelect: at(() => this._openLogs(name)) },
        'divider',
        {
          label: enabled ? t('Disable') : t('Enable'),
          iconName: enabled ? 'mdi:close-circle-outline' : 'mdi:check-circle-outline',
          onSelect: () => DeviceEvents.toggleDevice(this, name),
        },
        { label: t('Remove'), iconName: 'mdi:delete-outline', danger: true, onSelect: () => { this._removeTarget = name; } },
      ],
    };
  }

  /** @param {string} name @param {string} anchorKey */
  _toggleDeviceMenu(name, anchorKey) {
    this._toggleAnchoredPopover('device-menu', anchorKey, name);
  }

  /** Keep the Device header in step with the preview session it cannot see. */
  _onPreviewState(event) {
    const detail = event.detail || {};
    const previous = this.__previewState;
    this.__previewState = detail;
    this._store.actions.setPreviewIdle(Boolean(detail.idle));
    if (detail.mode && detail.mode !== this._store.getState().ui.preview.mode) {
      this._store.actions.setPreviewMode(detail.mode);
    }
    if (!previous || previous.idle !== detail.idle || previous.ready !== detail.ready
        || previous.canInteract !== detail.canInteract || previous.mode !== detail.mode
        || previous.sandboxChanged !== detail.sandboxChanged) {
      this.requestUpdate();
    }
  }

  /** Ask the hub to redraw the device display. @param {string} name */
  async _redrawDisplay(name) {
    if (!name || !this.entryId) return;
    try {
      await this.api.devices.refreshDisplay(this.entryId, name);
      this._showToast(t('Display refreshed for "{name}"').replace('{name}', name), 'success');
    } catch (error) {
      this._showToast(error.message || t('Failed to refresh display'), 'error');
    }
  }

  /** Collapse or expand the Connection & device card; remembered per browser. */
  _toggleDetails() {
    this._detailsExpanded = !this._detailsExpanded;
    writeStorage(DETAILS_EXPANDED_KEY, this._detailsExpanded ? '1' : '0');
  }

  /** Switch the Diagnostics card between its simple and expanded state; remembered per browser. */
  _toggleDiagnostics() {
    this._diagnosticsExpanded = !this._diagnosticsExpanded;
    writeStorage(DIAGNOSTICS_EXPANDED_KEY, this._diagnosticsExpanded ? '1' : '0');
  }

  /** Collapse or expand a device side-stack card; remembered per browser. @param {string} card */
  _togglePanelCard(card) {
    const expanded = this._panelCardsExpanded;
    this._panelCardsExpanded = expanded.includes(card)
      ? expanded.filter((entry) => entry !== card) : [...expanded, card];
    writeStorage(PANEL_CARDS_EXPANDED_KEY, this._panelCardsExpanded.join(','));
  }

  /** Copy a plain-text diagnostics report for a bug report. @param {string} name @param {any} status */
  async _copyDiagnostics(name, status) {
    try {
      await copyText(diagnosticsReport(name, status));
      this._showToast(t('Diagnostics report copied'), 'success');
    } catch (error) {
      this._showToast(error.message || t('Failed to copy the report'), 'error');
    }
  }

  /**
   * Toggle idle in the preview, explaining when the device has no idle panels.
   * @param {any} config
   * @param {{ idle?: boolean }} previewState
   */
  _onPreviewIdle(config, previewState) {
    if (!previewState?.idle && !idlePanelKeys(config?.idle_panel, config?.idle_panel_extra).length) {
      this._showToast(t('No idle panels are configured'), 'error');
      return;
    }
    this._callPreviewWorkspace('idleTimeout');
  }

  /** Call a preview-workspace action of the header or the Diagnostics card. @param {string} method @param {...any} args */
  _callPreviewWorkspace(method, ...args) {
    const element = this.renderRoot?.querySelector('nspanel-preview-workspace');
    const action = element?.[method];
    if (typeof action !== 'function') return;
    action.apply(element, args);
  }

  _devicePanels() {
    return this._panels.devices?.[this._selectedDevice]?.panels || [];
  }

  /**
   * Prepare the Device workspace's panel groups for `views/panel-list.js`.
   *
   * Every entry carries its hub-rendered preview, role markers, move state and
   * menu closures, so the view only renders and reports back through the model's
   * callbacks.
   *
   * @param {any} device - the routed device state (`{ name, panels, config }`)
   * @param {any} status - that device's status payload
   */
  _panelListModel(device, status) {
    const state = this._store.getState();
    const panels = device?.panels || [];
    const config = device?.config || {};
    const systemPanels = state.hub.systemPanels || [];
    const grouped = groupPanels(panels, systemPanels);
    const portrait = isPortraitModel(config.display_model);
    const systemKeys = new Set(systemPanels.map((entry) => entry.key).filter(Boolean));
    // The hub opens the first navigation panel as home while none is configured
    // (or the configured one is gone), so that panel carries the Home marker.
    const homeKnown = panels.some((panel) => panel.key === config.home_panel) || systemKeys.has(config.home_panel);
    const roleConfig = { ...config, home_panel: homeKnown ? config.home_panel : grouped.navigation[0]?.key };
    const context = {
      entryId: this.entryId,
      device: device?.name ?? this._selectedDevice,
      deviceConfig: config,
      panels,
      deviceInfo: status?.device_info || null,
      api: this.api,
    };
    // Every card shares this context: serialise it once, not once per card.
    const renderKey = previewRenderKey(context);
    const descriptorFor = (panel) => this._panelTypes.find((type) => type.type_key === panel.type);
    const nameOf = (panel) => panel.title || descriptorFor(panel)?.label || panel.key || t('Unnamed panel');
    const nextRole = (field, panel) => (config[field] === panel.key ? '' : panel.key);

    /**
     * @param {Array} list
     * @param {boolean} isNavigation
     */
    const userEntries = (list, isNavigation) => list.map((panel) => {
      const index = panels.indexOf(panel);
      const descriptor = descriptorFor(panel);
      return {
        key: panel.key,
        kind: 'user',
        sortable: true,
        title: nameOf(panel),
        typeLabel: descriptor?.label || panel.type || '',
        itemCount: Array.isArray(panel.items) ? panel.items.length : 0,
        preview: renderSimulatorPreview(context, panel, index, renderKey),
        roles: panelRoleMarkers(panel.key, roleConfig),
        onEdit: () => this._openEdit(index),
        menu: [
          { label: t('Edit'), iconName: 'mdi:pencil-outline', onSelect: () => this._openEdit(index) },
          { label: t('Duplicate'), iconName: 'mdi:content-copy', onSelect: () => Crud.duplicatePanel(this, panel.key) },
          'divider',
          {
            label: isNavigation ? t('Hide from navigation') : t('Show in navigation'),
            iconName: isNavigation ? 'mdi:eye-off-outline' : 'mdi:eye-outline',
            onSelect: () => this._toggleNavVisibility(panel.key),
          },
          {
            label: config.home_panel === panel.key ? t('Unset home panel') : t('Set as home panel'),
            iconName: 'mdi:home-outline',
            onSelect: () => this._setSpecialPanel('home_panel', nextRole('home_panel', panel)),
          },
          {
            label: config.idle_panel === panel.key ? t('Unset idle panel') : t('Set as idle panel'),
            iconName: 'mdi:weather-night',
            onSelect: () => this._setSpecialPanel('idle_panel', nextRole('idle_panel', panel)),
          },
          'divider',
          { label: t('Delete'), iconName: 'mdi:delete-outline', danger: true, onSelect: () => this._confirmDelete(index) },
        ],
      };
    });

    /** @param {Array} list - the popups this device extends */
    const popupEntries = (list) => list.map((entry) => ({
      key: entry.key,
      kind: 'popup',
      title: entry.label || entry.key,
      typeLabel: t('Popup'),
      preview: renderSimulatorPreview(context, entry, -1, renderKey),
      roles: panelRoleMarkers(entry.key, roleConfig),
      onEdit: () => this._openSysPanelEdit(entry),
      menu: [
        { label: t('Edit'), iconName: 'mdi:pencil-outline', onSelect: () => this._openSysPanelEdit(entry) },
        'divider',
        { label: t('Reset to default'), iconName: 'mdi:restore', onSelect: () => this._resetSysPanelOverride(entry.key) },
      ],
    }));

    const count = (list) => String(list.length);
    // A search narrows every group to the rows that match; while it is active
    // the list is not a place to reorder, and groups without a match are left out.
    const query = (this._panelSearch || '').trim().toLocaleLowerCase();
    const matches = (entry) => `${entry.title} ${entry.key} ${entry.typeLabel || ''}`.toLocaleLowerCase().includes(query);
    const narrowed = (groups) => (query
      ? groups.map((group) => ({ ...group, dropEnabled: false, entries: group.entries.filter(matches) }))
        .filter((group) => group.entries.length)
      : groups);
    return {
      emptyMessage: query ? t('No panels match this search.') : '',
      groups: narrowed([
        {
          id: 'navigation',
          title: t('Navigation ({count} panels)').replace('{count}', count(grouped.navigation)),
          hint: t('Drag to reorder or move between groups'),
          emptyMessage: t('Drop a panel here to show it in navigation.'),
          dropEnabled: true,
          entries: userEntries(grouped.navigation, true),
        },
        {
          id: 'hidden',
          title: t('Hidden ({count} panels)').replace('{count}', count(grouped.hidden)),
          hint: t('Reached from other panels, not the header'),
          emptyMessage: t('Drop a panel here to hide it from navigation.'),
          dropEnabled: true,
          entries: userEntries(grouped.hidden, false),
        },
        {
          id: 'popups',
          title: t('Popups ({count} panels)').replace('{count}', count(grouped.popups)),
          hint: t('Popups this device extends'),
          emptyMessage: t('Every popup is the built-in one. Extend one from Add panel.'),
          dropEnabled: false,
          entries: popupEntries(grouped.popups),
        },
      ]),
      portrait,
      menuKey: state.ui.overlays.at(-1)?.kind === 'panel-menu' ? state.ui.overlays.at(-1)?.subject : null,
      onToggleMenu: (key) => this._togglePanelMenu(key),
      onCloseMenu: () => this._closePanelMenu(),
      onDrop: (move) => Crud.movePanelToGroup(this, move.sourceKey, move.group, move.beforeKey),
    };
  }

  /** @param {string} key */
  _togglePanelMenu(key) {
    const top = this._store.getState().ui.overlays.at(-1);
    if (top?.kind === 'panel-menu' && top.subject === key) {
      this._closePanelMenu();
      return;
    }
    this._store.actions.pushOverlay({
      kind: 'panel-menu',
      anchorKey: overlayAnchor('panel-menu', key),
      subject: key,
      draft: null,
    });
  }

  /** @param {boolean} [restoreFocus] */
  _closePanelMenu(restoreFocus = true) {
    this._closeAnchoredPopover('panel-menu', restoreFocus);
  }

  _renderLoading(message) {
    return html`<div class="container">
      ${renderTitleHeader(this)}
      <div class="main-content">
      <div class="loading">
        <div>${message}</div>
        ${this._haElementsSlow ? html`
          <div style="margin-top:16px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap;">
            <button
              style="padding:8px 16px; border-radius:8px; border:1px solid var(--divider-color,#ddd); background:transparent; color:inherit; font:inherit; cursor:pointer;"
              @click=${() => this._forceRenderWithoutHaElements()}
            >${t('Continue anyway')}</button>
            <button
              style="padding:8px 16px; border-radius:8px; border:none; background:var(--primary-color,#03a9f4); color:var(--text-primary-color,#fff); font:inherit; cursor:pointer;"
              @click=${() => this._reloadPage()}
            >${t('Reload page')}</button>
          </div>
        ` : ''}
      </div>
      </div>
      ${renderFooter(this)}
    </div>`;
  }

  render() {
    if (!this._haElementsReady && !this._haElementsForced) {
      return this._renderLoading(this._haElementsSlow
        ? t('Waiting for Home Assistant to load {elements}. If this does not go away, this Home Assistant version may not be supported.')
          .replace('{elements}', undefinedHaElements().join(', '))
        : t('Loading panels...'));
    }

    if (this._entriesError) {
      return html`<div class="container">
        ${renderTitleHeader(this)}
        <div class="main-content">
        <ha-card outlined class="content-card">
          <div class="card-content"><p>${this._entriesError}</p></div>
        </ha-card>
        </div>
        ${renderFooter(this)}
      </div>`;
    }

    if (!this.entryId) {
      return html`<div class="container">
        ${renderTitleHeader(this)}
        <div class="main-content">
        <ha-card outlined class="content-card">
          <div class="card-content"><p>${t("No NSPanel HAUI integration configured. Add one via Settings → Devices and Services.")}</p></div>
        </ha-card>
        </div>
        ${renderFooter(this)}
      </div>`;
    }

    if (this._loading) return this._renderLoading(t('Loading panels...'));

    if (this._route?.view === 'fleet') return this._renderFleetScreen();

    if (this._route?.view === 'device') return this._renderDeviceScreen();

    return this._renderFleetScreen();
  }

  /* ── confirm dialog helper ─────────────────────────────────────────────── */

  get _confirmDialogParams() {
    const idx = this._deleteTarget;
    if (idx === null || idx === undefined) return null;
    const panel = this._devicePanels()[idx];
    const name = panel ? panel.title || t("Panel #{index}").replace("{index}", idx) : t("this panel");
    return {
      title: t("Delete panel?"),
      message: t("Delete {name}? This cannot be undone.").replace("{name}", name),
      confirmText: t("Delete"),
      cancelText: t("Cancel"),
    };
  }

  /* ── TFT install confirmation ───────────────────────────────────────────── */

  get _tftInstallParams() {
    return {
      title: t("Install display TFT?"),
      message: t("The display model changed. Install the matching TFT now? The display cannot be used while the TFT updates."),
      confirmText: t("Install TFT"),
      cancelText: t("Not now"),
      confirmVariant: "brand",
    };
  }

  async _confirmTftInstall() {
    const name = this._tftInstallTarget;
    this._tftInstallTarget = null;
    if (!name) return;
    await DeviceEvents.installTft(this, { detail: { name } });
  }

  _cancelTftInstall() {
    this._tftInstallTarget = null;
    this.requestUpdate();
  }

  /* ── device config save handler ──────────────────────────────────────────── */
  /* Receives form state from nspanel-device-settings and saves directly.      */

  async _onDeviceConfigSave(e) {
    const cfg = e.detail?.config;
    if (!cfg || !this._selectedDevice) return;
    const previousModel = this._deviceConfig?.display_model;

    // savePanels shows the success or error toast; keep the dialog open on failure.
    if (await this._savePanels(this._devicePanels(), t("Device configuration saved"), clone(cfg))) {
      this._closeDeviceConfig();
      // The display cannot report which layout it runs, so a model change
      // needs the matching TFT.  The upload restarts the display, so ask
      // first instead of installing on save.
      if (cfg.display_model !== previousModel && cfg.update?.enabled !== false) {
        this._tftInstallTarget = this._selectedDevice;
      }
    }
    this.requestUpdate();
  }

  /* ── updates sidebar ──────────────────────────────────────────────── */

  /** Open the Updates sidebar on the device's screen. @param {string} deviceName */
  _openFirmware(deviceName) {
    this._captureSidebarFocus();
    this._store.actions.pushOverlay({ kind: 'firmware', anchorKey: 'firmware', subject: deviceName, draft: null });
  }

  async _saveUpdateSettings(event) {
    const update = event.detail?.update;
    const deviceName = this._selectedDevice;
    if (!update || !deviceName) return;
    this.__pendingUpdateSettings = { deviceName, update: clone(update) };
    if (this.__savingUpdateSettings) return;

    this.__savingUpdateSettings = true;
    try {
      while (this.__pendingUpdateSettings) {
        const pending = this.__pendingUpdateSettings;
        this.__pendingUpdateSettings = null;
        while (this._store.getState().hub.saving) {
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
        const config = this._store.selectors.configFor(pending.deviceName);
        if (!config) continue;
        await Crud.savePanels(
          this,
          this._store.selectors.devicePanels(pending.deviceName),
          '',
          { ...config, update: pending.update },
          pending.deviceName,
        );
      }
    } finally {
      this.__savingUpdateSettings = false;
    }
  }

  _closeFirmware() {
    this._store.actions.closeOverlay('firmware', 'firmware');
    this._restoreSidebarFocus();
  }

  /* ── logs sidebar ─────────────────────────────────────────────────── */

  /**
   * Open the Logs sidebar on the screen shown: one device's lines, or every
   * device's (`null`, Fleet's Latest events).
   * @param {string|null} deviceName
   */
  _openLogs(deviceName) {
    this._captureSidebarFocus();
    this._store.actions.pushOverlay({ kind: 'logs', anchorKey: 'logs', subject: deviceName, draft: null });
  }

  _closeLogs() {
    this._store.actions.closeOverlay('logs', 'logs');
    this._restoreSidebarFocus();
  }

  /** @param {Array<string|{ line: string, deviceName?: string }>} logs - oldest first */
  _renderLogs(logs) {
    return html`<nspanel-logs-sidebar .open=${true} .logs=${logs}
      @copy-logs=${(event) => this._copyLogs(event.detail.text)}></nspanel-logs-sidebar>`;
  }

  /** @param {string} text */
  async _copyLogs(text) {
    try {
      await copyText(text);
      this._showToast(t('Logs copied'), 'success');
    } catch (error) {
      this._showToast(error.message || t('Failed to copy the logs'), 'error');
    }
  }

  _renderNotificationsView() {
    return notificationsView({
      open: this._isOverlayOpen('notification-centre'),
      notifications: this._notifications || [],
      onDismiss: (notification) => this._onNotificationDismiss({ detail: { notification } }),
      onClose: () => this._closeNotifications(true),
    });
  }

  _closeNotifications(restoreFocus = false) {
    this._closeAnchoredPopover('notification-centre', restoreFocus);
  }

  _openNotifications() {
    if (this._toggleAnchoredPopover('notification-centre', overlayAnchor('notification-centre'))) {
      this._store.actions.loadNotifications();
      const focus = () => this.renderRoot?.querySelector('#haui-notification-centre')?.focus();
      if (typeof globalThis.requestAnimationFrame === 'function') globalThis.requestAnimationFrame(focus);
      else focus();
    }
  }

  _onNotificationDismiss(event) {
    const notification = event.detail?.notification;
    if (notification) {
      this._store.actions.dismissNotification(notification.device, notification.id);
    }
  }

  _openTheme() {
    const name = this._selectedDevice;
    if (!name) return;
    // A new history entry: Back returns to Fleet, where the sidebar was opened.
    if (this._route?.view !== 'device' || this._route.device !== name) {
      this._router?.navigate({ view: 'device', device: name, panelView: 'preview' });
    }
    return ThemeEditor.openThemeSidebar(this);
  }
  _closeThemeSidebar()                   { return ThemeEditor.closeThemeSidebar(this); }
  async _onThemeSave(e)                 { return ThemeEditor.saveTheme(this, e.detail); }
}

customElements.define("nspanel-haui-editor", NSPanelEditor);
export { NSPanelEditor };
