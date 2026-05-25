/**
 * NSPanel HAUI - Editor - toolbar rendering.
 *
 * Renders the top toolbar with:
 *   - Title bar (separate from action bar)
 *   - Device manager button
 *   - Device selector dropdown
 *   - Device info strip (exported for use in content area)
 *   - Panel toolbar (device selector, device actions)
 *   - Below-toolbar actions (Add Panel, view toggle)
 */
import { html } from './lit-import.js';
import {
  buildDeviceMap,
  getDeviceDisplayName,
  selectDevice,
  renderDeviceManagerButton,
} from './device-manager.js';
import { renderPanelDropdown } from './panel-table.js';

/* ── re-exports for haui-editor.js ─────────────────────────────────────────── */

export { selectDevice } from './device-manager.js';

/* ── title header ────────────────────────────────────────────────────────── */

/**
 * Render a menu button (hamburger) to toggle HA sidebar.
 * Only shown on narrow viewports; always present in the template
 * but evaluates to empty string when host.narrow is false.
 */
export function renderMenuButton(host) {
  if (!host.narrow) return "";
  return html`
    <ha-icon-button
      class="menu-toggle-btn"
      label="Toggle sidebar"
      @click=${() => host.dispatchEvent(
        new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true })
      )}
    >
      <ha-icon icon="mdi:menu"></ha-icon>
    </ha-icon-button>
  `;
}

/**
 * Render the editor title bar (separate from toolbar actions).
 */
export function renderTitleHeader(host) {
  return html`
    <div class="toolbar-header">
      ${renderMenuButton(host)}
      <span class="toolbar-title">NSPanel HAUI - Editor</span>
      ${renderDeviceManagerButton(host)}
    </div>
  `;
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
    const dev = (host._panels.devices || {})[devKey] || {};
    const config = dev.config || {};
    const enabled = config.enabled !== false;
    const label = enabled ? `${name}` : `${name} (disabled)`;
    return {
      value: name,
      label,
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
      <span class="pl-spacer"></span>
      <ha-icon-button
        title="Colors"
        label="Colors"
        @click=${() => host._onHeaderColors()}
      >
        <ha-icon icon="mdi:palette-outline"></ha-icon>
      </ha-icon-button>
      <ha-icon-button
        title="Device settings"
        label="Device settings"
        @click=${() => host._onHeaderSettings()}
      >
        <ha-icon icon="mdi:cog-outline"></ha-icon>
      </ha-icon-button>
      <div class="pl-more">
        <ha-icon-button
          title="Device actions"
          label="Device actions"
          @click=${() => host._toggleHeaderMenu()}
        >
          <ha-icon icon="mdi:dots-vertical"></ha-icon>
        </ha-icon-button>
        ${host._actionsMenuIndex === '__header__'
          ? renderPanelDropdown(host, null, [
              { icon: 'mdi:information-outline', label: 'Info', disabled: !host._selectedDevice, action: () => { host._showDeviceInfo = true; host.requestUpdate(); } },
              { icon: 'mdi:palette-outline', label: 'Colors', disabled: !host._selectedDevice, action: () => host._onHeaderColors() },
              { icon: 'mdi:cog-outline', label: 'Settings', disabled: !host._selectedDevice, action: () => host._onHeaderSettings() },
              'divider',
              { icon: 'mdi:file-import', label: 'Import YAML', disabled: !host._selectedDevice, action: () => host._onHeaderImportYaml() },
              { icon: 'mdi:file-export', label: 'Export YAML', disabled: !host._selectedDevice, action: () => host._onHeaderExportYaml() },
              'divider',
              { icon: 'mdi:file-document-outline', label: 'Logs', action: () => { host._showLogs = true; host.requestUpdate(); } },
            ], () => { host._actionsMenuIndex = null; })
          : ""}
      </div>
    </div>
  `;
}

/* ── panel toolbar (shared by grid + list views) ──────────────────────────── */

/**
 * Shared toolbar for both grid and list views.
 * Renders device selector and device actions menu.
 * Placed inside a ha-card by haui-editor.js.
 */
export function renderPanelToolbar(host) {
  return html`
    <div class="panel-toolbar">
      <div class="panel-toolbar-row panel-toolbar-row-selector">
        <div class="toolbar-select-wrap">
          ${renderDeviceSelector(host)}
        </div>
      </div>
    </div>
  `;
}

/* ── below-toolbar actions strip ────────────────────── */

/**
 * Renders Add Panel button and view mode toggle below the toolbar card.
 * Separated from the main toolbar so it sits between the toolbar card
 * and the panel content area.
 */
export function renderToolbarActions(host) {
  const isGrid = host._viewMode === 'grid';
  return html`
    <div class="toolbar-actions-strip">
      <ha-button
        label="Add Panel"
        @click=${() => host._openAdd()}
      >
        <ha-icon icon="mdi:plus" slot="icon"></ha-icon>
        Add Panel
      </ha-button>
      <span class="pl-spacer"></span>
      <div class="view-toggle-group">
        <button
          class="view-toggle-btn ${isGrid ? 'active' : ''}"
          title="Grid view"
          @click=${() => {
            if (!isGrid) {
              host._viewMode = 'grid';
              localStorage.setItem('haui_viewMode', 'grid');
              host.requestUpdate();
            }
          }}
        >
          <ha-icon icon="mdi:grid"></ha-icon>
          <span>Grid</span>
        </button>
        <button
          class="view-toggle-btn ${!isGrid ? 'active' : ''}"
          title="List view"
          @click=${() => {
            if (isGrid) {
              host._viewMode = 'list';
              localStorage.setItem('haui_viewMode', 'list');
              host.requestUpdate();
            }
          }}
        >
          <ha-icon icon="mdi:view-list"></ha-icon>
          <span>List</span>
        </button>
      </div>
    </div>
  `;
}
