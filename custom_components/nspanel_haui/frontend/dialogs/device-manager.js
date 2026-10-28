/**
 * NSPanel HAUI - Device Manager dialog.
 *
 * Proper Lit custom element showing all configured devices with
 * add, select, settings, and remove capabilities.
 */
import { html } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';
import { positionContextMenu, onOutsideClick, offOutsideClick } from '../dom-helpers.js';
import * as Toast from '../toast.js';
import { scanDevices, getFirmwareDownload } from '../api.js';
import { readNetworkInfo, rssiIcon, rssiStrengthClass } from '../network-info.js';
import { isOlderVersion } from '../device-info.js';

/* ── helpers ────────────────────────────────────────────────── */

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
      _showAddForm: { type: Boolean, state: true },
      _newDeviceName: { type: String, state: true },
      _addError: { type: String, state: true },
      _scannedDevices: { type: Array, state: true },
      _scanning: { type: Boolean, state: true },
      _scanError: { type: String, state: true },
      _removingDevice: { type: String, state: true },
      _deviceMenuIndex: { type: Number, state: true },
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
    this._showAddForm = false;
    this._newDeviceName = "";
    this._addError = "";
    this._scannedDevices = [];
    this._scanning = false;
    this._scanError = "";
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
      if (this.open) this._startStatusPolling();
      else this._stopStatusPolling();
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
                  <input
                    class="native-input"
                    .value=${this._newDeviceName}
                    @input=${(e) => this._newDeviceName = e.target.value}
                    placeholder=${t('my_nspanel')}
                  />
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

            <!-- discovered devices (scan results) -->
            ${this._scannedDevices.length > 0 ? html`
              <div class="device-mgr-section">
                <h3 class="device-mgr-section-title">${t('Discovered Devices')}</h3>
                <div class="device-mgr-section-actions">
                  <ha-button @click=${() => this._emit("scan-devices", { devices: this._scannedDevices })} variant="neutral" appearance="plain">
                    <ha-icon icon="mdi:plus-circle-outline" slot="icon"></ha-icon>
                    ${t('Add All')}
                  </ha-button>
                </div>
                ${this._scannedDevices.map(d => html`
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
          <div class="footer-toggle-wrapper">
            <ha-button @click=${() => this._onScan()} variant="neutral" appearance="plain" ?disabled=${this._scanning}>
              <ha-icon icon="mdi:magnify" slot="icon"></ha-icon>
              ${this._scanning ? t('Scanning...') : t('Scan')}
            </ha-button>
            <ha-button @click=${() => this._emit("update-display", { name: "*" })} variant="neutral" appearance="plain">
              <ha-icon icon="mdi:refresh" slot="icon"></ha-icon>
              ${t('Refresh all displays')}
            </ha-button>
            <ha-button @click=${() => this._onDownloadFirmware()} variant="neutral" appearance="plain" title="${t('Download the firmware binary of the latest release')}">
              <ha-icon icon="mdi:download" slot="icon"></ha-icon>
              ${t('Download firmware')}
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
    const updateStatus = this._deviceStatuses?.[name]?.update;
    const yaml = di?.yaml_version;
    const tft = di?.tft_version;
    // Prefer the server-resolved network info (entity-registry based) over the
    // client-side slug lookup, which misses area/device-prefixed entity ids.
    const nw = (di?.ip) ? { ip: di.ip, ssid: di.ssid || '', rssi: di.rssi } : readNetworkInfo(this.hass, name);

    const displayName = dev.friendly_name || name;

    const dropdownItems = [
      {
        icon: enabled ? 'mdi:close-circle-outline' : 'mdi:check-circle-outline',
        label: enabled ? t('Disable') : t('Enable'), action: () => { this._emit("toggle-device", { name }); this._closeDeviceMenu(); }
      },
      'divider',
      { icon: 'mdi:refresh', label: t('Refresh display'), action: () => { this._emit("update-display", { name }); this._closeDeviceMenu(); } },
      { icon: 'mdi:update', label: t('Install TFT'), action: () => { this._emit("update-tft", { name }); this._closeDeviceMenu(); } },
      ...(updateStatus?.firmware_update_available ? [{
        icon: 'mdi:chip', label: t('Install firmware'), disabled: updateStatus.firmware_installing,
        action: () => { this._emit("update-firmware", { name }); this._closeDeviceMenu(); },
      }] : []),
      { icon: 'mdi:cloud-search-outline', label: t('Check for updates'), action: () => { this._emit("check-for-update", { name }); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:arrow-up', label: t('Move Up'), disabled: !canMoveUp, action: () => { this._emit("move-device", { name, direction: -1 }); this._closeDeviceMenu(); } },
      { icon: 'mdi:arrow-down', label: t('Move Down'), disabled: !canMoveDown, action: () => { this._emit("move-device", { name, direction: 1 }); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:cog-outline', label: t('Settings'), action: () => { this._emit("device-settings", { name }); this._closeDeviceMenu(); } },
      'divider',
      { icon: 'mdi:delete-outline', label: t('Remove'), disabled: isRemoving, danger: true, action: () => { this._emit("remove-device", { name }); this._closeDeviceMenu(); } },
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
            ${tft && yaml && isOlderVersion(tft, yaml)
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
      if (!discovered.length) {
        this._scanError = t('No new HAUI devices found');
      }
    } catch (e) {
      this._scanError = e.message || t('Scan failed');
    }
    this._scanning = false;
    this.requestUpdate();
  }

  /* ── firmware download link ─────────────────────────────────────── */

  async _onDownloadFirmware() {
    try {
      const { url, version } = await getFirmwareDownload({ entryId: this.entryId, hass: this.hass });
      if (!url) {
        this.showToast(t("No prebuilt firmware binary published for this release. Build from YAML or use the ESPHome dashboard."), "error");
        return;
      }
      window.open(url, "_blank");
      this.showToast(
        version
          ? t('Downloading firmware {version}').replace('{version}', version)
          : t('Downloading firmware'),
        "success",
      );
    } catch (e) {
      this.showToast(e.message || t("Failed to load the firmware link"), "error");
    }
  }

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
    this._emit("add-device", { device: { name, esphome_device_id: "" } });
    this._showAddForm = false;
    this._newDeviceName = "";
    this._addError = "";
    this.requestUpdate();
  }
}

customElements.define("nspanel-dialog-device-manager", DeviceManagerDialog);
export { DeviceManagerDialog };
