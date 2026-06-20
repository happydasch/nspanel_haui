/**
 * NSPanel HAUI - Editor - Device Manager dialog.
 *
 * Proper Lit custom element showing all configured devices with
 * add, select, settings, and remove capabilities.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { dialogHeader } from './dialog-header.js';
import { t } from '../localize.js';
import { positionContextMenu, onOutsideClick, offOutsideClick } from '../dom-helpers.js';
import * as Toast from '../toast.js';
import { readNetworkInfo, rssiIcon, rssiStrengthClass } from '../network-info.js';

/* ── helpers ────────────────────────────────────────────────── */

/**
 * Single event dispatcher that all event-emitting methods delegate to.
 */
function _dispatch(eventName, detail = {}) {
  return new CustomEvent(eventName, {
    detail,
    bubbles: true,
    composed: true,
  });
}

/**
 * Render a compact WiFi icon for the title row.
 */
function renderWifiIcon(rssi, ssid) {
  if (rssi == null || rssi === "") {
    return html`<ha-icon icon="mdi:wifi-off" class="wifi-icon-head wifi-off"
      title="${t('Offline')}"></ha-icon>`;
  }
  const icon = rssiIcon(rssi);
  const colorCls = rssiStrengthClass(rssi);
  let detail = `${rssi} dBm`;
  if (ssid) detail += `  ·  ${ssid}`;
  return html`<ha-icon icon="${icon}" class="wifi-icon-head ${colorCls}" title="${detail}"></ha-icon>`;
}

class DeviceManagerDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      devices: { type: Object },
      selectedDevice: { type: String },
      entryId: { type: String },
      _showAddForm: { type: Boolean, state: true },
      _newDeviceName: { type: String, state: true },
      _addError: { type: String, state: true },
      _removingDevice: { type: String, state: true },
      _deviceMenuIndex: { type: Number, state: true },
      _toast: { type: Object, state: true },
      _deviceStatuses: { type: Object, state: true },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
    this.devices = {};
    this.selectedDevice = null;
    this.entryId = null;
    this._deviceStatuses = {};
    this._showAddForm = false;
    this._newDeviceName = "";
    this._addError = "";
    this._removingDevice = null;
    this._deviceMenuIndex = null;
    this.__statusTimer = null;
  }

  connectedCallback() {
    super.connectedCallback();
    onOutsideClick(
      this,
      (e) => {
        if (this._deviceMenuIndex === null || this._deviceMenuIndex === undefined) return true; // nothing open
        const path = e.composedPath();
        const wraps = this.renderRoot.querySelectorAll('.device-mgr-more');
        return [...wraps].some((w) => path.includes(w));
      },
      () => this._closeDeviceMenu(),
    );
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    offOutsideClick(this);
  }

  showToast(message, type = "success") { Toast.showToast(this, message, type); }

  /* ── per-device status polling ──────────────────────────────────── */

  updated(changed) {
    if (changed.has("_deviceMenuIndex") && this._deviceMenuIndex !== null) {
      // Reposition the open dropdown to escape dialog overflow clipping
      this.updateComplete.then(() => {
        const dropdown = this.renderRoot.querySelector(".device-mgr-dropdown");
        const more = this.renderRoot.querySelector(".device-mgr-more ha-icon-button.active");
        if (dropdown && more) positionContextMenu(dropdown, more);
      });
    }
    if (changed.has("open")) {
      if (this.open) {
        this._fetchAllStatuses();
        this.__statusTimer = setInterval(() => this._fetchAllStatuses(), 5000);
      } else {
        if (this.__statusTimer) {
          clearInterval(this.__statusTimer);
          this.__statusTimer = null;
        }
      }
    }
  }

  async _fetchAllStatuses() {
    if (!this.entryId || !this.hass) return;
    try {
      const resp = await this.hass.fetchWithAuth(
        `/api/nspanel_haui/status/${this.entryId}`
      );
      if (resp.ok) {
        const data = await resp.json();
        this._deviceStatuses = (data.devices && typeof data.devices === "object")
          ? data.devices
          : {};
      }
    } catch (e) {
      // Silently ignore — stale status is harmless
    }
  }

  _closeDeviceMenu() { this._deviceMenuIndex = null; }

  render() {
    const deviceKeys = Object.keys(this.devices || {});
    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        .preventScrimClose=${true}
      >
        ${dialogHeader(t('Device Manager'), this._dispatchClose)}
        <form @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">
            <!-- add device form (foldable) -->
            ${this._showAddForm ? html`
              <div class="device-mgr-add-form">
                <div class="form-group">
                  <label>${t('Device Name')}</label>
                  <ha-input
                    .value=${this._newDeviceName}
                    @input=${(e) => this._newDeviceName = e.target.value}
                    placeholder=${t('my_nspanel')}
                  ></ha-input>
                </div>
                <div class="device-mgr-add-actions">
                  <ha-button variant="neutral" appearance="plain" @click=${() => { this._showAddForm = false; this._newDeviceName = ""; this._addError = ""; }}>
                    ${t('Cancel')}
                  </ha-button>
                  <ha-button @click=${this._onAddDevice}>
                    ${t('Add')}
                  </ha-button>
                </div>
                ${this._addError ? html`<p class="device-mgr-error">${this._addError}</p>` : ""}
              </div>
            ` : ""}

            <!-- configured devices -->
            <div class="device-mgr-section">
              <h3 class="device-mgr-section-title">${t('Devices')} (${deviceKeys.length})</h3>
              ${deviceKeys.length === 0 ? html`
                <p class="device-mgr-empty">${t('No devices configured yet.')}</p>
              ` : deviceKeys.map(name => this._renderDeviceRow(name))}
            </div>

            </div>
        </form>${Toast.renderToast(this)}

        <div slot="footer" class="device-mgr-footer">
          <div class="footer-toggle-wrapper">
            <ha-button @click=${() => this._dispatchUpdateAll()} variant="neutral" appearance="plain">
              <ha-icon icon="mdi:refresh" slot="icon"></ha-icon>
              ${t('Update All')}
            </ha-button>
          </div>
          <ha-button @click=${this._dispatchClose}>
            ${t('Close')}
          </ha-button>
        </div>
      </ha-dialog>
    `;
  }

  _renderDeviceRow(name) {
    const dev = (this.devices || {})[name] || {};
    const config = dev.config || {};
    const enabled = config.enabled !== false;
    const panelCount = (dev.panels || []).length;
    const isSelected = name === this.selectedDevice;
    const isRemoving = name === this._removingDevice;
    const deviceKeys = Object.keys(this.devices || {});
    const idx = deviceKeys.indexOf(name);
    const canMoveUp = idx > 0;
    const canMoveDown = idx >= 0 && idx < deviceKeys.length - 1;
    const menuOpen = this._deviceMenuIndex === idx;
    const di = this._deviceStatuses?.[name]?.device_info;
    const yaml = di?.yaml_version || '-';
    const tft = di?.tft_version || '-';
    const nw = readNetworkInfo(this.hass, name);

    const dropdownItems = [
      {
        icon: enabled ? 'mdi:close-circle-outline' : 'mdi:check-circle-outline',
        label: enabled ? t('Disable') : t('Enable'), action: () => { this._dispatchToggleDevice(name); this._closeDeviceMenu(); }
      },
      'divider',
      { icon: 'mdi:refresh', label: t('Update'), action: () => { this._dispatchUpdateDisplay(name); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:arrow-up', label: t('Move Up'), disabled: !canMoveUp, action: () => { this._dispatchMoveDevice(name, -1); this._closeDeviceMenu(); } },
      { icon: 'mdi:arrow-down', label: t('Move Down'), disabled: !canMoveDown, action: () => { this._dispatchMoveDevice(name, 1); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:cog-outline', label: t('Settings'), action: () => { this._dispatchDeviceSettings(name); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:delete-outline', label: t('Remove'), disabled: isRemoving, danger: true, action: () => { this._onRemoveDevice(name); this._closeDeviceMenu(); } },
    ];

    return html`
      <div class="device-mgr-row ${isSelected ? 'selected' : ''} ${enabled ? 'row-enabled' : 'row-disabled'}" @click=${() => this._dispatchSelectDevice(name)}>
        <div class="device-mgr-row-body">
          <div class="device-mgr-row-head">
            <span class="device-mgr-state-indicator ${enabled ? 'state-on' : 'state-off'}"
                  title=${enabled ? t('Enabled') : t('Disabled')}></span>
            <span class="device-mgr-name">${name}</span>
            ${renderWifiIcon(nw.rssi, nw.ssid)}
            <span class="device-mgr-panel-count">${panelCount} ${t('panel')}${panelCount !== 1 ? 's' : ''}</span>
          </div>
          <div class="device-mgr-row-details">
            ${yaml !== '-' ? html`<span class="info-chip" title="${t('YAML Version')}">Y: ${yaml}</span>` : ''}
            ${tft !== '-' ? html`<span class="info-chip" title="${t('TFT Version')}">T: ${tft}</span>` : ''}
            ${nw.ip ? html`<span class="info-chip" title="${t('IP Address')}">${nw.ip}</span>` : ''}
          </div>
        </div>
        <div class="device-mgr-row-actions">
          <div class="device-mgr-more" data-didx=${idx}>
            <ha-icon-button
              title=${t('More')}
              class=${menuOpen ? 'active' : ''}
              @click=${(e) => {
                e.stopPropagation();
                if (this._deviceMenuIndex === idx) {
                  this._closeDeviceMenu();
                } else {
                  this._deviceMenuIndex = idx;
                }
              }}
            >
              <ha-icon icon="mdi:dots-vertical"></ha-icon>
            </ha-icon-button>
            ${menuOpen ? html`
              <div class="device-mgr-dropdown">
                ${dropdownItems.map(item => item === 'divider'
                  ? html`<div class="device-mgr-dropdown-divider"></div>`
                  : html`<button class="device-mgr-dropdown-item${item.danger ? ' danger' : ''}"
                      ?disabled=${item.disabled}
                      @click=${(e) => { e.stopPropagation(); item.action(); }}>
                      <ha-icon icon=${item.icon}></ha-icon> ${item.label}
                    </button>`
                )}
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }

  /* ── event dispatchers ───────────────────────────────────────────────── */

  _dispatchToggleDevice(name) { this.dispatchEvent(_dispatch("toggle-device", { name })); }

  _dispatchClose() { this.dispatchEvent(_dispatch("dialog-closed")); }

  _dispatchSelectDevice(name) { this.dispatchEvent(_dispatch("select-device", { name })); }

  _dispatchDeviceSettings(name) { this.dispatchEvent(_dispatch("device-settings", { name })); }

  _dispatchRemoveDevice(name) { this.dispatchEvent(_dispatch("remove-device", { name })); }

  _dispatchAddDevice(device) { this.dispatchEvent(_dispatch("add-device", { device })); }

  _dispatchMoveDevice(name, direction) { this.dispatchEvent(_dispatch("move-device", { name, direction })); }

  _dispatchUpdateDisplay(name) { this.dispatchEvent(_dispatch("update-display", { name })); }

  _dispatchUpdateAll() { this._dispatchUpdateDisplay("*"); }


  /* ── add device ──────────────────────────────────────────────────── */

  _onAddDevice() {
    const name = (this._newDeviceName || "").trim();
    if (!name) {
      this._addError = t('Device name is required');
      this.requestUpdate();
      return;
    }
    if (this.devices[name]) {
      this._addError = `${t('Device')} "${name}" ${t('already exists')}`;
      this.requestUpdate();
      return;
    }
    this._dispatchAddDevice({
      name,
      esphome_device_id: "",
    });
    this._showAddForm = false;
    this._newDeviceName = "";
    this._addError = "";
    this.requestUpdate();
  }

  /* ── remove ──────────────────────────────────────────────────────────── */

  _onRemoveDevice(name) {
    this._dispatchRemoveDevice(name);
  }
}

customElements.define("ha-dialog-device-manager", DeviceManagerDialog);
export { DeviceManagerDialog };
