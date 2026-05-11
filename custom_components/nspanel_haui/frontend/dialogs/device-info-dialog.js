/**
 * NSPanel HAUI - Editor - Device Info dialog.
 *
 * Proper Lit custom element replacing the old renderDeviceInfoDialog() function.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';

/* ── timestamp formatting ─────────────────────────────────────────── */

function fmtTimestamp(isoString) {
  if (!isoString) return "-";
  try {
    const then = new Date(isoString);
    if (isNaN(then.getTime())) return "-";
    const now = new Date();
    const diffSec = Math.floor((now - then) / 1000);

    if (diffSec < 0) return then.toLocaleString();

    if (diffSec < 60) return "Just now";
    if (diffSec < 3600) {
      const m = Math.floor(diffSec / 60);
      return `${m} minute${m === 1 ? "" : "s"} ago`;
    }
    if (diffSec < 86400) {
      const h = Math.floor(diffSec / 3600);
      return `${h} hour${h === 1 ? "" : "s"} ago`;
    }
    if (diffSec < 604800) {
      const d = Math.floor(diffSec / 86400);
      return `${d} day${d === 1 ? "" : "s"} ago`;
    }
    return then.toLocaleString();
  } catch {
    return "-";
  }
}

function fmtInterval(seconds) {
  if (seconds == null) return "-";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${+(seconds / 3600).toFixed(1)}h`;
}

/* ── sub-sections ─────────────────────────────────────────────────── */

function renderActiveTimers(ds) {
  const timers = ds.active_timers;
  const count = ds.active_timer_count ?? 0;

  if (!timers || timers.length === 0) {
    return html`<div class="active-timers-section">
      <h4>Active Timers (${count})</h4>
      <p style="color:var(--secondary-text-color,#666);font-style:italic;">No active timers.</p>
    </div>`;
  }

  return html`
    <div class="active-timers-section">
      <h4>Active Timers (${count})</h4>
      <div class="timers-table">
        <div class="timers-header">
          <span class="timers-col timers-col-cb">Callback</span>
          <span class="timers-col timers-col-type">Type</span>
          <span class="timers-col timers-col-int">Interval</span>
        </div>
        ${timers.map(t => html`
          <div class="timers-row">
            <span class="timers-col timers-col-cb" title="${t.callback_name}">${t.callback_name}</span>
            <span class="timers-col timers-col-type">${t.type}</span>
            <span class="timers-col timers-col-int">${fmtInterval(t.interval)}</span>
          </div>
        `)}
      </div>
    </div>
  `;
}

function renderActiveListeners(ds) {
  const listeners = ds.active_listeners;
  const count = ds.active_listener_count ?? 0;

  if (!listeners || listeners.length === 0) {
    return html`<div class="active-listeners-section">
      <h4>Active Listeners (${count})</h4>
      <p style="color:var(--secondary-text-color,#666);font-style:italic;">No active listeners.</p>
    </div>`;
  }

  return html`
    <div class="active-listeners-section">
      <h4>Active Listeners (${count})</h4>
      <div class="listeners-table">
        <div class="listeners-header">
          <span class="listeners-col listeners-col-entity">Entity</span>
          <span class="listeners-col listeners-col-attr">Attribute</span>
          <span class="listeners-col listeners-col-cb">Callback</span>
        </div>
        ${listeners.map(l => html`
          <div class="listeners-row">
            <span class="listeners-col listeners-col-entity" title="${l.item_id}">${l.item_id}</span>
            <span class="listeners-col listeners-col-attr">${l.attribute || "-"}</span>
            <span class="listeners-col listeners-col-cb" title="${l.callback_name}">${l.callback_name}</span>
          </div>
        `)}
      </div>
    </div>
  `;
}

/* ── dialog component ─────────────────────────────────────────────── */

class DeviceInfoDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      deviceStatus: { type: Object },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
    this.deviceStatus = null;
  }

  render() {
    const ds = this.deviceStatus;
    if (!ds) return "";

    const di = ds.device_info || {};

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title="Device Info"
      >

        <div class="dialog-body">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div>
              <strong>Device:</strong> ${di.friendly_name || "-"}
            </div>
            <div>
              <strong>Connection:</strong>
              ${ds.connected ? "Connected" : "Disconnected"}
              <span style="color:var(--secondary-text-color,#666);">(${ds.connection_state || "unknown"})</span>
            </div>
            <div>
              <strong>Current Page:</strong> ${ds.current_page || "-"}
            </div>
            <div>
              <strong>Render Count:</strong> ${ds.render_count ?? "-"}
            </div>
            <div>
              <strong>YAML Version:</strong> ${di.yaml_version || "-"}
            </div>
            <div>
              <strong>TFT Version:</strong> ${di.tft_version || "-"}
            </div>
            <div>
              <strong>Last Connection:</strong> ${fmtTimestamp(di.last_connection)}
            </div>
            <div>
              <strong>Last Panel Update:</strong> ${fmtTimestamp(di.last_panel_update)}
            </div>
          </div>

          ${renderActiveListeners(ds)}
          ${renderActiveTimers(ds)}
        </div>

        <ha-dialog-footer slot="footer">
          <ha-button slot="primaryAction" appearance="plain" @click=${this._dispatchClose}>
            Close
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }
}

customElements.define("ha-dialog-device-info", DeviceInfoDialog);
export { DeviceInfoDialog };