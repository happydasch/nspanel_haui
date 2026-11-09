/**
 * NSPanel HAUI - toolbar rendering.
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
import { t } from './localize.js';
import {
  getDeviceKeys,
  selectDevice,
  renderDeviceManagerButton,
} from './device-manager.js';
import { writeStorage } from './dom-helpers.js';
import { renderPanelDropdown } from './panel-table.js';
import { getConnectionStateClass, getConnectionStateLabel } from './device-info.js';

/* ── title header ────────────────────────────────────────────────────────── */

/**
 * Render a menu button (hamburger) to toggle HA sidebar.
 * Only shown on narrow viewports; always present in the template
 * but evaluates to empty string when host.narrow is false.
 */
function renderMenuButton(host) {
  if (!host.narrow) return "";
  return html`
    <ha-icon-button
      class="menu-toggle-btn"
      label=${t('Toggle sidebar')}
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
      <span class="toolbar-title">${t('NSPanel HAUI')}</span>
      ${host.entryId ? html`<ha-icon-button
        class="notifications-button"
        label=${t('Notifications')}
        title=${t('Notifications')}
        @click=${() => host._openNotifications()}
      >
        <ha-icon icon="mdi:bell-outline"></ha-icon>
        ${host._notifications?.length ? html`<span class="notification-count">${host._notifications.length}</span>` : ''}
      </ha-icon-button>` : ''}
      ${renderDeviceManagerButton(host)}
    </div>
  `;
}

/* ── device selector ─────────────────────────────────────────────────────── */

/**
 * Render a device selector dropdown. Always shows as a dropdown so users
 * can see device names even when only one device exists.
 */
function renderDeviceSelector(host) {
  if (!host._panels) return "";
  const displayNames = getDeviceKeys(host);
  if (displayNames.length === 0) return "";
  const selected = host._selectedDevice;

  const options = displayNames.map((name) => {
    const dev = (host._panels.devices || {})[name] || {};
    const config = dev.config || {};
    const enabled = config.enabled !== false;
    const displayName = dev.friendly_name || name;
    const label = enabled ? `${displayName}` : `${displayName} (${t('disabled')})`;
    return { value: name, label };
  });

  return html`
    <select
      class="toolbar-select native-select"
      .value=${selected || ""}
      @change=${(e) => selectDevice(host, e.target.value)}
    >
      ${options.map((o) => html`<option value=${o.value} ?selected=${(selected || "") === o.value}>${o.label}</option>`)}
    </select>
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
  const label = getConnectionStateLabel(t, connected, connState);

  const currentPage = ds?.current_page || "—";
  const ip = ds?.device_info?.ip || null;

  return html`
    <div class="device-info-strip">
      <span class="info-strip-item connection-indicator" title=${`${t('Connection')}: ${connState}`}>
        <span class="connection-indicator-dot ${dotClass}"></span>
        <span class="strip-label">${label}</span>
      </span>
      ${ip && !host.narrow ? html`
        <span class="info-strip-item" title=${t('IP: {ip}').replace('{ip}', ip)}>
          <ha-icon icon="mdi:ip-network-outline" class="strip-icon"></ha-icon>
          <span class="strip-label strip-mono">${ip}</span>
        </span>
      ` : ""}
      ${currentPage !== "-" && !host.narrow ? html`
        <span class="info-strip-item" title=${`${t('Current page')}: ${currentPage}`}>
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
        title=${t('Live preview')}
        label=${t('Live preview')}
        ?disabled=${!host._selectedDevice}
        @click=${() => host._onHeaderLivePreview()}
      >
        <ha-icon icon="mdi:television-play"></ha-icon>
      </ha-icon-button>
      <ha-icon-button
        title=${t('Colors')}
        label=${t('Colors')}
        @click=${() => host._onHeaderColors()}
      >
        <ha-icon icon="mdi:palette-outline"></ha-icon>
      </ha-icon-button>
      <ha-icon-button
        title=${t('Device settings')}
        label=${t('Device settings')}
        @click=${() => host._onHeaderSettings()}
      >
        <ha-icon icon="mdi:cog-outline"></ha-icon>
      </ha-icon-button>
      ` : ""}
      <div class="pl-more">
        <ha-icon-button
          title=${t('Device actions')}
          label=${t('Device actions')}
          @click=${() => host._toggleHeaderMenu()}
        >
          <ha-icon icon="mdi:dots-vertical"></ha-icon>
        </ha-icon-button>
        ${host._actionsMenuIndex === '__header__'
          ? renderPanelDropdown(host, null, [
              { icon: 'mdi:information-outline', label: t('Info'), disabled: !host._selectedDevice, action: () => { host._showDeviceInfo = true; host.requestUpdate(); } },
              { icon: 'mdi:television-play', label: t('Live preview'), disabled: !host._selectedDevice, action: () => host._onHeaderLivePreview() },
              'divider',
              { icon: 'mdi:palette-outline', label: t('Colors'), disabled: !host._selectedDevice, action: () => host._onHeaderColors() },
              { icon: 'mdi:cog-outline', label: t('Settings'), disabled: !host._selectedDevice, action: () => host._onHeaderSettings() },
              'divider',
              { icon: 'mdi:file-import', label: t('Import YAML'), disabled: !host._selectedDevice, action: () => host._onHeaderImportYaml() },
              { icon: 'mdi:file-export', label: t('Export YAML'), disabled: !host._selectedDevice, action: () => host._onHeaderExportYaml() },
              'divider',
              { icon: 'mdi:file-document-outline', label: t('Logs'), action: () => { host._showLogs = true; host.requestUpdate(); } },
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
        label=${t('Add Panel')}
        @click=${() => host._openAdd()}
      >
        <ha-icon icon="mdi:plus" slot="icon"></ha-icon>
        ${t('Add Panel')}
      </ha-button>
      <span class="pl-spacer"></span>
      <div class="view-toggle-group">
        <button
          class="view-toggle-btn ${isGrid ? 'active' : ''}"
          title=${t('Grid view')}
          @click=${() => {
            if (!isGrid) {
              host._viewMode = 'grid';
              writeStorage('haui_viewMode', 'grid');
              host.requestUpdate();
            }
          }}
        >
          <ha-icon icon="mdi:grid"></ha-icon>
          <span>${t('Grid')}</span>
        </button>
        <button
          class="view-toggle-btn ${!isGrid ? 'active' : ''}"
          title=${t('List view')}
          @click=${() => {
            if (isGrid) {
              host._viewMode = 'list';
              writeStorage('haui_viewMode', 'list');
              host.requestUpdate();
            }
          }}
        >
          <ha-icon icon="mdi:view-list"></ha-icon>
          <span>${t('List')}</span>
        </button>
      </div>
    </div>
  `;
}

/** Read the integration version embedded in the registered frontend asset URL. */
export function getEditorVersion(moduleUrl) {
  const pathname = new URL(moduleUrl).pathname;
  const assetVersion = pathname.match(/\/nspanel_haui_frontend\/([^/]+)\/toolbar\.js$/)?.[1];
  return assetVersion?.replace(/-[\da-f]{12}$/, '') || null;
}

/** Return whether a PEP 440 version identifies a prerelease. */
export function isPrereleaseVersion(version) {
  const publicVersion = version.split('+', 1)[0];
  return /(?:\.dev\d*|(?:a|alpha|b|beta|c|pre|preview|rc)\d*)(?=$|[.+-])/i.test(
    publicVersion,
  );
}

const DOCS_URL = 'https://happydasch.github.io/nspanel_haui/';

/** Return the docs for a version: prereleases are built from `dev`, published under `dev/`. */
export function docsUrl(version) {
  return version && isPrereleaseVersion(version) ? `${DOCS_URL}dev/` : DOCS_URL;
}

const EDITOR_VERSION = getEditorVersion(import.meta.url);

/** Render version information alongside the persistent editor links. */
export function renderFooter(host) {
  return html`
    <div class="editor-footer">
      ${EDITOR_VERSION ? html`
        <span class="footer-version-group">
          <span class="footer-version" title="${t('Version')}">v${EDITOR_VERSION}</span>
          ${isPrereleaseVersion(EDITOR_VERSION) ? html`
            <span class="footer-dev-badge" title="${t('Development prerelease')}">${t('Dev')}</span>
          ` : ''}
        </span>
      ` : ''}
      <a
        class="footer-link"
        href="https://github.com/happydasch/nspanel_haui"
        target="_blank"
        rel="noopener noreferrer"
        title="${t('GitHub')}"
      >
        <ha-icon icon="mdi:github"></ha-icon>
        <span>${t('GitHub')}</span>
      </a>
      <a
        class="footer-link"
        href="${docsUrl(EDITOR_VERSION)}"
        target="_blank"
        rel="noopener noreferrer"
        title="${t('Documentation')}"
      >
        <ha-icon icon="mdi:help-circle-outline"></ha-icon>
        <span>${t('Documentation')}</span>
      </a>
    </div>
  `;
}
