/**
 * NSPanel HAUI - Editor - device polling and connection state helpers.
 *
 * Contains only:
 *   - startStatusPolling / stopStatusPolling
 *   - getConnectionStateClass / getConnectionStateLabel (shared helpers)
 *
 * Device Info dialog and Logs dialog are now separate custom elements:
 *   - ha-dialog-device-info  (in dialogs/device-info.js)
 *   - ha-dialog-logs         (in dialogs/logs.js)
 */
import * as Api from './api.js';
import { t } from './localize.js';

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

/* ── connection state helpers ──────────────────────────────────────────── */

/**
 * Map (connected, connState) to a CSS dot class for the connection indicator.
 * @param {boolean|undefined} connected
 * @param {string} [connState="unknown"]
 * @returns {string} CSS class name
 */
export function getConnectionStateClass(connected, connState) {
  if (connected === true) return "dot-connected";
  if (connState === "handshaking") return "dot-handshaking";
  if (connState === "disconnected") return "dot-disconnected";
  return "dot-unknown";
}

/**
 * Map (connected, connState) to a human-readable label.
 * @param {function} t - translation function
 * @param {boolean|undefined} connected
 * @param {string} [connState="unknown"]
 * @returns {string} translated label
 */
export function getConnectionStateLabel(t, connected, connState) {
  if (connected === true) return t('Connected');
  if (connState === "handshaking") return t('Handshaking\u2026');
  if (connState === "disconnected") return t('Disconnected');
  return t('Unknown');
}
