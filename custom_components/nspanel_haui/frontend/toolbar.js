/**
 * NSPanel HAUI - Editor - toolbar rendering.
 *
 * Renders the top toolbar with:
 *   - Title bar (separate from action bar)
 *   - Device manager button
 *   - Device selector dropdown
 *   - Device info strip (exported for use in content area)
 */
import { html } from './lit-import.js';
import {
  buildDeviceMap,
  getDeviceDisplayName,
  selectDevice,
  renderDeviceManagerButton,
} from './device-manager.js';

/* ── re-exports for haui-editor.js ─────────────────────────────────────────── */

export { selectDevice } from './device-manager.js';

/* ── title header ────────────────────────────────────────────────────────── */

/**
 * Render the editor title bar (separate from toolbar actions).
 */
export function renderTitleHeader(host) {
  return html`
    <div class="toolbar-header">
      <span class="toolbar-title">NSPanel HAUI - Editor</span>
      ${renderDeviceManagerButton(host)}
    </div>
  `;
}

/* ── device actions bar ──────────────────────────────────────────────────── */

/**
 * Render the device action bar: no longer needed — all controls are in the title bar.
 */
export function renderActionBar(_host) {
  return "";
}

/* ── device manager button ─────────────────────────────────────────────── */

export { renderDeviceManagerButton };

/* ── device selector ─────────────────────────────────────────────────────── */

/**
 * Render a device selector dropdown. Always shows as a dropdown so users
 * can see device names even when only one device exists.
 */
export function renderDeviceSelector(host) {
  if (!host._panels) return "";
  const deviceMap = buildDeviceMap(host);
  const displayNames = Object.keys(deviceMap);
  if (displayNames.length === 0) return "";
  const selected = host._selectedDevice;
  const selectedDisplayName = getDeviceDisplayName(host, selected);

  const options = displayNames.map((name) => {
    const devKey = deviceMap[name];
    const panelCount = (host._panels.devices[devKey]?.panels || []).length;
    const devConfig = (host._panels.devices[devKey]?.config) || {};
    const devEnabled = devConfig.enabled !== false;
    const suffix = devEnabled
      ? `\u00b7 ${panelCount} panel${panelCount !== 1 ? 's' : ''}`
      : `\u00b7 (disabled)`;
    return {
      value: name,
      label: `${name} ${suffix}`,
    };
  });

  return html`
    <ha-select
      class="toolbar-select"
      .value=${selectedDisplayName || ""}
      .options=${options}
      @selected=${(e) => selectDevice(host, e.detail.value)}
    ></ha-select>
  `;
}

/* ── device info strip ────────────────────────────────────────────────────── */

/**
 * Render the inline device status strip shown below the primary action row.
 */
export function renderDeviceInfoStrip(host) {
  const ds = host._deviceStatus;
  const err = host._deviceStatusError;

  const connected = ds?.connected;
  const connState = ds?.connection_state || "unknown";

  let dotClass, label;
  if (connected === true) {
    dotClass = "dot-connected";
    label = "Connected";
  } else if (connState === "handshaking") {
    dotClass = "dot-handshaking";
    label = "Handshaking\u2026";
  } else if (connState === "disconnected") {
    dotClass = "dot-disconnected";
    label = "Disconnected";
  } else {
    dotClass = "dot-unknown";
    label = "Unknown";
  }

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
