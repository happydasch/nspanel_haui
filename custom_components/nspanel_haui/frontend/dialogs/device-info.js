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
import { renderSelect } from '../form-fields.js';
import * as Toast from '../toast.js';

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

function renderDeviceInfoSection(
  ds,
  di,
  actions,
  firmwareDownloadVersion,
  firmwareDownloadLoading,
  firmwareDownloadError,
) {
  const esph = ds.esphome;
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
          <div class="di-info-cell">
            <span class="di-info-label">${t('Firmware Update Version')}</span>
            <span class="di-info-value di-mono">${(ds.update || {}).firmware_update_version || "-"}</span>
          </div>
          ${ds.update?.enabled !== false ? html`
            <div class="di-info-cell">
              <span class="di-info-label">${t('Firmware download version')}</span>
              <span class="di-info-value di-mono" title=${firmwareDownloadError || firmwareDownloadVersion || ""}>
                ${firmwareDownloadLoading
                  ? t('Loading releases…')
                  : firmwareDownloadError || firmwareDownloadVersion || t('Unavailable')}
              </span>
            </div>
          ` : ""}
          ${esph ? html`
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
          ` : ""}
        </div>
        ${actions ? html`
          <div class="di-device-actions">${actions}</div>
        ` : ""}
      </div>
    </details>
  `;
}

/* ── health section (Panel Doctor) ─────────────────────────────── */

function renderHealthSection(ds, di, healthActions) {
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
            <span class="di-info-label">${t("HAUI Version")}</span>
            <span class="di-info-value di-mono">${ds.haui_version || "-"}</span>
          </div>
          ${ds.haui_version_mismatch === true ? html`
          <div class="di-info-cell di-info-error">
            <span class="di-info-label">${t("Firmware version")}</span>
            <span class="di-info-value">${t("Firmware and HAUI versions do not match")}</span>
          </div>
          ` : ""}
          <div class="di-info-cell">
            <span class="di-info-label">${t("Connection Uptime")}</span>
            <span class="di-info-value">${uptime != null ? fmtInterval(uptime) : "—"}</span>
          </div>
          <div class="di-info-cell">
            <span class="di-info-label">${t("Page Mode")}</span>
            <span class="di-info-value">${idlePage ? t("Idle page") : t("Regular page")}</span>
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
        ${healthActions ? html`<div class="di-health-actions">${healthActions}</div>` : ""}
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
      deviceName: { type: String },
      entryId: { type: String },
      api: { type: Object },
      _picker: { type: Object, state: true },
      _firmwareDownloadUrl: { type: String, state: true },
      _firmwareDownloadVersion: { type: String, state: true },
      _firmwareDownloadLoading: { type: Boolean, state: true },
      _firmwareDownloadError: { type: String, state: true },
      _actionBusy: { type: Boolean, state: true },
      _toast: { type: Object, state: true },
    };
  }

  constructor() {
    super();
    this.deviceStatus = null;
    this.deviceName = null;
    this.entryId = null;
    this._picker = null;
    this._firmwareDownloadUrl = null;
    this._firmwareDownloadVersion = null;
    this._firmwareDownloadLoading = false;
    this._firmwareDownloadError = null;
    this._actionBusy = false;
    this._toast = null;
  }

  updated(changed) {
    if (changed.has("open") && this.open) {
      this.renderRoot.querySelectorAll("details.config-section").forEach((d) => {
        d.removeAttribute("open");
      });
      this._loadFirmwareDownloadInfo();
    } else if (changed.has("open") && !this.open) {
      this._picker = null;
    }
  }

  async _loadFirmwareDownloadInfo() {
    if (this.deviceStatus?.update?.enabled === false || !this.entryId || !this.api) return;
    this._firmwareDownloadUrl = null;
    this._firmwareDownloadVersion = null;
    this._firmwareDownloadError = null;
    this._firmwareDownloadLoading = true;
    try {
      const { url, version } = await this.api.updates.firmwareDownload();
      this._firmwareDownloadUrl = url;
      this._firmwareDownloadVersion = url ? version : null;
      if (!url) {
        this._firmwareDownloadError = t("No prebuilt firmware binary published for this release. Build from YAML or use the ESPHome dashboard.");
      }
    } catch (err) {
      this._firmwareDownloadError = err.message || t("Failed to load the firmware link");
    } finally {
      this._firmwareDownloadLoading = false;
    }
  }

  async _refreshDisplay() {
    if (!this.deviceName || this._actionBusy) return;
    this._actionBusy = true;
    try {
      await this.api.devices.refreshDisplay(this.entryId, this.deviceName);
      Toast.showToast(
        this,
        t('Display refreshed for "{name}"').replace('{name}', this.deviceName),
        "success",
      );
    } catch (err) {
      Toast.showToast(this, err.message || t("Failed to refresh display"), "error");
    } finally {
      this._actionBusy = false;
    }
  }

  async _resetInteractionTimer() {
    if (!this.deviceName || this._actionBusy) return;
    this._actionBusy = true;
    try {
      await this.api.devices.resetInteraction(this.entryId, this.deviceName);
      Toast.showToast(this, t("Interaction timer reset"), "success");
    } catch (err) {
      Toast.showToast(this, err.message || t("Failed to reset interaction timer"), "error");
    } finally {
      this._actionBusy = false;
    }
  }

  async _downloadFirmware() {
    if (this._actionBusy || this.deviceStatus?.update?.enabled === false) return;
    this._actionBusy = true;
    try {
      const download = this._firmwareDownloadUrl
        ? { url: this._firmwareDownloadUrl, version: this._firmwareDownloadVersion }
        : await this.api.updates.firmwareDownload();
      const { url, version } = download;
      if (!url) {
        Toast.showToast(
          this,
          t("No prebuilt firmware binary published for this release. Build from YAML or use the ESPHome dashboard."),
          "error",
        );
        return;
      }
      this._firmwareDownloadUrl = url;
      this._firmwareDownloadVersion = version || null;
      this._firmwareDownloadError = null;
      window.open(url, "_blank");
      Toast.showToast(
        this,
        version
          ? t('Downloading firmware {version}').replace('{version}', version)
          : t('Downloading firmware'),
        "success",
      );
    } catch (err) {
      Toast.showToast(this, err.message || t("Failed to load the firmware link"), "error");
    } finally {
      this._actionBusy = false;
    }
  }

  /* ── TFT / firmware install picker ────────────────────────────────── */

  async _openPicker(kind, name, choice = "") {
    if (this.deviceStatus?.update?.enabled === false) return;
    if (kind === "select") {
      this._picker = { kind, device: name };
      return;
    }
    this._picker = { kind, device: name, releases: null, releasesError: "", choice, url: "", file: null, error: "" };
    const load = kind === "tft"
      ? () => this.api.updates.tftReleases(this.entryId, name)
      : () => this.api.updates.firmwareReleases(this.entryId, name);
    let result;
    try {
      result = await load();
    } catch (e) {
      result = {
        releases: [],
        error: e.message || (kind === "tft" ? t('Failed to load the TFT releases') : t('Failed to load the firmware releases')),
      };
    }
    // The picker may have been closed or opened for another install meanwhile.
    if (this._picker?.kind !== kind || this._picker.device !== name) return;
    const releases = result.releases;
    const pending = this._picker.choice === null;
    const required = result.required;
    const tftNeedsExplicitChoice = kind === "tft"
      && this._picker.choice === ""
      && (!required || releases.length === 0);
    const defaultChoice = pending || tftNeedsExplicitChoice
      ? (releases[0] ?? "url")
      : this._picker.choice;
    this._picker = {
      ...this._picker,
      releases,
      releasesError: result.error || "",
      choice: defaultChoice,
    };
  }

  _updatePicker(changes) { this._picker = { ...this._picker, ...changes }; }

  _finishLocalUpload(error = "") {
    if (!this._picker?.uploading) return;
    this._picker = error ? { ...this._picker, uploading: false, error } : null;
  }

  _installFromPicker() {
    const { kind, device: name, choice } = this._picker;
    if (this.deviceStatus?.update?.enabled === false) return;
    if (choice === null) return;
    const event = kind === "tft" ? "update-tft" : "update-firmware";
    if (choice === "url") {
      const url = this._picker.url.trim();
      if (!/^https?:\/\/\S+$/i.test(url)) {
        this._updatePicker({
          error: kind === "tft"
            ? t('Enter the http(s) URL of a .tft file')
            : t('Enter the http(s) URL of a firmware OTA image (.bin)'),
        });
        return;
      }
      this._emit(event, { name, url });
    } else if (choice === "file") {
      const file = this._picker.file;
      if (!file) {
        this._updatePicker({ error: t("Choose a local update file") });
        return;
      }
      const extension = kind === "tft" ? ".tft" : ".bin";
      if (!file.name.toLowerCase().endsWith(extension)) {
        this._updatePicker({
          error: kind === "tft"
            ? t("Choose a Nextion TFT file (.tft)")
            : t("Choose an ESPHome OTA image (.bin)"),
        });
        return;
      }
      this._updatePicker({ uploading: true, error: "" });
      this._emit(event, { name, file });
      return;
    } else if (choice) {
      this._emit(event, { name, version: choice });
    } else {
      this._emit(event, { name });
    }
    this._picker = null;
  }

  _renderPicker(name, required, updateStatus) {
    if (updateStatus?.enabled === false) {
      return html`<div class="device-update-picker">${t('Updates are disabled for this device.')}</div>`;
    }
    const { kind, releases, releasesError, choice, url, file, error, uploading } = this._picker;
    if (kind === "select") {
      return html`
        <div class="device-update-picker device-update-picker" @click=${(e) => e.stopPropagation()}>
          <div class="form-group">
            <label>${t('Choose update type')}</label>
            <div class="device-update-actions">
              <ha-button variant="neutral" appearance="plain" @click=${() => { this._picker = null; }}>
                ${t('Cancel')}
              </ha-button>
              <ha-button @click=${() => this._openPicker("tft", name)}>${t('Display (TFT)')}</ha-button>
              <ha-button
                ?disabled=${updateStatus?.firmware_installing}
                @click=${() => this._openPicker("firmware", name, updateStatus?.firmware_update_available ? "" : null)}
              >${t('Firmware')}</ha-button>
            </div>
          </div>
        </div>
      `;
    }
    const tft = kind === "tft";
    let defaults = [];
    if (tft) {
      defaults = [["", required
        ? t('Version the firmware needs ({version})').replace('{version}', required)
        : t('Version the firmware needs')]];
    } else if (updateStatus?.firmware_update_available) {
      defaults = [["", t('Offered update ({version})').replace('{version}', updateStatus.firmware_update_version || '')]];
    }
    // The manifest's TFT is normally the required one, which the default
    // already installs; list it only when it differs.
    const listed = (releases || []).filter((tag) => !(tft && required && tag === required));
    const options = [
      ...defaults,
      ...listed.map((tag) => [tag, tag]),
      ["url", t('From URL')],
      ["file", t('From local file')],
    ];
    return html`
      <div class="device-update-picker device-update-picker" @click=${(e) => e.stopPropagation()}>
        <div class="form-group">
          <label for="di-install-source">${tft ? t('TFT to install') : t('Firmware to install')}</label>
          ${renderSelect(
            "di-install-source",
            choice,
            options,
            (value) => this._updatePicker({ choice: value, file: null, error: "" }),
            { disabled: uploading },
          )}
          ${releases === null ? html`<div class="field-hint">${t('Loading releases\u2026')}</div>` : ''}
          ${releasesError
            ? html`<div class="field-hint">${t('Releases unavailable: {error}').replace('{error}', releasesError)}</div>`
            : ''}
        </div>
        ${choice === "url" ? html`
          <div class="form-group">
            <label for="di-install-url">${tft ? t('TFT file URL') : t('Firmware OTA image URL')}</label>
            <input
              id="di-install-url"
              class="native-input"
              type="url"
              .value=${url}
              @input=${(e) => this._updatePicker({ url: e.target.value, error: "" })}
            />
          </div>
        ` : ''}
        ${choice === "file" ? html`
          <div class="form-group">
            <label for="di-install-file">${tft ? t('Local TFT file') : t('Local firmware OTA image')}</label>
            <input
              id="di-install-file"
              class="native-input"
              type="file"
              accept=${tft ? ".tft" : ".bin"}
              ?disabled=${uploading}
              @change=${(e) => this._updatePicker({ file: e.target.files?.[0] || null, error: "" })}
            />
            <div class="field-hint">
              ${t('The file is uploaded to Home Assistant and must be reachable by the device.')}
            </div>
          </div>
        ` : ''}
        ${uploading ? html`<div class="field-hint">${t('Uploading local update file…')}</div>` : ''}
        <div class="field-hint">${tft
          ? t('Another release, URL or local file stays on the display until the firmware version changes or Home Assistant restarts.')
          : t('Another release, URL or local file pauses automatic firmware updates until Home Assistant restarts. Use the OTA image (nspanel_haui_ota.bin), not the factory image.')}</div>
        ${error ? html`<p class="device-update-error">${error}</p>` : ''}
        <div class="device-update-actions">
          <ha-button
            variant="neutral"
            appearance="plain"
            ?disabled=${uploading}
            @click=${() => { this._picker = null; }}
          >
            ${t('Cancel')}
          </ha-button>
          <ha-button
            ?disabled=${uploading || choice === null || (choice === "file" && !file)}
            @click=${() => this._installFromPicker()}
          >
            ${uploading ? t('Uploading…') : t('Install')}
          </ha-button>
        </div>
      </div>
    `;
  }

  render() {
    const ds = this.deviceStatus;
    if (!ds) return "";

    const di = ds.device_info || {};
    const nw = di;
    const update = ds.update || {};
    const updatesEnabled = update.enabled !== false;
    const installing = update.firmware_installing || update.state === "checking" || update.state === "installing";
    const requiredTft = di.tft_required_version;
    const healthActions = html`
      <ha-button
        variant="neutral"
        appearance="plain"
        ?disabled=${this._actionBusy || !this.deviceName}
        @click=${this._resetInteractionTimer}
      >${t('Reset interaction timer')}</ha-button>
      <ha-button
        variant="neutral"
        appearance="plain"
        ?disabled=${this._actionBusy || !this.deviceName}
        @click=${this._refreshDisplay}
      >${t('Redraw display')}</ha-button>
    `;
    const deviceActions = updatesEnabled ? html`
      <ha-button
        variant="neutral"
        appearance="plain"
        ?disabled=${this._actionBusy || !this.deviceName || installing}
        @click=${() => this._openPicker("select", this.deviceName)}
      >${t('Install update')}</ha-button>
      <ha-button
        variant="neutral"
        appearance="plain"
        ?disabled=${this._actionBusy || this._firmwareDownloadLoading}
        @click=${this._downloadFirmware}
      >${t('Download firmware')}</ha-button>
    ` : "";

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        >
        ${dialogHeader(t('Device Info'), this._dispatchClose)}

        <div class="dialog-body">
          ${Toast.renderToast(this)}
          ${renderStatusCard(ds, di, nw)}
          ${renderDeviceInfoSection(
            ds,
            di,
            deviceActions,
            this._firmwareDownloadVersion,
            this._firmwareDownloadLoading,
            this._firmwareDownloadError,
          )}
          ${this._picker ? this._renderPicker(this.deviceName, requiredTft, update) : ''}
          ${renderHealthSection(ds, di, healthActions)}
          ${renderWifiSection(di, nw)}
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