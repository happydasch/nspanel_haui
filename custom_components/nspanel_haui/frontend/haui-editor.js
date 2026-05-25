/**
 * NSPanel HAUI - Editor - Lit-based custom element.
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
import { clone, DEVICE_CONFIG_DEFAULTS, POPUP_TO_USER_TYPE } from './constants.js';
import { haStyle, haStyleDialog, editorStyles } from './styles.js';
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
import './dialogs/device-manager.js';
import './dialogs/colors.js';

import { renderOptionField } from './form-fields.js';
import { encodeItemValue } from './haui-item.js';
import { ENTITY_OVERRIDE_FIELDS } from './haui-entity.js';
import { formVal } from './dom-helpers.js';
import { selectDevice } from './device-manager.js';
import { renderPanelTable, renderSystemPanels, renderEmptyCard } from './panel-table.js';
import { renderPanelGrid } from './panel-grid.js';
import { renderTitleHeader, renderDeviceInfoStrip, renderPanelToolbar, renderToolbarActions } from './toolbar.js';
import { startStatusPolling, stopStatusPolling } from './device-info.js';

/* ── component ───────────────────────────────────────────────────────────── */

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
      _showDeviceManager: { type: Boolean, state: true },
      _showColorsDialog: { type: Boolean, state: true },
      _colorsDialog: { type: Object, state: true },
      _editingItem: { type: Object, state: true },
      _editingItemType: { type: String, state: true },

      _actionsMenuIndex: { type: Number, state: true },
      _viewMode: { type: String, state: true },
      _cardMenuKey: { type: String, state: true },
      _dialogVersion: { type: Number, state: true },

    };
  }

  static _readStorage(key, fallback) {
    try {
      const v = localStorage.getItem(key);
      return v === null ? fallback : v;
    } catch (_e) {
      return fallback;
    }
  }

  static _writeStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_e) {
      // ignore — Safari private mode / sandboxed iframe
    }
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this._panels = { version: 1, devices: {} };
    this._loading = true;
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
    this._editingItem = null;
    this._itemListData = {};
    this._editingItemType = null;
    this._actionsMenuIndex = null;
    this._viewMode = NSPanelEditor._readStorage('haui_viewMode', 'grid');
    this._cardMenuKey = null;
    this._dialogVersion = 0;
    this.__systemPanelsOpen = NSPanelEditor._readStorage('haui_systemPanelsOpen', '') === 'true';
    this.__navPanelsOpen = NSPanelEditor._readStorage('haui_navPanelsOpen', '') !== 'false';
    this.__hiddenPanelsOpen = NSPanelEditor._readStorage('haui_hiddenPanelsOpen', '') !== 'false';

    this._deviceStatus = null;
    this._deviceStatusError = null;
    this._showDeviceInfo = false;
    this._showLogs = false;
    this._showDeviceManager = false;
    this._statusTimer = null;
    this._showColorsDialog = false;
    this._colorsDialog = {};
    this._panelSaveTimer = null;
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
    if (this._panelSaveTimer) {
      clearTimeout(this._panelSaveTimer);
      this._panelSaveTimer = null;
    }
  }

  updated(changed) {
    if (changed.has("hass") && this.hass) {
      if (this._loading && !this.entryId) this._loadEntries();
      if (this._panelTypes.length === 0) this._loadPanelTypes();
    }
    if (changed.has("_selectedDevice") && this._selectedDevice) {
      startStatusPolling(this);
    }
  }

  /* ── data loading ─────────────────────────────────────────────────────── */

  async _loadEntries()     { return Api.loadEntries(this); }
  async _load() {
    await Api.loadPanels(this);
    if (!this._autoDiscovered && this.entryId) {
      this._autoDiscovered = true;
      await this._autoDiscoverAndAdd();
    }
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
    this._deviceConfig = dc;
    if (!this._panels.devices[this._selectedDevice]) {
      this._panels.devices[this._selectedDevice] = {};
    }
    this._panels.devices[this._selectedDevice].config = clone(dc);
    await this._savePanels(this._devicePanels(), `Set ${field} to "${panelKey}"`);
  }
  _confirmDelete(i)        { Crud.confirmDelete(this, i); }
  _cancelDelete()          { Crud.cancelDelete(this); }
  async _doDelete()        { return Crud.doDelete(this); }

  _openSysPanelEdit(sysPanel) {
    this._dialogVersion++;
    const panels = this._devicePanels();
    const existingIdx = panels.findIndex(p => p.key === sysPanel.key);
    const resolvedType = POPUP_TO_USER_TYPE[sysPanel.type] || sysPanel.type;

    if (existingIdx >= 0) {
      // Already overridden — resolve the stored panel's type to the user
      // type so the editor's descriptor lookup works.
      const existingData = clone(panels[existingIdx]);
      existingData.type = resolvedType;
      this._itemListData = {};
      this._editingPanel = { index: existingIdx, data: existingData };
      this._editingPanelType = resolvedType;
      this._error = null;
      this._deleteTarget = null;
      this.requestUpdate();
      return;
    }

    // Create new override panel from system panel defaults.
    // Leave title empty — the display will fall back to the system panel's
    // label at runtime. Only user-set titles should persist.
    const data = {
      type: resolvedType,
      key: sysPanel.key,
      show_in_navigation: false,
    };
    this._itemListData = {};
    this._editingPanelType = resolvedType;
    this._editingPanel = { index: -1, data };
    this._error = null;
    this._deleteTarget = null;
    this.requestUpdate();
  }

  async _resetSysPanelOverride(key) {
    const panels = this._devicePanels();
    const newPanels = panels.filter(p => p.key !== key);
    await this._savePanels(newPanels, 'Reset system panel "' + key + '" to defaults');
  }

  /* ── save ─────────────────────────────────────────────────────────────── */

  async _save(e) {
    // Receive serialized form data from ha-dialog-edit-panel via event detail.
    if (!e?.detail?.panel) return;
    // Sync item list data from dialog so saveFromData can read it
    if (e.detail.itemListData) {
      this._itemListData = e.detail.itemListData;
    }
    return Crud.saveFromData(this, e.detail.panel, e.detail.index);
  }
  async _savePanels(p, m)  { return Crud.savePanels(this, p, m); }

  /* ── device actions (called from templates, delegate to device-manager) ─ */

  async _selectDevice(name) { selectDevice(this, name); startStatusPolling(this); }

  _openDeviceConfig()      { DeviceConfig.openDeviceConfig(this); this.requestUpdate(); }
  _closeDeviceConfig()     { DeviceConfig.closeDeviceConfig(this); this.requestUpdate(); }
  async _saveDeviceConfig(){ return DeviceConfig.saveDeviceConfig(this); }

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
    this._onDeviceManagerImportYaml();
  }

  _onHeaderExportYaml() {
    this._actionsMenuIndex = null;
    this._onDeviceManagerExportYaml();
  }

  async _onDeviceManagerMoveDevice(e) {
    const { name, direction } = e.detail || {};
    if (!name || !direction) return;
    const devices = this._panels.devices || {};
    const deviceKeys = Object.keys(devices);
    const idx = deviceKeys.indexOf(name);
    if (idx < 0) return;
    const swapIdx = idx + direction;
    if (swapIdx < 0 || swapIdx >= deviceKeys.length) return;

    const newKeys = [...deviceKeys];
    [newKeys[idx], newKeys[swapIdx]] = [newKeys[swapIdx], newKeys[idx]];

    const newDevices = {};
    for (const key of newKeys) {
      newDevices[key] = devices[key];
    }
    this._panels = { ...this._panels, devices: newDevices };
    const label = direction < 0 ? "up" : "down";
    await this._savePanels(this._devicePanels(), `Device "${name}" moved ${label}`);
  }

  _onDeviceManagerSelect(e) {
    const name = e.detail?.name;
    if (!name) return;
    this._selectDevice(name);
  }

  _onDeviceManagerSettings(e) {
    const name = e.detail?.name;
    if (!name) return;
    this._showDeviceManager = false;
    this._selectedDevice = name;
    this._loadDeviceConfig(name);
    this._openDeviceConfig();
    this.requestUpdate();
  }

  async _onDeviceManagerRemove(e) {
    const name = e.detail?.name;
    if (!name) return;
    try {
      await Api.removeDevice(this, name);
      await Api.loadPanels(this);
      this._showToast(`Removed "${name}"`, "success");
    } catch (err) {
      this._showToast(err.message || "Failed to remove device", "error");
    }
    this.requestUpdate();
  }

  async _onDeviceManagerAdd(e) {
    const device = e.detail?.device;
    if (!device) return;
    try {
      await Api.addDevice(this, device);
      await Api.loadPanels(this);
      this._showToast(`Added "${device.name}"`, "success");
    } catch (err) {
      this._showToast(err.message || "Failed to add device", "error");
    }
    this.requestUpdate();
  }

  /* ── device manager action events ─────────────────────────────── */

  async _onDeviceManagerImportYaml() {
    const { importDeviceYaml } = await import('./device-manager.js');
    this._showDeviceManager = false;
    importDeviceYaml(this);
    this.requestUpdate();
  }

  async _onDeviceManagerExportYaml() {
    const { exportDeviceYaml } = await import('./device-manager.js');
    this._showDeviceManager = false;
    exportDeviceYaml(this);
    this.requestUpdate();
  }

  /* ── auto device discovery ──────────────────────────────────────────── */

  _autoDiscovered = false;

  async _autoDiscoverAndAdd() {
    let added = 0;
    try {
      const result = await Api.discoverDevices(this);
      const unconfigured = (result.devices || []).filter((d) => !d.configured);
      for (const device of unconfigured) {
        try {
          await Api.addDevice(this, {
            name: device.name,
            esphome_device_id: device.esphome_device_id || "",
          });
          added++;
        } catch (_e) {
          // skip devices that fail to add (duplicate, etc.)
        }
      }
    } catch (_e) {
      // discovery not available — not critical on load
      return;
    }
    if (added > 0) {
      await Api.loadPanels(this);
      this._showToast(`Added ${added} device(s)`, "success");
    }
  }

  /* ── toast ────────────────────────────────────────────────────────────── */

  _showToast(m, t)         { Toast.showToast(this, m, t); }

  /* ── render helpers ───────────────────────────────────────────────────── */

  _renderOptionField(o, v) { return renderOptionField(this, o, v); }

  /* ── render ───────────────────────────────────────────────────────────── */

  _devicePanels() {
    if (!this._selectedDevice || !this._panels?.devices?.[this._selectedDevice]) return [];
    return this._panels.devices[this._selectedDevice].panels || [];
  }

  render() {
    if (!this.entryId) {
      return html`<div class="container">
        ${renderTitleHeader(this)}
        <ha-card outlined class="content-card">
          ${renderEmptyCard("No NSPanel HAUI integration configured. Add one via Settings → Devices and Services.")}
        </ha-card>
      </div>`;
    }

    if (this._loading) {
      return html`<div class="container">
        ${renderTitleHeader(this)}
        <div class="loading">Loading panels...</div>
      </div>`;
    }

    return html`
      <div class="container">
        ${renderTitleHeader(this)}

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

        <ha-dialog-edit-panel
          .hass=${this.hass}
          .open=${!!this._editingPanel}
          .panel=${this._editingPanel}
          .panelTypes=${this._panelTypes}
          .devicePanels=${this._devicePanels()}
          .saving=${this._saving}
          .error=${this._error}
          .entryId=${this.entryId}
          .dialogVersion=${this._dialogVersion}
          @dialog-closed=${this._closeEdit}
          @dialog-save=${this._save}
        ></ha-dialog-edit-panel>

        <ha-dialog-device-config
          .hass=${this.hass}
          .open=${!!this._editingDeviceConfig}
          .config=${this._deviceConfigForm}
          .devicePanels=${this._devicePanels()}
          .saving=${this._saving}
          @dialog-closed=${this._closeDeviceConfig}
          @dialog-save=${this._onDeviceConfigSave}
        ></ha-dialog-device-config>

        <ha-dialog-confirm
          .hass=${this.hass}
          .open=${this._deleteTarget !== null}
          .params=${this._deleteTarget !== null ? this._confirmDialogParams : null}
          @dialog-closed=${this._cancelDelete}
          @dialog-confirmed=${this._doDelete}
        ></ha-dialog-confirm>

        <ha-dialog-device-info
          .hass=${this.hass}
          .open=${this._showDeviceInfo}
          .deviceStatus=${this._deviceStatus}
          @dialog-closed=${() => { this._showDeviceInfo = false; this.requestUpdate(); }}
        ></ha-dialog-device-info>

        <ha-dialog-logs
          .hass=${this.hass}
          .open=${this._showLogs}
          .logs=${this._deviceStatus?.logs || []}
          @dialog-closed=${() => { this._showLogs = false; this.requestUpdate(); }}
        ></ha-dialog-logs>
        <ha-dialog-device-manager
          .hass=${this.hass}
          .open=${this._showDeviceManager}
          .devices=${this._panels.devices || {}}
          .selectedDevice=${this._selectedDevice}
          .entryId=${this.entryId}
          @dialog-closed=${this._closeDeviceManager}
          @select-device=${this._onDeviceManagerSelect}
          @device-settings=${this._onDeviceManagerSettings}
          @remove-device=${this._onDeviceManagerRemove}
          @add-device=${this._onDeviceManagerAdd}
          @import-yaml=${this._onDeviceManagerImportYaml}
          @export-yaml=${this._onDeviceManagerExportYaml}
          @move-device=${this._onDeviceManagerMoveDevice}
        ></ha-dialog-device-manager>

        <ha-dialog-colors
          .hass=${this.hass}
          .open=${this._showColorsDialog}
          .overrides=${this._colorsDialog}
          @dialog-closed=${this._closeColorsDialog}
          @dialog-save=${this._onColorsSave}
        ></ha-dialog-colors>
        ${this._toast ? Toast.renderToast(this) : ""}
      </div>
    `;
  }

  /* ── item config dialog ─────────────────────────────────────────────── */

  _saveItemEdit() {
    const ee = this._editingItem;
    if (!ee) return;
    const { optKey, index } = ee;

    const uid = `item-edit-${optKey}-${index}`;
    const inline = this.renderRoot.querySelector(`#${uid}`);
    if (!inline) return;

    const typeVal = this._editingItemType || inline.querySelector("#item-type")?.value || "entity_id";

    // Encode item value based on type
    const inputVal = formVal(inline, "item-entity");
    const config = { item: encodeItemValue(inputVal, typeVal) };

    // Read standard entity override fields from ee.config — the input handlers
    // mutate ee.config with typed values (list/int/dict) where applicable, so
    // reading the DOM string would discard those types (e.g., strip list brackets).
    for (const f of ENTITY_OVERRIDE_FIELDS) {
      const fv = ee.config?.[f];
      if (fv !== null && fv !== undefined && fv !== '') config[f] = fv;
    }

    // Read per-item appearance overrides (declared by the panel type descriptor).
    const savePt = this._editingPanelType || this._editingPanel?.data?.type;
    const descriptor = (savePt && this._panelTypes)
      ? this._panelTypes.find(d => d.type_key === savePt) || null
      : null;
    if (descriptor?.item_options) {
      for (const f of descriptor.item_options) {
        const fv = ee.config?.[f];
        if (fv !== null && fv !== undefined && fv !== '') config[f] = fv;
      }
    }

    if (!this._itemListData) this._itemListData = {};
    if (!this._itemListData[optKey]) this._itemListData[optKey] = [];

    if (index >= 0) {
      const updated = [...this._itemListData[optKey]];
      updated[index] = config;
      this._itemListData[optKey] = updated;
    } else {
      this._itemListData[optKey] = [...this._itemListData[optKey], config];
    }

    this._editingItem = null;
    this._editingItemType = null;
    this.requestUpdate();
  }

  _cancelItemEdit() {
    this._editingItem = null;
    this._editingItemType = null;
    this.requestUpdate();
  }

  /* ── confirm dialog helper ─────────────────────────────────────────────── */

  get _confirmDialogParams() {
    const idx = this._deleteTarget;
    if (idx === null || idx === undefined) return null;
    const panel = this._devicePanels()[idx];
    const name = panel ? panel.title || `panel #${idx}` : "this panel";
    return {
      title: "Delete panel?",
      message: `Delete ${name}? This cannot be undone.`,
      confirmText: "Delete",
      cancelText: "Cancel",
    };
  }

  /* ── device config save handler ──────────────────────────────────────────── */
  /* Receives form state from ha-dialog-device-config and saves directly.      */

  async _onDeviceConfigSave(e) {
    const cfg = e.detail?.config;
    if (!cfg || !this._selectedDevice) return;

    // savePanels clones host._deviceConfig into the POST payload, so we
    // only need to update _deviceConfig here — the _panels state will be
    // synced from _deviceConfig by savePanels.
    this._deviceConfig = clone(cfg);

    this._saving = true;
    this.requestUpdate();

    try {
      await this._savePanels(this._devicePanels(), "Device config saved");
      this._showToast("Device configuration saved", "success");
    } catch (e) {
      this._showToast(e.message || "Device config save failed", "error");
    } finally {
      this._saving = false;
      this._editingDeviceConfig = false;
      this._deviceConfigForm = null;
      this.requestUpdate();
    }
  }

  /* ── colors dialog ────────────────────────────────────────────────── */

  _onHeaderColors() {
    this._actionsMenuIndex = null;
    if (!this._selectedDevice) return;
    this._loadDeviceConfig(this._selectedDevice);
    const overrides = this._deviceConfig?.color_overrides || {};
    this._colorsDialog = clone(overrides);
    this._showColorsDialog = true;
    this.requestUpdate();
  }

  _closeColorsDialog() {
    this._showColorsDialog = false;
    this.requestUpdate();
  }

  async _onColorsSave(e) {
    const overrides = e.detail?.overrides;
    if (!overrides || !this._selectedDevice) return;

    // Merge overrides into device config — DEVICE_CONFIG_DEFAULTS now includes
    // color_overrides:{} so fallback is always safe.
    this._deviceConfig = {
      ...(this._deviceConfig || DEVICE_CONFIG_DEFAULTS),
      color_overrides: overrides,
    };

    try {
      await this._savePanels(this._devicePanels(), "Device colors saved");
      this._showToast("Device colors saved", "success");
    } catch (e) {
      this._showToast(e.message || "Failed to save colors", "error");
    } finally {
      this._showColorsDialog = false;
      this.requestUpdate();
    }
  }
}

customElements.define("nspanel-haui-editor", NSPanelEditor);
export { NSPanelEditor };
