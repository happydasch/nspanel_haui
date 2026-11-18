/**
 * NSPanel HAUI - the editor shell.
 *
 * The custom element: one API client and one store, the hash route, the
 * status pollers' scope, overlay and focus handling, and the editor's loading
 * and error states. Shared state lives in `store/store.js`; the shell mirrors
 * it into the Lit properties the render modules read and keeps one-line
 * wrappers around its collaborators (the screen compositions in
 * `fleet-screen.js` and `device-screen.js`, the panel models, the device
 * sidebars and the editor's bootstrap data).
 */
import '../iconset.js';

import { LitElement, html } from '../lit-import.js';
import { t, getLanguage } from '../localize.js';
import { haStyle, haStyleDialog, editorContainerStyles, editorStyles } from '../styles.js';
import { createApiClient } from '../api/client.js';
import { createStore } from '../store/store.js';
import { StoreController } from '../store/controller.js';
import { createRouter } from './router.js';
import { carouselEdgesFrom, carouselSlots, centerCard } from '../views/fleet.js';
import { railOverflows } from '../ui/device-rail.js';
import * as Crud from '../crud.js';
import * as DeviceConfig from '../device-config.js';
import * as EditorData from '../editor-data.js';
import * as EditorPreferences from '../editor-preferences.js';
import * as FleetScreen from '../fleet-screen.js';
import * as DeviceScreen from '../device-screen.js';
import * as DeviceSidebars from '../device-sidebars.js';
import * as PanelModels from '../panel-models.js';

// Register dialog custom elements
import '../views/panel-editor.js';
import '../dialogs/confirm.js';
import '../views/device-settings.js';
import '../dialogs/backup.js';
import '../dialogs/updates.js';
import '../dialogs/logs.js';
import '../dialogs/theme.js';
import '../views/workspace.js';

import { anchorElement, focusAnchor, focusMenu, overlayAnchor, placeOpenPopovers, popoverSurface } from '../ui/popover.js';
import { isAnchoredOverlayKind, isSidebarOverlayKind } from '../store/store.js';
import { selectDevice, importDeviceYaml, exportDeviceYaml } from '../device-yaml.js';
import { notificationsView } from '../views/notifications.js';
import { renderTitleHeader, renderFooter } from '../toolbar.js';
import { HA_ELEMENTS_TIMEOUT_MS, undefinedHaElements, whenHaElementsDefined } from '../ha-elements.js';

import * as SystemPanels from '../system-panels.js';
import * as ThemeEditor from '../theme-editor.js';
import { readStorage, writeStorage } from '../dom-helpers.js';

/* ── component ───────────────────────────────────────────────────────────── */

/** @type {import("../store/store.js").StoreStorage} */
const STORAGE = {
  read: (key, fallback) => readStorage(key, fallback),
  write: (key, value) => writeStorage(key, value),
};


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
      _panelCatalogCompact: { type: Boolean, state: true },
      _saving: { type: Boolean, state: true },
      _error: { type: String, state: true },
      _toast: { type: Object, state: true },
      _deleteTarget: { type: Number, state: true },
      _tftInstallTarget: { type: String, state: true },
      _deviceConfig: { type: Object, state: true },
      _editingDeviceConfig: { type: Boolean, state: true },
      _deviceConfigForm: { type: Object, state: true },
      _deviceSettingsSection: { type: String, state: true },
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
      _selectedPanelKey: { type: String, state: true },
      _panelSubmenuKey: { type: String, state: true },
      _fleetSelection: { type: String, state: true },
      _fleetEventsSince: { type: Number, state: true },
      _panelPreviewCollapsed: { type: Boolean, state: true },
      _collapsedPanelGroups: { type: Array, state: true },
      _railCollapsed: { type: Boolean, state: true },
      _detailsExpanded: { type: Boolean, state: true },
      _diagnosticsExpanded: { type: Boolean, state: true },
      _builtinThemes: { type: Object, state: true },
      _customThemes: { type: Object, state: true },
      _themesLoading: { type: Boolean, state: true },
      _themesError: { type: String, state: true },

      _dialogVersion: { type: Number, state: true },
      _haElementsReady: { type: Boolean, state: true },
      _haElementsSlow: { type: Boolean, state: true },
      _haElementsForced: { type: Boolean, state: true },

    };
  }

  static styles = [haStyle, haStyleDialog, editorContainerStyles, editorStyles];

  constructor() {
    super();
    const preferences = EditorPreferences.readEditorPreferences();
    this.api = createApiClient(() => this.hass);
    this._store = createStore({ client: this.api, storage: STORAGE });
    this._router = null;
    this.__lastSelectedDevice = null;
    this.__selectedPanelFor = null;
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
    this._panelCatalogCompact = preferences.catalogCompact;
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
    /** The open device settings group, or null for the tile grid. */
    this._deviceSettingsSection = null;
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
    this._selectedPanelKey = null;
    this._panelSubmenuKey = null;
    this._fleetSelection = null;
    // The moment Fleet's latest events were reset to, or null for the default 24 hours;
    // remembered per browser so a reload keeps the shortened timeline.
    this._fleetEventsSince = EditorPreferences.readFleetEventsSince();
    this._panelPreviewCollapsed = preferences.panelPreviewCollapsed;
    this._collapsedPanelGroups = [];
    this._railCollapsed = false;
    this._detailsExpanded = preferences.detailsExpanded;
    this._diagnosticsExpanded = preferences.diagnosticsExpanded;
    // Earlier versions let several side cards stay expanded; only one is now open at a time, so a
    // saved Diagnostics choice wins over Connection.
    if (this._diagnosticsExpanded) {
      this._detailsExpanded = false;
    }
    this._builtinThemes = {};
    this._customThemes = {};
    this._themesLoading = false;
    this._themesError = '';
    this.__themeLibraryEntry = null;
    this.__themeLibraryLoadingEntry = null;
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
    // The selected panel row belongs to the list of the device it came from,
    // and to the list only while its panel is still there.
    if (this.__selectedPanelFor !== state.devices.selected) {
      this.__selectedPanelFor = state.devices.selected;
      this._selectedPanelKey = null;
    } else if (this._selectedPanelKey
      && !(state.devices.byName[state.devices.selected]?.panels || []).some(
        (panel) => panel.key === this._selectedPanelKey,
      )) {
      this._selectedPanelKey = null;
    }
    if (this._fleetSelection && !state.devices.byName[this._fleetSelection]) this._fleetSelection = null;
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
    // the window resizes or the page scrolls.
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
    // The device screen names the selected theme on its Themes row and in the
    // settings' theme field, so the library loads with either view.
    if (this._route?.view === 'device' && this.entryId) {
      this._loadThemeLibrary();
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
    this._watchCarousel();
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
   * Keep the carousel's edges (its arrows and fades) current when its width or its cards
   * change, not only when it scrolls: a row that fits has nothing to scroll to.
   */
  _watchCarousel() {
    const carousel = this.renderRoot?.querySelector?.('.haui-fleet-carousel');
    if (carousel !== this.__carouselElement) {
      this.__carouselObserver?.disconnect();
      this.__carouselObserver = null;
      this.__carouselElement = carousel || null;
      if (carousel && typeof ResizeObserver === 'function') {
        this.__carouselObserver = new ResizeObserver(() => this._watchCarousel());
        this.__carouselObserver.observe(carousel);
      }
      // Fleet keeps its selection across a visit to the selected device's screen, and a
      // fresh row starts at its first card: show the selection in the middle again.
      const index = this._store.getState().devices.order.indexOf(this._fleetSelection);
      if (carousel && index >= 0) centerCard(carousel, index, 'auto');
    }
    if (!carousel) return;
    this._setCarouselEdges(carouselEdgesFrom(carousel));
    this._setCarouselSlots(carouselSlots(carousel));
  }

  _setCarouselEdges(edges) {
    const previous = this.__carousel;
    if (previous && previous.atStart === edges.atStart && previous.atEnd === edges.atEnd) return;
    this.__carousel = edges;
    this.requestUpdate();
  }

  /** The room after the last card and the placeholders that fill it. */
  _setCarouselSlots(slots) {
    const previous = this.__carouselSlots;
    if (previous && previous.room === slots.room && previous.count === slots.count
      && previous.width === slots.width && previous.height === slots.height
      && previous.left === slots.left && previous.top === slots.top) return;
    this.__carouselSlots = slots;
    this.requestUpdate();
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
    return EditorData.loadEntries(this);
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

  async _loadThemeLibrary(entryId = this.entryId, force = false) {
    return EditorData.loadThemeLibrary(this, entryId, force);
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
    else if (kind === 'backups') this._closeBackups();
    else if (kind === 'updates') this._closeUpdates();
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
    if (kind === 'panel-menu') this._panelSubmenuKey = null;
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
  /** The catalog's preview size is a per-browser preference: the next open keeps it. */
  _chooseCatalogPreviewSize(compact) {
    this._panelCatalogCompact = compact;
    EditorPreferences.writeCatalogCompact(compact);
  }
  _openEdit(i) { this._captureSidebarFocus(); Crud.openEdit(this, i); }
  _closeEdit() {
    Crud.closeEdit(this);
    this._restoreSidebarFocus();
  }
  _toggleNavVisibility(key) { Crud.toggleNavVisibility(this, key); }

  /**
   * Put the device on screen before a sidebar opens over it: a new history
   * entry, so Back returns to Fleet, where the sidebar was opened.
   * @param {string} name
   */
  _ensureDeviceRoute(name) {
    if (this._route?.view !== 'device' || this._route.device !== name) {
      this._router?.navigate({ view: 'device', device: name, panelView: 'preview' });
    }
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
  async _savePanels(p, m) { return Crud.savePanels(this, p, m); }
  async _saveDeviceConfig(c, m, n) { return Crud.saveDeviceConfig(this, c, m, n); }

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
    // The General group's theme choice lists the hub's themes.
    this._loadThemeLibrary();
    return DeviceConfig.openDeviceConfig(this);
  }
  _closeDeviceConfig() {
    DeviceConfig.closeDeviceConfig(this);
    this._deviceSettingsSection = null;
    this.requestUpdate();
    this._restoreSidebarFocus();
  }

  /* ── device settings and YAML ─────────────────────────────────────── */

  /**
   * Open the selected device's settings in the sidebar, on its Device screen.
   * Opened from another sidebar (the Panels view's Schedule and Gestures
   * buttons), they go on top of it on that group; closing them returns there.
   * @param {string[]} [sections] - the group to open, e.g. ['screen']
   */
  _openSettings(sections = []) {
    const name = this._selectedDevice;
    if (!name) return;
    this._ensureDeviceRoute(name);
    this._deviceSettingsSection = sections[0] ?? null;
    this._loadDeviceConfig(name);
    this._openDeviceConfig();
    this.requestUpdate();
  }

  /**
   * Show one group of the open device settings, or their tile grid for null.
   * @param {string|null} section
   */
  _openDeviceSettingsSection(section) {
    const previous = this._deviceSettingsSection;
    if (previous === section) return;
    this._deviceSettingsSection = section;
    this.requestUpdate();
    // The strip's back control leads a group; the tile that opened it leads the grid.
    const focus = () => {
      const settings = this.renderRoot?.querySelector('nspanel-device-settings');
      const target = section
        ? this.renderRoot?.querySelector('.haui-sidebar-back')
        : settings?.renderRoot?.querySelector(`[data-settings-tile="${previous}"]`);
      target?.focus?.();
    };
    if (typeof globalThis.requestAnimationFrame === 'function') globalThis.requestAnimationFrame(focus);
    else focus();
  }

  _importYaml() { importDeviceYaml(this); }

  _exportYaml() { exportDeviceYaml(this); }

  /* ── device discovery, enabling and removal ───────────────────────── */

  async _scanDevices() {
    return FleetScreen.scanDevices(this);
  }

  _discoveredDevices() {
    return FleetScreen.discoveredDevices(this);
  }

  /** @param {Array<any>} devices */
  async _addDevices(devices) {
    await FleetScreen.addDevices(this, devices);
  }

  _updatableDevices() {
    return FleetScreen.updatableDevices(this);
  }

  get _bulkUpdateParams() {
    return FleetScreen.bulkUpdateParams(this);
  }

  async _installOfferedUpdates() {
    return FleetScreen.installOfferedUpdates(this);
  }

  get _removeDeviceParams() {
    return FleetScreen.removeDeviceParams(this);
  }

  async _confirmRemoveDevice() {
    return FleetScreen.confirmRemoveDevice(this);
  }


  /* ── haui-toast ────────────────────────────────────────────────────────────── */

  _showToast(m, kind)      { this._store.actions.showToast(m, kind); }

  /* ── localization ─────────────────────────────────────────────────────── */

  /** Load the UI translations and the localized panel types for `lang`. */
  async _loadLanguage(lang) {
    return EditorData.loadLanguage(this, lang);
  }

  /* ── render ───────────────────────────────────────────────────────────── */

  _renderFleetScreen() {
    return FleetScreen.renderFleetScreen(this);
  }

  _renderDeviceScreen() {
    return DeviceScreen.renderDeviceScreen(this);
  }

  _panelEditorLabel() {
    return DeviceScreen.panelEditorLabel(this);
  }

  /** @param {string|undefined} kind */
  _sidebarLabel(kind) {
    return DeviceScreen.sidebarLabel(this, kind);
  }

  _deviceMenuModel() {
    return FleetScreen.deviceMenuModel(this);
  }

  /** @param {string} name @param {string} anchorKey */
  _toggleDeviceMenu(name, anchorKey) {
    return FleetScreen.toggleDeviceMenu(this, name, anchorKey);
  }

  /** Keep the Device header in step with the preview session it cannot see. @param {any} event */
  _onPreviewState(event) {
    return DeviceScreen.onPreviewState(this, event);
  }

  /** Ask the hub to redraw the device display. @param {string} name */
  async _redrawDisplay(name) {
    return DeviceScreen.redrawDisplay(this, name);
  }

  _toggleDetails() {
    return DeviceScreen.toggleDetails(this);
  }

  _toggleDiagnostics() {
    return DeviceScreen.toggleDiagnostics(this);
  }

  /** @param {string} name @param {any} status */
  async _copyDiagnostics(name, status) {
    return DeviceScreen.copyDiagnostics(this, name, status);
  }

  /** @param {any} config @param {{ idle?: boolean }} previewState */
  _onPreviewIdle(config, previewState) {
    return DeviceScreen.onPreviewIdle(this, config, previewState);
  }

  /** @param {string} method @param {...any} args */
  _callPreviewWorkspace(method, ...args) {
    return DeviceScreen.callPreviewWorkspace(this, method, ...args);
  }

  _devicePanels() {
    return PanelModels.devicePanels(this);
  }

  /** @param {string} groupId */
  _togglePanelGroup(groupId) {
    return PanelModels.togglePanelGroup(this, groupId);
  }

  /** @param {any} device @param {any} status */
  _panelListModel(device, status) {
    return PanelModels.panelListModel(this, device, status);
  }

  /** @param {any} device @param {any} status */
  _panelSideModel(device, status) {
    return PanelModels.panelSideModel(this, device, status);
  }

  /** @param {string} key */
  _togglePanelSelection(key) {
    return PanelModels.togglePanelSelection(this, key);
  }

  _togglePanelPreview() {
    return PanelModels.togglePanelPreview(this);
  }

  /** @param {string} key */
  _togglePanelMenu(key) {
    return PanelModels.togglePanelMenu(this, key);
  }

  /** @param {string} key */
  _togglePanelSubmenu(key) {
    return PanelModels.togglePanelSubmenu(this, key);
  }

  /** @param {boolean} [restoreFocus] */
  _closePanelMenu(restoreFocus = true) {
    return PanelModels.closePanelMenu(this, restoreFocus);
  }

  /** @param {string} message */
  _renderLoading(message) {
    return DeviceScreen.renderLoading(this, message);
  }

  render() {
    if (!this._haElementsReady && !this._haElementsForced) {
      return this._renderLoading(this._haElementsSlow
        ? t('Waiting for Home Assistant to load {elements}. If this does not go away, this Home Assistant version may not be supported.')
          .replace('{elements}', undefinedHaElements().join(', '))
        : t('Loading panels...'));
    }

    if (this._entriesError) {
      return html`<div class="haui-container">
        ${renderTitleHeader(this)}
        <div class="haui-main-content">
        <ha-card outlined class="haui-content-card">
          <div class="haui-card-content"><p>${this._entriesError}</p></div>
        </ha-card>
        </div>
        ${renderFooter(this)}
      </div>`;
    }

    if (!this.entryId) {
      return html`<div class="haui-container">
        ${renderTitleHeader(this)}
        <div class="haui-main-content">
        <ha-card outlined class="haui-content-card">
          <div class="haui-card-content"><p>${t("No NSPanel HAUI integration configured. Add one via Settings → Devices and Services.")}</p></div>
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
    return DeviceConfig.tftInstallParams();
  }

  async _confirmTftInstall() {
    return DeviceConfig.confirmTftInstall(this);
  }

  _cancelTftInstall() {
    return DeviceConfig.cancelTftInstall(this);
  }

  /* ── device config save handler ──────────────────────────────────────────── */
  /* Receives form state from nspanel-device-settings and saves directly.      */

  /** @param {any} event */
  async _onDeviceConfigSave(event) {
    return DeviceConfig.onDeviceConfigSave(this, event);
  }

  /* ── backups sidebar ──────────────────────────────────────────────── */

  _renderBackups() {
    return DeviceSidebars.renderBackups(this);
  }

  /** @param {string} deviceName */
  _openBackups(deviceName) {
    return DeviceSidebars.openBackups(this, deviceName);
  }

  _closeBackups() {
    return DeviceSidebars.closeBackups(this);
  }

  /* ── updates sidebar ──────────────────────────────────────────────── */

  /** @param {string} name */
  _renderUpdates(name) {
    return DeviceSidebars.renderUpdates(this, name);
  }

  /** @param {Promise<unknown>} request */
  async _installThenRefresh(request) {
    return DeviceSidebars.installThenRefresh(this, request);
  }

  /** @param {string} deviceName */
  _openUpdates(deviceName) {
    return DeviceSidebars.openUpdates(this, deviceName);
  }

  /** @param {string} name @param {{ action: 'install_now'|'defer'|'skip', seconds?: number }} detail */
  async _controlUpdate(name, detail) {
    return DeviceSidebars.controlUpdate(this, name, detail);
  }

  /** @param {any} event */
  async _saveUpdateSettings(event) {
    return DeviceSidebars.saveUpdateSettings(this, event);
  }

  _closeUpdates() {
    return DeviceSidebars.closeUpdates(this);
  }

  /* ── latest events ────────────────────────────────────────────────── */

  /**
   * Start Fleet's latest-events window at `since` (ms), or restore the default
   * 24 hours with null. Kept in localStorage so a reload keeps the reset.
   *
   * @param {number|null} since
   */
  _setFleetEventsSince(since) {
    this._fleetEventsSince = since;
    EditorPreferences.writeFleetEventsSince(since);
  }

  /* ── logs sidebar ─────────────────────────────────────────────────── */

  /** @param {string|null} deviceName */
  _openLogs(deviceName) {
    return DeviceSidebars.openLogs(this, deviceName);
  }

  _closeLogs() {
    return DeviceSidebars.closeLogs(this);
  }

  /** @param {string} deviceName */
  _selectLogsDevice(deviceName) {
    return DeviceSidebars.selectLogsDevice(this, deviceName);
  }

  _renderLogs() {
    return DeviceSidebars.renderLogs(this);
  }

  /** @param {string} text */
  async _copyLogs(text) {
    return DeviceSidebars.copyLogs(this, text);
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

  _openTheme(themeId = null) {
    const name = this._selectedDevice;
    if (!name) return;
    this._ensureDeviceRoute(name);
    return ThemeEditor.openThemeSidebar(this, themeId);
  }
  _closeThemeSidebar()                   { return ThemeEditor.closeThemeSidebar(this); }
  async _onThemeSave(e) {
    await ThemeEditor.saveTheme(this, e.detail);
    await this._loadThemeLibrary(this.entryId, true);
  }
}

customElements.define("nspanel-haui-editor", NSPanelEditor);
export { NSPanelEditor };
