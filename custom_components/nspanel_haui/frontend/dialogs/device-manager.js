/**
 * NSPanel HAUI - Editor - Device Manager dialog.
 *
 * Proper Lit custom element showing all configured devices with
 * add, discover, select, settings, and remove capabilities.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';

class DeviceManagerDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      devices: { type: Object },
      selectedDevice: { type: String },
      entryId: { type: String },
      _discovering: { type: Boolean, state: true },
      _discoveredDevices: { type: Array, state: true },
      _showAddForm: { type: Boolean, state: true },
      _newDeviceName: { type: String, state: true },
      _addError: { type: String, state: true },
      _removingDevice: { type: String, state: true },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
    this.devices = {};
    this.selectedDevice = null;
    this.entryId = null;
    this._discovering = false;
    this._discoveredDevices = [];
    this._showAddForm = false;
    this._newDeviceName = "";
    this._addError = "";
    this._removingDevice = null;
  }

  render() {
    const deviceKeys = Object.keys(this.devices || {});
    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title="Device Manager"
        .preventScrimClose=${true}
      >
        <form @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">
            <!-- add device form (foldable) -->
            ${this._showAddForm ? html`
              <div class="device-mgr-add-form">
                <div class="form-group">
                  <label>Device Name</label>
                  <ha-input
                    .value=${this._newDeviceName}
                    @input=${(e) => this._newDeviceName = e.target.value}
                    placeholder="my_nspanel"
                  ></ha-input>
                </div>
                <div class="device-mgr-add-actions">
                  <ha-button variant="neutral" appearance="plain" @click=${() => { this._showAddForm = false; this._newDeviceName = ""; this._addError = ""; }}>
                    Cancel
                  </ha-button>
                  <ha-button @click=${this._onAddDevice}>
                    Add
                  </ha-button>
                </div>
                ${this._addError ? html`<p class="device-mgr-error">${this._addError}</p>` : ""}
              </div>
            ` : ""}

            <!-- discovered devices -->
            ${this._discoveredDevices.length > 0 ? html`
              <div class="device-mgr-section">
                <h3 class="device-mgr-section-title">Discovered Devices (${this._discoveredDevices.length})</h3>
                ${this._discoveredDevices.map(d => html`
                  <div class="device-mgr-row discovered-row">
                    <div class="device-mgr-row-info">
                      <span class="device-mgr-name"><strong>${d.name}</strong></span>
                    </div>
                    <ha-button variant="neutral" appearance="plain" @click=${() => this._onAddDiscovered(d)}>
                      Add
                    </ha-button>
                  </div>
                `)}
              </div>
            ` : ""}

            <!-- configured devices -->
            <div class="device-mgr-section">
              <h3 class="device-mgr-section-title">Configured Devices (${deviceKeys.length})</h3>
              ${deviceKeys.length === 0 ? html`
                <p class="device-mgr-empty">No devices configured yet.</p>
              ` : deviceKeys.map(name => this._renderDeviceRow(name))}
            </div>

            </div>
        </form>

        <div slot="footer" class="device-mgr-footer">
          <ha-button
            ?disabled=${this._discovering}
            @click=${this._onDiscover}
            variant="neutral" appearance="plain"
          >
            <ha-icon icon="mdi:wifi" slot="icon"></ha-icon>
            ${this._discovering ? "Discovering…" : "Discover"}
          </ha-button>
          <ha-button @click=${this._dispatchClose}>
            Close
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

    return html`
      <div class="device-mgr-row ${isSelected ? 'selected' : ''}" @click=${() => this._dispatchSelectDevice(name)}>
        <div class="device-mgr-row-status">
          <span class="device-mgr-dot ${enabled ? 'dot-connected' : 'dot-disconnected'}"
                title=${enabled ? "Enabled" : "Disabled"}></span>
        </div>
        <div class="device-mgr-row-info">
          <span class="device-mgr-name"><strong>${name}</strong></span>
          <span class="device-mgr-meta">
            ${panelCount} panel${panelCount !== 1 ? 's' : ''}
            ${!enabled ? '· (disabled)' : ''}
          </span>
        </div>
        <div class="device-mgr-row-actions">
          <ha-icon-button
            title="Move up"
            ?disabled=${!canMoveUp}
            @click=${(e) => { e.stopPropagation(); this._dispatchMoveDevice(name, -1); }}
          >
            <ha-icon icon="mdi:arrow-up"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
            title="Move down"
            ?disabled=${!canMoveDown}
            @click=${(e) => { e.stopPropagation(); this._dispatchMoveDevice(name, 1); }}
          >
            <ha-icon icon="mdi:arrow-down"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
            title="Device Settings"
            @click=${(e) => { e.stopPropagation(); this._dispatchDeviceSettings(name); }}
          >
            <ha-icon icon="mdi:cog-outline"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
            title="Remove"
            class="device-mgr-remove-btn"
            ?disabled=${isRemoving}
            @click=${(e) => { e.stopPropagation(); this._onRemoveDevice(name); }}
          >
            <ha-icon icon="mdi:delete-outline"></ha-icon>
          </ha-icon-button>
        </div>
      </div>
    `;
  }

  /* ── event dispatchers ───────────────────────────────────────────────── */

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }

  _dispatchSelectDevice(name) {
    this.dispatchEvent(new CustomEvent("select-device", {
      detail: { name },
      bubbles: true,
      composed: true,
    }));
  }

  _dispatchDeviceSettings(name) {
    this.dispatchEvent(new CustomEvent("device-settings", {
      detail: { name },
      bubbles: true,
      composed: true,
    }));
  }

  _dispatchRemoveDevice(name) {
    this.dispatchEvent(new CustomEvent("remove-device", {
      detail: { name },
      bubbles: true,
      composed: true,
    }));
  }

  _dispatchAddDevice(device) {
    this.dispatchEvent(new CustomEvent("add-device", {
      detail: { device },
      bubbles: true,
      composed: true,
    }));
  }

  _dispatchMoveDevice(name, direction) {
    this.dispatchEvent(new CustomEvent("move-device", {
      detail: { name, direction },
      bubbles: true,
      composed: true,
    }));
  }



  /* ── add device ──────────────────────────────────────────────────── */

  _onAddDevice() {
    const name = (this._newDeviceName || "").trim();
    if (!name) {
      this._addError = "Device name is required";
      this.requestUpdate();
      return;
    }
    if (this.devices[name]) {
      this._addError = `Device "${name}" already exists`;
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

  /* ── discover ────────────────────────────────────────────────────────── */

  async _onDiscover() {
    if (this._discovering || !this.entryId || !this.hass) return;
    this._discovering = true;
    this._discoveredDevices = [];
    this.requestUpdate();

    try {
      const resp = await this.hass.fetchWithAuth(
        `/api/nspanel_haui/discover/${this.entryId}`
      );
      if (resp.ok) {
        const result = await resp.json();
        this._discoveredDevices = (result.devices || []).filter((d) => !d.configured);
      } else {
        this._discoveredDevices = [];
      }
    } catch (_e) {
      this._discoveredDevices = [];
    } finally {
      this._discovering = false;
      this.requestUpdate();
    }
  }

  _onAddDiscovered(device) {
    this._dispatchAddDevice({
      name: device.name,
      esphome_device_id: device.esphome_device_id || "",
    });
    this._discoveredDevices = this._discoveredDevices.filter(d => d.name !== device.name);
    this.requestUpdate();
  }

  /* ── remove ──────────────────────────────────────────────────────────── */

  _onRemoveDevice(name) {
    this._dispatchRemoveDevice(name);
  }
}

customElements.define("ha-dialog-device-manager", DeviceManagerDialog);
export { DeviceManagerDialog };
