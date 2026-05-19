/**
 * NSPanel HAUI - Editor - device info strip and polling.
 *
 * Contains only:
 *   - startStatusPolling / stopStatusPolling
 *   - renderDeviceInfoStrip (always-visible inline strip)
 *
 * Device Info dialog and Logs dialog are now separate custom elements:
 *   - ha-dialog-device-info  (in dialogs/device-info.js)
 *   - ha-dialog-logs         (in dialogs/logs.js)
 */
import { html } from './lit-import.js';
import * as Api from './api.js';

/* ── status polling ──────────────────────────────────────────────────────── */

export function startStatusPolling(host) {
  if (host._statusTimer) return;
  Api.loadStatus(host);
  host._statusTimer = setInterval(() => Api.loadStatus(host), 5000);
}

export function stopStatusPolling(host) {
  if (host._statusTimer) {
    clearInterval(host._statusTimer);
    host._statusTimer = null;
  }
}

/* ── info strip ──────────────────────────────────────────────────────────── */

export function renderDeviceInfoStrip(host) {
  const ds = host._deviceStatus;
  const err = host._deviceStatusError;

  // Connection indicator with color coding
  const connected = ds?.connected;
  const connState = ds?.connection_state || "unknown";

  let dotClass, label;
  if (connected === true) {
    dotClass = "dot-connected";
    label = "Connected";
  } else if (connState === "handshaking") {
    dotClass = "dot-handshaking";
    label = "Handshaking…";
  } else if (connState === "disconnected") {
    dotClass = "dot-disconnected";
    label = "Disconnected";
  } else {
    dotClass = "dot-unknown";
    label = "Unknown";
  }

  // Current page
  const currentPage = ds?.current_page || "-";

  return html`
    <div class="device-info-strip">
      <span class="info-strip-item connection-indicator" title="Connection: ${connState}">
        <span class="connection-indicator-dot ${dotClass}"></span>
        ${label}
      </span>
      <span class="info-strip-item" title="Current page: ${currentPage}">
        ${currentPage}
      </span>
      ${err ? html`<span class="info-strip-item" style="color:var(--error-color,#f44336);">${err}</span>` : ""}
    </div>
  `;
}
