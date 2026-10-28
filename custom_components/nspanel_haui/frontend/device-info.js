/**
 * NSPanel HAUI - device polling and connection state helpers.
 *
 * Contains only:
 *   - startStatusPolling / stopStatusPolling
 *   - getConnectionStateClass / getConnectionStateLabel (shared helpers)
 *
 * Device Info dialog and Logs dialog are now separate custom elements:
 *   - nspanel-dialog-device-info  (in dialogs/device-info.js)
 *   - nspanel-dialog-logs         (in dialogs/logs.js)
 */
import * as Api from './api.js';
import { t } from './localize.js';

/* ── status polling ──────────────────────────────────────────────────────── */

/**
 * Poll the selected device's status. Restarts when the selected device has
 * changed, dropping the previous device's status so it is never shown for the
 * new one.
 */
/**
 * Whether version ``a`` (e.g. "0.3.3") is older than ``b``. Missing or
 * non-numeric parts count as 0.
 *
 * @param {string} a
 * @param {string} b
 * @returns {boolean}
 */
export function isOlderVersion(a, b) {
  const pa = String(a).split(".").map((n) => parseInt(n, 10) || 0);
  const pb = String(b).split(".").map((n) => parseInt(n, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0);
    if (diff !== 0) return diff < 0;
  }
  return false;
}

function rssiValue(rssi) {
  if ((typeof rssi !== "number" && typeof rssi !== "string") || rssi === "") return null;
  const value = Number(rssi);
  return Number.isFinite(value) ? value : null;
}

function rssiLevel(rssi) {
  const value = rssiValue(rssi);
  if (value == null) return 0;
  if (value >= -50) return 4;
  if (value >= -60) return 3;
  if (value >= -70) return 2;
  return 1;
}

export function rssiStrengthClass(rssi) {
  const classes = ["wifi-unknown", "wifi-weak", "wifi-fair", "wifi-good", "wifi-excellent"];
  return classes[rssiLevel(rssi)];
}

export function rssiIcon(rssi) {
  const level = rssiLevel(rssi);
  return level ? `mdi:wifi-strength-${level}` : "mdi:wifi";
}

export function rssiBarCount(rssi) {
  return rssiLevel(rssi);
}

export function fmtRssi(rssi) {
  const value = rssiValue(rssi);
  return value == null ? t('Unknown') : `${value} dBm`;
}


export function startStatusPolling(host) {
  if (host._statusTimer && host._statusDevice === host._selectedDevice) return;
  stopStatusPolling(host);
  if (host._statusDevice !== host._selectedDevice) {
    host._deviceStatus = null;
    host._deviceStatusError = null;
    host._statusDevice = host._selectedDevice;
  }
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
