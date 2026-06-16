/**
 * NSPanel HAUI - Editor - Device Info dialog.
 *
 * Proper Lit custom element. Shows device connection state, firmware info,
 * WiFi signal, active listeners/timers, and ESPHome transport details.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { dialogHeader } from './dialog-header.js';
import { t } from '../localize.js';
import { readNetworkInfo, rssiStrengthClass, rssiBarCount, fmtRssi } from '../network-info.js';

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

/* ── connection status card ─────────────────────────────────────── */

function renderStatusCard(ds, di, nw) {
  const connected = ds.connected === true;
  const stateCls = connected ? "connected" : "disconnected";
  const stateLabel = connected ? t('Connected') : t('Disconnected');
  const connDetail = ds.connection_state || t('unknown');
  const ip = (nw && nw.ip) ? nw.ip : null;

  return html`
    <div class="di-status-card ${stateCls}">
      <div class="di-status-left">
        <div class="di-status-icon-wrapper">
          <ha-icon
            class="di-status-icon"
            icon=${connected ? "mdi:check-circle" : "mdi:alert-circle-outline"}
          ></ha-icon>
        </div>
        <div class="di-status-text">
          <span class="di-status-label">${stateLabel}</span>
          <span class="di-status-detail">${connDetail}</span>
        </div>
      </div>
      <div class="di-status-meta">
        ${ip ? html`
          <span class="di-status-meta-item" title=${ip}>
            <ha-icon icon="mdi:ip-network" class="di-meta-icon"></ha-icon>
            ${ip}
          </span>
        ` : ""}
        ${di.last_connection ? html`
          <span class="di-status-meta-item" title=${di.last_connection}>
            <ha-icon icon="mdi:clock-outline" class="di-meta-icon"></ha-icon>
            ${fmtTimestamp(di.last_connection)}
          </span>
        ` : ""}
        ${di.last_panel_update ? html`
          <span class="di-status-meta-item" title="${t('Last Panel Update')}: ${di.last_panel_update}">
            <ha-icon icon="mdi:update" class="di-meta-icon"></ha-icon>
            ${fmtTimestamp(di.last_panel_update)}
          </span>
        ` : ""}
      </div>
    </div>
  `;
}

/* ── device info section ────────────────────────────────────────── */

function renderDeviceInfoSection(ds, di) {
  return html`
    <details class="config-section">
      <summary>
        <ha-icon icon="mdi:information-outline" class="di-section-icon"></ha-icon>
        ${t('Device')}
      </summary>
      <div class="config-section-body">
        <div class="di-info-grid">
          <div class="di-info-cell">
            <span class="di-info-label">${t('Name')}</span>
            <span class="di-info-value">${di.name || "-"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t('Current Page')}</span>
            <span class="di-info-value">${ds.current_page || "-"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t('YAML Version')}</span>
            <span class="di-info-value di-mono">${di.yaml_version || "-"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t('TFT Version')}</span>
            <span class="di-info-value di-mono">${di.tft_version || "-"}</span>
          </div>
        </div>
      </div>
    </details>
  `;
}

/* ── WiFi section ──────────────────────────────────────────────── */

function renderWifiSection(di, nw) {
  const rssi = (nw && nw.rssi != null) ? nw.rssi : null;
  const ssid = (nw && nw.ssid) ? nw.ssid : null;
  const ip = (nw && nw.ip) ? nw.ip : null;
  const cls = rssiStrengthClass(rssi);
  const bars = rssiBarCount(rssi);

  return html`
    <details class="config-section">
      <summary>
        <ha-icon icon="mdi:wifi" class="di-section-icon ${cls}"></ha-icon>
        ${t('WiFi')}
      </summary>
      <div class="config-section-body">
        <div class="di-info-grid">
          <div class="di-info-cell">
            <span class="di-info-label">${t('SSID')}</span>
            <span class="di-info-value">${ssid || "—"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t('IP Address')}</span>
            <span class="di-info-value di-mono">${ip || "—"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t('Signal')}</span>
            <span class="di-info-value">
              <span class="rssi-bars" title=${fmtRssi(rssi)}>
                <span class="rssi-bar ${bars >= 1 ? cls : ''}"></span>
                <span class="rssi-bar ${bars >= 2 ? cls : ''}"></span>
                <span class="rssi-bar ${bars >= 3 ? cls : ''}"></span>
                <span class="rssi-bar ${bars >= 4 ? cls : ''}"></span>
              </span>
              <span class="di-rssi-text">${fmtRssi(rssi)}</span>
            </span>
          </div>
        </div>
      </div>
    </details>
  `;
}

/* ── ESPHome transport section ──────────────────────────────────── */

function renderEsphomeSection(ds) {
  const esph = ds.esphome;
  if (!esph) return "";

  return html`
    <details class="config-section">
      <summary>
        <ha-icon icon="mdi:devices" class="di-section-icon"></ha-icon>
        ${t('ESPHome')}
      </summary>
      <div class="config-section-body">
        <div class="di-info-grid">
          <div class="di-info-cell">
            <span class="di-info-label">${t('Transport')}</span>
            <span class="di-info-value di-mono">${esph.transport || "-"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t('Device Names')}</span>
            <span class="di-info-value">
              ${(esph.device_names || []).join(", ") || "-"}
            </span>
          </div>
        </div>
      </div>
    </details>
  `;
}

/* ── active listeners table ─────────────────────────────────────── */

function renderActiveListeners(ds) {
  const listeners = ds.active_listeners;
  const count = ds.active_listener_count ?? 0;

  return html`
    <details class="config-section">
      <summary>
        <ha-icon icon="mdi:ear-hearing" class="di-section-icon"></ha-icon>
        ${t('Listeners')} (${count})
      </summary>
      <div class="config-section-body">
        ${!listeners || listeners.length === 0 ? html`
          <p class="empty-state-text">${t('No active listeners.')}</p>
        ` : html`
          <div class="di-table">
            <div class="di-table-row di-table-header">
              <span class="di-table-cell di-table-cell-entity">${t('Entity')}</span>
              <span class="di-table-cell di-table-cell-attr">${t('Attribute')}</span>
              <span class="di-table-cell di-table-cell-cb">${t('Callback')}</span>
            </div>
            ${listeners.map(l => html`
              <div class="di-table-row">
                <span class="di-table-cell di-table-cell-entity" title="${l.item_id}">${l.item_id}</span>
                <span class="di-table-cell di-table-cell-attr">${l.attribute || "-"}</span>
                <span class="di-table-cell di-table-cell-cb di-mono" title="${l.callback_name}">${l.callback_name}</span>
              </div>
            `)}
          </div>
        `}
      </div>
    </details>
  `;
}

/* ── active timers table ──────────────────────────────────────── */

function renderActiveTimers(ds) {
  const timers = ds.active_timers;
  const count = ds.active_timer_count ?? 0;

  return html`
    <details class="config-section">
      <summary>
        <ha-icon icon="mdi:timer-outline" class="di-section-icon"></ha-icon>
        ${t('Timers')} (${count})
      </summary>
      <div class="config-section-body">
        ${!timers || timers.length === 0 ? html`
          <p class="empty-state-text">${t('No active timers.')}</p>
        ` : html`
          <div class="di-table">
            <div class="di-table-row di-table-header">
              <span class="di-table-cell di-table-cell-cb">${t('Callback')}</span>
              <span class="di-table-cell di-table-cell-type">${t('Type')}</span>
              <span class="di-table-cell di-table-cell-int">${t('Interval')}</span>
            </div>
            ${timers.map(t => html`
              <div class="di-table-row">
                <span class="di-table-cell di-table-cell-cb di-mono" title="${t.callback_name}">${t.callback_name}</span>
                <span class="di-table-cell di-table-cell-type">${t.type}</span>
                <span class="di-table-cell di-table-cell-int">${fmtInterval(t.interval)}</span>
              </div>
            `)}
          </div>
        `}
      </div>
    </details>
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

  updated(changed) {
    if (changed.has("open") && this.open) {
      this.renderRoot.querySelectorAll("details.config-section").forEach((d) => {
        d.removeAttribute("open");
      });
    }
  }

  render() {
    const ds = this.deviceStatus;
    if (!ds) return "";

    const di = ds.device_info || {};
    const deviceName = di.name || "";
    const nw = readNetworkInfo(this.hass, deviceName);

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        .preventScrimClose=${true}
      >
        ${dialogHeader(t('Device Info'), this._dispatchClose)}

        <div class="dialog-body">
          ${renderStatusCard(ds, di, nw)}
          ${renderDeviceInfoSection(ds, di)}
          ${renderWifiSection(di, nw)}
          ${renderEsphomeSection(ds)}
          ${renderActiveListeners(ds)}
          ${renderActiveTimers(ds)}
        </div>

        <div slot="footer" class="footer-wrapper">
          <ha-dialog-footer>
            <ha-button slot="primaryAction" @click=${this._dispatchClose}>
              ${t('Close')}
            </ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }
}

customElements.define("ha-dialog-device-info", DeviceInfoDialog);
export { DeviceInfoDialog };