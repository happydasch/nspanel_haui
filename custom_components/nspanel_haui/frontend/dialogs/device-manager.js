/**
 * NSPanel HAUI - Device Manager dialog.
 *
 * Lists the configured devices with their versions and update state; adds
 * devices found by a scan and runs the per-device actions of the row menu.
 */
import { html } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import './confirm.js';
import { t } from '../localize.js';
import { positionContextMenu, onOutsideClick, offOutsideClick } from '../dom-helpers.js';
import * as Toast from '../toast.js';
import { scanDevices } from '../api.js';
import { rssiIcon, rssiStrengthClass, fmtRssi, isOlderVersion } from '../device-info.js';

/* ── helpers ────────────────────────────────────────────────── */

/**
 * Render a compact WiFi icon for the title row.
 */
function renderWifiIcon(rssi, ssid) {
  const colorCls = rssiStrengthClass(rssi);
  const detail = [fmtRssi(rssi), ssid].filter(Boolean).join("  ·  ");
  return html`<ha-icon icon="${rssiIcon(rssi)}" class="wifi-icon-head ${colorCls}"
    title="${detail}"></ha-icon>`;
}

/**
 * Render a TFT update state chip for a device status payload.
 *
 * @param {Object|undefined} update - `status.update` from the backend
 * @returns {string|undefined} chip markup, or nothing when idle/absent
 */
function renderUpdateStateChip(update) {
  const state = update?.state;
  if (!state || state === "idle") return "";
  const labels = {
    checking: t('Checking for update\u2026'),
    installing: t('Installing TFT\u2026'),
    done: t('TFT installed'),
    error: t('TFT update failed'),
  };
  const label = labels[state] || state;
  const warn = state === "error" ? " info-chip-error" : "";
  const title = state === "error" && update?.last_error
    ? `${label}: ${update.last_error}`
    : label;
  return html`<span class="info-chip${warn}" title="${title}">${label}</span>`;
}

class DeviceManagerDialog extends HauiDialog {
  static get properties() {
    return {
      devices: { type: Object },
      selectedDevice: { type: String },
      entryId: { type: String },
      _scannedDevices: { type: Array, state: true },
      _scanning: { type: Boolean, state: true },
      _scanError: { type: String, state: true },
      _deviceMenuIndex: { type: Number, state: true },
      _removeTarget: { type: String, state: true },
      _toast: { type: Object, state: true },
      _deviceStatuses: { type: Object, state: true },
    };
  }

  constructor() {
    super();
    this.devices = {};
    this.selectedDevice = null;
    this.entryId = null;
    this._deviceStatuses = {};
    this._scannedDevices = [];
    this._scanning = false;
    this._scanError = "";
    this._deviceMenuIndex = null;
    // Device whose removal waits for confirmation.
    this._removeTarget = null;
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
    this._stopStatusPolling();
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
        this._startStatusPolling();
        this._onScan();
      } else {
        this._stopStatusPolling();
        this._removeTarget = null;
      }
    }
  }

  _startStatusPolling() {
    this._stopStatusPolling();
    this._fetchAllStatuses();
    this.__statusTimer = setInterval(() => this._fetchAllStatuses(), 5000);
  }

  _stopStatusPolling() {
    if (this.__statusTimer) {
      clearInterval(this.__statusTimer);
      this.__statusTimer = null;
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
    // A device added from the scan results leaves them once the editor reloads.
    const scanned = this._scannedDevices.filter((d) => !(this.devices || {})[d.name]);
    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
      >
        ${dialogHeader(t('Device Manager'), this._dispatchClose)}
        <form @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">
            <!-- configured devices -->
            <div class="device-mgr-section">
              <h3 class="device-mgr-section-title">${t('Devices')} (${deviceKeys.length})</h3>
              ${deviceKeys.length === 0 ? html`
                <p class="device-mgr-empty">${t('No devices configured yet.')}</p>
              ` : deviceKeys.map(name => this._renderDeviceRow(name))}
            </div>

            ${this._scanning ? html`<p class="field-hint">${t('Scanning...')}</p>` : ''}
            <!-- discovered devices (scan results) -->
            ${scanned.length > 0 ? html`
              <div class="device-mgr-section">
                <h3 class="device-mgr-section-title">${t('Discovered Devices')}</h3>
                <div class="device-mgr-section-actions">
                  <ha-button @click=${() => this._emit("scan-devices", { devices: scanned })} variant="neutral" appearance="plain">
                    <ha-icon icon="mdi:plus-circle-outline" slot="icon"></ha-icon>
                    ${t('Add All')}
                  </ha-button>
                </div>
                ${scanned.map(d => html`
                  <div class="device-mgr-row">
                    <div class="device-mgr-row-body">
                      <div class="device-mgr-row-head">
                        <span class="device-mgr-name">${d.friendly_name || d.name}</span>
                      </div>
                      <div class="device-mgr-row-details">
                        ${d.name !== (d.friendly_name || d.name) ? html`<span class="info-chip">${d.name}</span>` : ''}
                      </div>
                    </div>
                    <div class="device-mgr-row-actions">
                      <ha-button @click=${() => this._emit("add-device", { device: { name: d.name, esphome_device_id: d.esphome_device_id || '' } })}>
                        ${t('Add')}
                      </ha-button>
                    </div>
                  </div>
                `)}
              </div>
            ` : ''}
            ${this._scanError ? html`<p class="device-mgr-error">${this._scanError}</p>` : ''}

            </div>
        </form>${Toast.renderToast(this)}

        <div slot="footer" class="device-mgr-footer">
          <ha-button @click=${this._dispatchClose}>
            ${t('Close')}
          </ha-button>
        </div>
      </ha-dialog>

      <!-- outside ha-dialog: its closed event must not close the manager -->
      <nspanel-dialog-confirm
        .hass=${this.hass}
        .open=${this._removeTarget !== null}
        .params=${this._removeParams}
        @dialog-closed=${() => { this._removeTarget = null; }}
        @dialog-confirmed=${this._confirmRemove}
      ></nspanel-dialog-confirm>
    `;
  }

  get _removeParams() {
    const name = this._removeTarget;
    if (name === null || name === undefined) return null;
    return {
      title: t('Remove device?'),
      message: t('Remove {name} from the hub? Its settings and panels are deleted. This cannot be undone.')
        .replace('{name}', (this.devices || {})[name]?.friendly_name || name),
      confirmText: t('Remove'),
      cancelText: t('Cancel'),
    };
  }

  _confirmRemove() {
    const name = this._removeTarget;
    this._removeTarget = null;
    if (name) this._emit("remove-device", { name });
  }

  _renderDeviceRow(name) {
    const dev = (this.devices || {})[name] || {};
    const config = dev.config || {};
    const enabled = config.enabled !== false;
    const panelCount = (dev.panels || []).length;
    const isSelected = name === this.selectedDevice;
    const deviceKeys = Object.keys(this.devices || {});
    const idx = deviceKeys.indexOf(name);
    const canMoveUp = idx > 0;
    const canMoveDown = idx >= 0 && idx < deviceKeys.length - 1;
    const menuOpen = this._deviceMenuIndex === idx;
    const di = this._deviceStatuses?.[name]?.device_info;
    const status = this._deviceStatuses?.[name];
    const updateStatus = status?.update;
    const yaml = di?.yaml_version;
    const requiredTft = di?.tft_required_version;
    const tft = di?.tft_version;
    const nw = di || {};

    const displayName = dev.friendly_name || name;

    const dropdownItems = [
      {
        icon: enabled ? 'mdi:close-circle-outline' : 'mdi:check-circle-outline',
        label: enabled ? t('Disable') : t('Enable'), action: () => { this._emit("toggle-device", { name }); this._closeDeviceMenu(); }
      },
      'divider',
      { icon: 'mdi:arrow-up', label: t('Move Up'), disabled: !canMoveUp, action: () => { this._emit("move-device", { name, direction: -1 }); this._closeDeviceMenu(); } },
      { icon: 'mdi:arrow-down', label: t('Move Down'), disabled: !canMoveDown, action: () => { this._emit("move-device", { name, direction: 1 }); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:cog-outline', label: t('Settings'), action: () => { this._emit("device-settings", { name }); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:delete-outline', label: t('Remove'), danger: true, action: () => { this._removeTarget = name; this._closeDeviceMenu(); } },
    ];

    return html`
      <div class="device-mgr-row ${isSelected ? 'selected' : ''} ${enabled ? 'row-enabled' : 'row-disabled'}" @click=${() => this._emit("select-device", { name })}>
        <div class="device-mgr-row-body">
          <div class="device-mgr-row-head">
            <span class="device-mgr-state-indicator ${enabled ? 'state-on' : 'state-off'}"
                  title=${enabled ? t('Enabled') : t('Disabled')}></span>
            <span class="device-mgr-name">${displayName}</span>
            ${name !== displayName ? html`<span class="device-mgr-name-sub">${name}</span>` : ''}
            ${renderWifiIcon(nw.rssi, nw.ssid)}
            <span class="device-mgr-panel-count">${panelCount} ${panelCount !== 1 ? t('panels') : t('panel')}</span>
          </div>
          <div class="device-mgr-row-details">
            ${yaml
              ? html`<span class="info-chip" title="${t('ESPHome firmware version')}">${t('Firmware')} ${yaml}</span>`
              : html`<span class="info-chip" title="${t('ESPHome firmware version')}">${t('Firmware')} ${t('Unknown')}</span>`}
            ${status?.haui_version_mismatch === true
              ? html`<span class="info-chip info-chip-warn" title="${t('The ESPHome firmware version does not match this HAUI version')}">${t('Firmware mismatch')}</span>`
              : ""}
            ${tft && requiredTft && isOlderVersion(tft, requiredTft)
              ? html`<span class="info-chip info-chip-warn" title="${t('The display is updated automatically to the version the firmware needs')}">${t('Display')} ${tft} · ${t('update pending')}</span>`
              : html`<span class="info-chip${tft ? '' : ' info-chip-warn'}" title="${t('Display (TFT) version')}">${t('Display')} ${tft || t('Unknown')}</span>`}
            ${renderUpdateStateChip(this._deviceStatuses?.[name]?.update)}
            ${updateStatus?.firmware_installing
              ? html`<span class="info-chip info-chip-warn" title="${t('Firmware update in progress')}">${t('Installing firmware…')}</span>`
              : updateStatus?.firmware_update_available
                ? html`<span class="info-chip info-chip-warn" title="${t('The device reports a firmware update available')}">${t('Firmware update available')}</span>`
                : ''}
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

  /* ── scan for devices ──────────────────────────────────────────────── */

  async _onScan() {
    this._scanning = true;
    this._scanError = "";
    this._scannedDevices = [];
    this.requestUpdate();
    try {
      const result = await scanDevices({ entryId: this.entryId, hass: this.hass });
      const discovered = (result.devices || []).filter(
        (d) => !(this.devices || {})[d.name || d.friendly_name]
      );
      this._scannedDevices = discovered;
    } catch (e) {
      this._scanError = e.message || t('Scan failed');
    }
    this._scanning = false;
    this.requestUpdate();
  }
}

customElements.define("nspanel-dialog-device-manager", DeviceManagerDialog);
export { DeviceManagerDialog };
