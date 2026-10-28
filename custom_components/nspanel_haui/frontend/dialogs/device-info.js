/**
 * NSPanel HAUI - Device Info dialog.
 *
 * Proper Lit custom element. Shows device connection state, firmware info,
 * WiFi signal, active listeners/timers, and ESPHome transport details.
 */
import { html } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';
import { rssiStrengthClass, rssiBarCount, fmtRssi } from '../device-info.js';

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
      return t('{count} minute(s) ago').replace('{count}', m);
    }
    if (diffSec < 86400) {
      const h = Math.floor(diffSec / 3600);
      return t('{count} hour(s) ago').replace('{count}', h);
    }
    if (diffSec < 604800) {
      const d = Math.floor(diffSec / 86400);
      return t('{count} day(s) ago').replace('{count}', d);
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

/* ── health section (Panel Doctor) ─────────────────────────────── */

function renderHealthSection(ds, di) {
  const connected = ds.connected === true;
  const uptime = connected && di.connection_uptime != null ? di.connection_uptime : null;
  const reason = di.last_disconnect_reason;
  const offlineSince = di.disconnected_since;
  const idlePage = di.idle_page_active === true;
  const update = ds.update || {};
  const updateLabels = {
    checking: t('Checking for update\u2026'),
    installing: t('Installing TFT\u2026'),
    done: t('TFT installed'),
    error: t('TFT update failed'),
  };
  const updateLabel = updateLabels[update.state] || (update.state && update.state !== "idle" ? update.state : "");

  return html`
    <details class="config-section">
      <summary>
        <ha-icon icon="mdi:heart-pulse" class="di-section-icon"></ha-icon>
        ${t("Health")}
      </summary>
      <div class="config-section-body">
        <div class="di-info-grid">
          <div class="di-info-cell">
            <span class="di-info-label">${t("Integration Version")}</span>
            <span class="di-info-value di-mono">${ds.integration_version || "-"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t("Connection Uptime")}</span>
            <span class="di-info-value">${uptime != null ? fmtInterval(uptime) : "—"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t("State")}</span>
            <span class="di-info-value">${idlePage ? t("Idle page") : t("Active")}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t("Last Disconnect")}</span>
            <span class="di-info-value" title=${reason || "—"}>
              ${reason ? `${reason}${offlineSince ? ` · ${fmtTimestamp(offlineSince)}` : ""}` : "—"}
            </span>
          </div>
          ${updateLabel ? html`
          <div class="di-info-cell${update.state === "error" ? ' di-info-error' : ''}">
            <span class="di-info-label">${t("TFT Update")}</span>
            <span class="di-info-value" title=${update.last_error || updateLabel}>
              ${update.version ? `${updateLabel} · ${update.version}` : updateLabel}
            </span>
          </div>
          ` : ""}
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

class DeviceInfoDialog extends HauiDialog {
  static get properties() {
    return {
      deviceStatus: { type: Object },
    };
  }

  constructor() {
    super();
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
    const nw = di;

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        >
        ${dialogHeader(t('Device Info'), this._dispatchClose)}

        <div class="dialog-body">
          ${renderStatusCard(ds, di, nw)}
          ${renderDeviceInfoSection(ds, di)}
          ${renderHealthSection(ds, di)}
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
}

customElements.define("nspanel-dialog-device-info", DeviceInfoDialog);
export { DeviceInfoDialog, renderHealthSection };