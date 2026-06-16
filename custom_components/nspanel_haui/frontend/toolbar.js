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
  getDeviceKeys,
  selectDevice,
  renderDeviceManagerButton,
} from './device-manager.js';
import { renderPanelDropdown } from './panel-table.js';
import { readNetworkInfo } from './network-info.js';
import { getConnectionStateClass, getConnectionStateLabel } from './device-info.js';

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
      label=${host._t('Toggle sidebar')}
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
      <span class="toolbar-title">${host._t('NSPanel HAUI - Editor')}</span>
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
  const displayNames = getDeviceKeys(host);
  if (displayNames.length === 0) return "";
  const selected = host._selectedDevice;

  const options = displayNames.map((name) => {
    const dev = (host._panels.devices || {})[name] || {};
    const config = dev.config || {};
    const enabled = config.enabled !== false;
    const label = enabled ? `${name}` : `${name} (${host._t('disabled')})`;
    return { value: name, label };
  });

  return html`
    <ha-select
      class="toolbar-select"
      .value=${selected || ""}
      .options=${options}
      @selected=${(e) => selectDevice(host, e.detail.value)}
    ></ha-select>
  `;
}

/* ── device info strip ────────────────────────────────────────────────────── */

/**
 * Render the inline device status strip shown below the primary action row.
 * Shows connection state with color-coded dot, current page, IP address,
 * and quick-action buttons.
 */
export function renderDeviceInfoStrip(host) {
  const ds = host._deviceStatus;
  const err = host._deviceStatusError;

  const connected = ds?.connected;
  const connState = ds?.connection_state || "unknown";

  const dotClass = getConnectionStateClass(connected, connState);
  const label = getConnectionStateLabel(host._t, connected, connState);

  const currentPage = ds?.current_page || "—";
  const nw = readNetworkInfo(host.hass, host._selectedDevice);
  const ip = nw && nw.ip ? nw.ip : null;

  return html`
    <div class="device-info-strip">
      <span class="info-strip-item connection-indicator" title=${`${host._t('Connection')}: ${connState}`}>
        <span class="connection-indicator-dot ${dotClass}"></span>
        <span class="strip-label">${label}</span>
      </span>
      ${ip && !host.narrow ? html`
        <span class="info-strip-item" title="IP: ${ip}">
          <ha-icon icon="mdi:ip-network-outline" class="strip-icon"></ha-icon>
          <span class="strip-label strip-mono">${ip}</span>
        </span>
      ` : ""}
      ${currentPage !== "-" && !host.narrow ? html`
        <span class="info-strip-item" title=${`${host._t('Current page')}: ${currentPage}`}>
          <ha-icon icon="mdi:application-brackets-outline" class="strip-icon"></ha-icon>
          <span class="strip-label">${currentPage}</span>
        </span>
      ` : ""}
      ${err ? html`
        <span class="info-strip-item strip-error" title=${err}>
          <ha-icon icon="mdi:alert-circle" class="strip-icon"></ha-icon>
          <span class="strip-label">${err}</span>
        </span>
      ` : ""}
      <span class="pl-spacer"></span>
      ${!host.narrow ? html`
      <ha-icon-button
        title=${host._t('Colors')}
        label=${host._t('Colors')}
        @click=${() => host._onHeaderColors()}
      >
        <ha-icon icon="mdi:palette-outline"></ha-icon>
      </ha-icon-button>
      <ha-icon-button
        title=${host._t('Device settings')}
        label=${host._t('Device settings')}
        @click=${() => host._onHeaderSettings()}
      >
        <ha-icon icon="mdi:cog-outline"></ha-icon>
      </ha-icon-button>
      ` : ""}
      <div class="pl-more">
        <ha-icon-button
          title=${host._t('Device actions')}
          label=${host._t('Device actions')}
          @click=${() => host._toggleHeaderMenu()}
        >
          <ha-icon icon="mdi:dots-vertical"></ha-icon>
        </ha-icon-button>
        ${host._actionsMenuIndex === '__header__'
          ? renderPanelDropdown(host, null, [
              { icon: 'mdi:information-outline', label: host._t('Info'), disabled: !host._selectedDevice, action: () => { host._showDeviceInfo = true; host.requestUpdate(); } },
              'divider',
              { icon: 'mdi:palette-outline', label: host._t('Colors'), disabled: !host._selectedDevice, action: () => host._onHeaderColors() },
              { icon: 'mdi:cog-outline', label: host._t('Settings'), disabled: !host._selectedDevice, action: () => host._onHeaderSettings() },
              'divider',
              { icon: 'mdi:file-import', label: host._t('Import YAML'), disabled: !host._selectedDevice, action: () => host._onHeaderImportYaml() },
              { icon: 'mdi:file-export', label: host._t('Export YAML'), disabled: !host._selectedDevice, action: () => host._onHeaderExportYaml() },
              'divider',
              { icon: 'mdi:file-document-outline', label: host._t('Logs'), action: () => { host._showLogs = true; host.requestUpdate(); } },
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
        label=${host._t('Add Panel')}
        @click=${() => host._openAdd()}
      >
        <ha-icon icon="mdi:plus" slot="icon"></ha-icon>
        ${host._t('Add Panel')}
      </ha-button>
      <span class="pl-spacer"></span>
      <div class="view-toggle-group">
        <button
          class="view-toggle-btn ${isGrid ? 'active' : ''}"
          title=${host._t('Grid view')}
          @click=${() => {
            if (!isGrid) {
              host._viewMode = 'grid';
              localStorage.setItem('haui_viewMode', 'grid');
              host.requestUpdate();
            }
          }}
        >
          <ha-icon icon="mdi:grid"></ha-icon>
          <span>${host._t('Grid')}</span>
        </button>
        <button
          class="view-toggle-btn ${!isGrid ? 'active' : ''}"
          title=${host._t('List view')}
          @click=${() => {
            if (isGrid) {
              host._viewMode = 'list';
              localStorage.setItem('haui_viewMode', 'list');
              host.requestUpdate();
            }
          }}
        >
          <ha-icon icon="mdi:view-list"></ha-icon>
          <span>${host._t('List')}</span>
        </button>
      </div>
    </div>
  `;
}
