/**
 * NSPanel HAUI - Lit-based custom element.
 *
 * Simplified single-hub editor.  Panel management is delegated to CRUD helpers
 * and rendering is composed from focused modules: device-manager, panel-table,
 * and device-info.
 *
 * Reads and writes panel configuration via:
 *   GET/POST /api/nspanel_haui/panels/{entry_id}
 *   GET       /api/nspanel_haui/panel_types
 */
import './iconset.js';

import { LitElement, html } from './lit-import.js';
import { clone } from './constants.js';
import { fetchTranslations, t, getLanguage } from './localize.js';
import { haStyle, haStyleDialog, editorContainerStyles, editorStyles } from './styles.js';
import * as Api from './api.js';
import * as Crud from './crud.js';
import * as DeviceConfig from './device-config.js';
import * as Toast from './toast.js';

// Register dialog custom elements
import './dialogs/edit.js';
import './dialogs/confirm.js';
import './dialogs/device-config.js';
import './dialogs/device-info.js';
import './dialogs/logs.js';
import './dialogs/notifications.js';
import './dialogs/device-manager.js';
import './dialogs/colors.js';

import { positionContextMenu, readStorage } from './dom-helpers.js';
import { selectDevice } from './device-manager.js';
import { renderPanelTable, renderSystemPanels, renderEmptyCard } from './panel-table.js';
import { renderPanelGrid } from './panel-grid.js';
import { renderTitleHeader, renderDeviceInfoStrip, renderPanelToolbar, renderToolbarActions, renderFooter } from './toolbar.js';
import { startStatusPolling, stopStatusPolling } from './device-info.js';
import { HA_ELEMENTS_TIMEOUT_MS, undefinedHaElements, whenHaElementsDefined } from './ha-elements.js';

import * as SystemPanels from './system-panels.js';
import * as ColorsEditor from './colors-editor.js';
import * as DeviceEvents from './device-events.js';
import * as Notifications from './notifications.js';

/* ── component ───────────────────────────────────────────────────────────── */

// A shared empty list, so the closed logs dialog does not see a new array on
// every editor render and re-render with it.
const NO_LOGS = [];

class NSPanelEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
      entryId: { type: String, state: true },
      _panels: { type: Object, state: true },
      _loading: { type: Boolean, state: true },
      _entriesError: { type: String, state: true },
      _selectedDevice: { type: String, state: true },
      _panelTypes: { type: Array, state: true },
      _editingPanel: { type: Object, state: true },
      _editingPanelType: { type: String, state: true },
      _saving: { type: Boolean, state: true },
      _error: { type: String, state: true },
      _toast: { type: Object, state: true },
      _deleteTarget: { type: Number, state: true },
      _deviceConfig: { type: Object, state: true },
      _editingDeviceConfig: { type: Boolean, state: true },
      _deviceConfigForm: { type: Object, state: true },
      _deviceStatus: { type: Object, state: true },
      _deviceStatusError: { type: String, state: true },
      _showDeviceInfo: { type: Boolean, state: true },
      _showLogs: { type: Boolean, state: true },
      _showNotifications: { type: Boolean, state: true },
      _notifications: { type: Array, state: true },
      _showDeviceManager: { type: Boolean, state: true },
      _showColorsDialog: { type: Boolean, state: true },
      _colorsDialog: { type: Object, state: true },

      _actionsMenuIndex: { type: Number, state: true },
      _viewMode: { type: String, state: true },
      _cardMenuKey: { type: String, state: true },
      _dialogVersion: { type: Number, state: true },
      _haElementsReady: { type: Boolean, state: true },
      _haElementsSlow: { type: Boolean, state: true },
      _haElementsForced: { type: Boolean, state: true },

    };
  }

  static styles = [haStyle, haStyleDialog, editorContainerStyles, editorStyles];

  constructor() {
    super();
    this._panels = { version: 1, devices: {} };
    this._loading = true;
    this._entriesError = null;
    this._selectedDevice = null;
    this.entryId = null;
    this._panelTypes = [];
    this._editingPanel = null;
    this._editingPanelType = null;
    this._saving = false;
    this._error = null;
    this._toast = null;
    this._deleteTarget = null;

    this._deviceConfig = null;
    this._editingDeviceConfig = false;
    this._deviceConfigForm = null;
    this._itemListData = {};
    this._actionsMenuIndex = null;
    this._viewMode = readStorage('haui_viewMode', 'grid');
    this._cardMenuKey = null;
    this._dialogVersion = 0;
    this.__systemPanelsOpen = readStorage('haui_systemPanelsOpen', '') === 'true';
    this.__navPanelsOpen = readStorage('haui_navPanelsOpen', '') !== 'false';
    this.__hiddenPanelsOpen = readStorage('haui_hiddenPanelsOpen', '') !== 'false';

    this._deviceStatus = null;
    this._deviceStatusError = null;
    this._showDeviceInfo = false;
    this._showLogs = false;
    this._showNotifications = false;
    this._notifications = [];
    this._showDeviceManager = false;
    this._statusTimer = null;
    this._showColorsDialog = false;
    this._colorsDialog = {};
    this._panelSaveTimer = null;
    this._haElementsForced = false;
    this._waitForHaElements();
  }

  /* ── lifecycle ────────────────────────────────────────────────────────── */

  connectedCallback() {
    super.connectedCallback();
    this.__onDocMouseDown = (e) => {
      const path = e.composedPath();
      if (this._actionsMenuIndex !== null && this._actionsMenuIndex !== undefined) {
        const wraps = this.renderRoot.querySelectorAll('.pl-more');
        let inside = false;
        wraps.forEach((w) => { if (path.includes(w)) inside = true; });
        if (!inside) {
          this._actionsMenuIndex = null;
          this.requestUpdate();
        }
      }
      if (this._cardMenuKey) {
        const wraps = this.renderRoot.querySelectorAll('.pg-card-dropdown-wrap');
        let inside = false;
        wraps.forEach((w) => { if (path.includes(w)) inside = true; });
        if (!inside) {
          this._cardMenuKey = null;
          this.requestUpdate();
        }
      }
    };
    document.addEventListener('mousedown', this.__onDocMouseDown, true);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.__onDocMouseDown) {
      document.removeEventListener('mousedown', this.__onDocMouseDown, true);
      this.__onDocMouseDown = null;
    }
    stopStatusPolling(this);
    Notifications.stopNotificationSubscription(this);
    this._clearHaElementsTimer();
    if (this._panelSaveTimer) {
      clearTimeout(this._panelSaveTimer);
      this._panelSaveTimer = null;
    }
  }

  updated(changed) {
    // hass is replaced on every state change, so each load runs once (per
    // language) rather than on every push while it is still pending.
    if (changed.has("hass") && this.hass) {
      Notifications.subscribeNotifications(this);
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
      Notifications.loadNotifications(this);
    }
    if (changed.has("_selectedDevice") && this._selectedDevice) {
      startStatusPolling(this);
    }
    if ((changed.has("_actionsMenuIndex") && this._actionsMenuIndex !== null && this._actionsMenuIndex !== undefined) ||
        (changed.has("_cardMenuKey") && this._cardMenuKey)) {
      this.updateComplete.then(() => {
        // Reposition panel table context menu
        const plDropdown = this.renderRoot.querySelector(".pl-more ha-icon-button.active ~ .pl-dropdown, .pl-dropdown");
        if (plDropdown) {
          const activeBtn = this.renderRoot.querySelector(".pl-more ha-icon-button.active");
          if (activeBtn) positionContextMenu(plDropdown, activeBtn);
        }
        // Reposition grid card context menu
        const cardDropdown = this.renderRoot.querySelector(".pg-card-dropdown-wrap .pl-dropdown");
        if (cardDropdown) {
          const cardMore = this.renderRoot.querySelector(".pg-card-more.active");
          if (cardMore) positionContextMenu(cardDropdown, cardMore);
        }
      });
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

  async _loadEntries()     { return Api.loadEntries(this); }
  async _load() {
    await Api.loadPanels(this);
  }
  async _loadPanelTypes()  { return Api.loadPanelTypes(this); }
  _loadDeviceConfig(name)  { DeviceConfig.loadDeviceConfig(this, name); }

  /* ── CRUD actions ─────────────────────────────────────────────────────── */

  _openAdd()               { Crud.openAdd(this); }
  _openEdit(i)             { Crud.openEdit(this, i); }
  _closeEdit() {
    Crud.closeEdit(this);
  }
  _moveUp(key)             { Crud.moveUp(this, key); }
  _moveDown(key)           { Crud.moveDown(this, key); }
  _toggleNavVisibility(key) { Crud.toggleNavVisibility(this, key); }
  async _setSpecialPanel(field, panelKey) {
    const dc = { ...this._deviceConfig, [field]: panelKey };
    await this._savePanels(
      this._devicePanels(),
      t('Set {field} to "{panel}"').replace('{field}', field).replace('{panel}', panelKey),
      dc,
    );
  }
  _confirmDelete(i)        { Crud.confirmDelete(this, i); }
  _cancelDelete()          { Crud.cancelDelete(this); }
  async _doDelete()        { return Crud.doDelete(this); }

  _openSysPanelEdit(sysPanel)             { return SystemPanels.openSysPanelEdit(this, sysPanel); }
  _resetSysPanelOverride(key)             { return SystemPanels.resetSysPanelOverride(this, key); }

  /* ── save ─────────────────────────────────────────────────────────────── */

  async _save(e) {
    // Receive serialized form data from nspanel-dialog-edit-panel via event detail.
    if (!e?.detail?.panel) return;
    // Sync item list data from dialog so saveFromData can read it
    if (e.detail.itemListData) {
      this._itemListData = e.detail.itemListData;
    }
    return Crud.saveFromData(this, e.detail.panel, e.detail.index);
  }
  async _savePanels(p, m, c) { return Crud.savePanels(this, p, m, c); }

  /* ── device actions (called from templates, delegate to device-manager) ─ */

  async _selectDevice(name) { selectDevice(this, name); startStatusPolling(this); }

  _openDeviceConfig()      { DeviceConfig.openDeviceConfig(this); this.requestUpdate(); }
  _closeDeviceConfig()     { DeviceConfig.closeDeviceConfig(this); this.requestUpdate(); }

  /* ── device manager ────────────────────────────────────────────────── */

  _openDeviceManager() {
    this._showDeviceManager = true;
    this.requestUpdate();
  }

  _closeDeviceManager() {
    this._showDeviceManager = false;
    this.requestUpdate();
  }

  /* ── header menu ───────────────────────────────────────────────── */

  _toggleHeaderMenu() {
    this._actionsMenuIndex = this._actionsMenuIndex === '__header__' ? null : '__header__';
    this.requestUpdate();
  }

  _onHeaderSettings() {
    this._actionsMenuIndex = null;
    if (!this._selectedDevice) return;
    this._loadDeviceConfig(this._selectedDevice);
    this._openDeviceConfig();
    this.requestUpdate();
  }

  _onHeaderImportYaml() {
    this._actionsMenuIndex = null;
    DeviceEvents.onDeviceManagerImportYaml(this);
  }

  _onHeaderExportYaml() {
    this._actionsMenuIndex = null;
    DeviceEvents.onDeviceManagerExportYaml(this);
  }


  /* ── toast ────────────────────────────────────────────────────────────── */

  _showToast(m, t)         { Toast.showToast(this, m, t); }

  /* ── localization ─────────────────────────────────────────────────────── */


  /** Load the UI translations and the localized panel types for `lang`. */
  async _loadLanguage(lang) {
    // Translations first: panel types carry translated labels, and a failed
    // load is reported through t(), which is only translated once this resolves.
    await fetchTranslations(this.hass, lang);
    this._loadPanelTypes();
    // t() reads a module-level map, so Lit does not know the text changed.
    this.requestUpdate();
  }

  /* ── render ───────────────────────────────────────────────────────────── */

  _devicePanels() {
    if (!this._selectedDevice || !this._panels?.devices?.[this._selectedDevice]) return [];
    return this._panels.devices[this._selectedDevice].panels || [];
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
          ${renderEmptyCard(this._entriesError)}
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
          ${renderEmptyCard(t("No NSPanel HAUI integration configured. Add one via Settings \u2192 Devices and Services."))}
        </ha-card>
        </div>
        ${renderFooter(this)}
      </div>`;
    }

    if (this._loading) return this._renderLoading(t('Loading panels...'));

    return html`
      <div class="container">
        ${renderTitleHeader(this)}

        <div class="main-content">

        <ha-card outlined class="content-card">
          <div class="card-content">
            ${renderPanelToolbar(this)}
            ${this._selectedDevice ? html`
              <div class="card-toolbar-device-info">
                ${renderDeviceInfoStrip(this)}
              </div>` : ''}
          </div>
        </ha-card>

        ${renderToolbarActions(this)}

        ${this._viewMode === 'grid'
          ? html`<div class="content-card">
              ${renderPanelGrid(this)}
              ${renderSystemPanels(this, this._viewMode)}
            </div>`
          : html`<div class="content-card">
              ${renderPanelTable(this)}
              ${renderSystemPanels(this, this._viewMode)}
            </div>`}

        </div>

        <nspanel-dialog-edit-panel
          .hass=${this.hass}
          .open=${!!this._editingPanel}
          .panel=${this._editingPanel}
          .panelTypes=${this._panelTypes}
          .devicePanels=${this._devicePanels()}
          .systemPanels=${this._panels?.system_panels || []}
          .saving=${this._saving}
          .error=${this._error}
          .entryId=${this.entryId}
          .dialogVersion=${this._dialogVersion}
          @dialog-closed=${this._closeEdit}
          @dialog-save=${this._save}
        ></nspanel-dialog-edit-panel>

        <nspanel-dialog-device-config
          .hass=${this.hass}
          .open=${!!this._editingDeviceConfig}
          .config=${this._deviceConfigForm}
          .devicePanels=${this._devicePanels()}
          .saving=${this._saving}
          @dialog-closed=${this._closeDeviceConfig}
          @dialog-save=${this._onDeviceConfigSave}
        ></nspanel-dialog-device-config>

        <nspanel-dialog-confirm
          .hass=${this.hass}
          .open=${this._deleteTarget !== null}
          .params=${this._deleteTarget !== null ? this._confirmDialogParams : null}
          @dialog-closed=${this._cancelDelete}
          @dialog-confirmed=${this._doDelete}
        ></nspanel-dialog-confirm>

        <nspanel-dialog-device-info
          .hass=${this.hass}
          .open=${this._showDeviceInfo}
          .deviceStatus=${this._deviceStatus}
          @dialog-closed=${() => { this._showDeviceInfo = false; this.requestUpdate(); }}
        ></nspanel-dialog-device-info>

        <nspanel-dialog-notifications
          .hass=${this.hass}
          .open=${this._showNotifications}
          .notifications=${this._notifications}
          @dialog-closed=${() => { this._showNotifications = false; this.requestUpdate(); }}
          @notification-dismiss=${this._onNotificationDismiss}
        ></nspanel-dialog-notifications>

        <nspanel-dialog-logs
          .hass=${this.hass}
          .open=${this._showLogs}
          .logs=${this._deviceStatus?.logs || NO_LOGS}
          @dialog-closed=${() => { this._showLogs = false; this.requestUpdate(); }}
        ></nspanel-dialog-logs>
        <nspanel-dialog-device-manager
          .hass=${this.hass}
          .open=${this._showDeviceManager}
          .devices=${this._panels.devices || {}}
          .selectedDevice=${this._selectedDevice}
          .entryId=${this.entryId}
          @dialog-closed=${this._closeDeviceManager}
          @select-device=${(e) => DeviceEvents.onDeviceManagerSelect(this, e)}
          @device-settings=${(e) => DeviceEvents.onDeviceManagerSettings(this, e)}
          @remove-device=${(e) => DeviceEvents.onDeviceManagerRemove(this, e)}
          @add-device=${(e) => DeviceEvents.onDeviceManagerAdd(this, e)}
          @move-device=${(e) => DeviceEvents.onDeviceManagerMoveDevice(this, e)}
          @toggle-device=${(e) => DeviceEvents.onDeviceManagerToggleDevice(this, e)}
          @scan-devices=${(e) => DeviceEvents.onDeviceManagerScan(this, e)}
          @update-display=${(e) => DeviceEvents.onDeviceManagerUpdateDisplay(this, e)}
          @update-tft=${(e) => DeviceEvents.onDeviceManagerUpdateTft(this, e)}
          @update-firmware=${(e) => DeviceEvents.onDeviceManagerUpdateFirmware(this, e)}
          @check-for-update=${(e) => DeviceEvents.onDeviceManagerCheckUpdate(this, e)}
        ></nspanel-dialog-device-manager>

        <nspanel-dialog-colors
          .hass=${this.hass}
          .open=${this._showColorsDialog}
          .overrides=${this._colorsDialog}
          @dialog-closed=${this._closeColorsDialog}
          @dialog-save=${this._onColorsSave}
        ></nspanel-dialog-colors>
        ${this._toast ? Toast.renderToast(this) : ""}
        ${renderFooter(this)}
      </div>
    `;
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

  /* ── device config save handler ──────────────────────────────────────────── */
  /* Receives form state from nspanel-dialog-device-config and saves directly.      */

  async _onDeviceConfigSave(e) {
    const cfg = e.detail?.config;
    if (!cfg || !this._selectedDevice) return;

    // savePanels shows the success or error toast; keep the dialog open on failure.
    if (await this._savePanels(this._devicePanels(), t("Device configuration saved"), clone(cfg))) {
      this._editingDeviceConfig = false;
      this._deviceConfigForm = null;
    }
    this.requestUpdate();
  }

  /* ── colors dialog ────────────────────────────────────────────────── */

  _openNotifications() {
    this._showNotifications = true;
    Notifications.loadNotifications(this);
  }

  _onNotificationDismiss(event) {
    const notification = event.detail?.notification;
    if (notification) Notifications.dismissNotification(this, notification);
  }

  _onHeaderColors()                      { return ColorsEditor.openColorsDialog(this); }
  _closeColorsDialog()                   { return ColorsEditor.closeColorsDialog(this); }
  async _onColorsSave(e)                 { return ColorsEditor.saveColors(this, e.detail?.overrides); }
}

customElements.define("nspanel-haui-editor", NSPanelEditor);
export { NSPanelEditor };
