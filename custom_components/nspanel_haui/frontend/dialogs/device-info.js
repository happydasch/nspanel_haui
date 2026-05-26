/**
 * NSPanel HAUI - Editor - Device Info dialog.
 *
 * Proper Lit custom element replacing the old renderDeviceInfoDialog() function.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { t } from '../localize.js';

/* ── timestamp formatting ─────────────────────────────────────────── */

function fmtTimestamp(isoString) {
  if (!isoString) return "-";
  try {
    const then = new Date(isoString);
    if (isNaN(then.getTime())) return "-";
    const now = new Date();
    const diffSec = Math.floor((now - then) / 1000);

    if (diffSec < 0) return then.toLocaleString();

    if (diffSec < 60) return t('Just now');
    if (diffSec < 3600) {
      const m = Math.floor(diffSec / 60);
      return `${m} ${t('minute(s) ago')}`;
    }
    if (diffSec < 86400) {
      const h = Math.floor(diffSec / 3600);
      return `${h} ${t('hour(s) ago')}`;
    }
    if (diffSec < 604800) {
      const d = Math.floor(diffSec / 86400);
      return `${d} ${t('day(s) ago')}`;
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
      <h4>${t('Active Timers')} (${count})</h4>
      <p class="empty-state-text">${t('No active timers.')}</p>
    </div>`;
  }

  return html`
    <div class="active-timers-section">
      <h4>${t('Active Timers')} (${count})</h4>
      <div class="timers-table">
        <div class="timers-header">
          <span class="timers-col timers-col-cb">${t('Callback')}</span>
          <span class="timers-col timers-col-type">${t('Type')}</span>
          <span class="timers-col timers-col-int">${t('Interval')}</span>
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
      <h4>${t('Active Listeners')} (${count})</h4>
      <p class="empty-state-text">${t('No active listeners.')}</p>
    </div>`;
  }

  return html`
    <div class="active-listeners-section">
      <h4>${t('Active Listeners')} (${count})</h4>
      <div class="listeners-table">
        <div class="listeners-header">
          <span class="listeners-col listeners-col-entity">${t('Entity')}</span>
          <span class="listeners-col listeners-col-attr">${t('Attribute')}</span>
          <span class="listeners-col listeners-col-cb">${t('Callback')}</span>
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
        .preventScrimClose=${true}
        header-title=${t('Device Info')}
      >

        <div class="dialog-body">
          <div class="info-grid-2col">
            <div>
              <strong>${t('Device:')}</strong> ${di.name || "-"}
            </div>
            <div>
              <strong>${t('Connection:')}</strong>
              ${ds.connected ? t('Connected') : t('Disconnected')}
              <span class="text-secondary">(${ds.connection_state || t('unknown')})</span>
            </div>
            <div>
              <strong>${t('Current Page:')}</strong> ${ds.current_page || "-"}
            </div>
            <div>
              <strong>${t('YAML Version:')}</strong> ${di.yaml_version || "-"}
            </div>
            <div>
              <strong>${t('TFT Version:')}</strong> ${di.tft_version || "-"}
            </div>
            <div>
              <strong>${t('Last Connection:')}</strong> ${fmtTimestamp(di.last_connection)}
            </div>
            <div>
              <strong>${t('Last Panel Update:')}</strong> ${fmtTimestamp(di.last_panel_update)}
            </div>
          </div>

          ${renderActiveListeners(ds)}
          ${renderActiveTimers(ds)}
        </div>

        <ha-dialog-footer slot="footer">
          <ha-button slot="primaryAction" @click=${this._dispatchClose}>
            ${t('Close')}
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