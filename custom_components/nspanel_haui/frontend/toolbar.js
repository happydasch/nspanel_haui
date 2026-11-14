/**
 * NSPanel HAUI - toolbar rendering.
 *
 * Renders the top toolbar with:
 *   - Dashboard title bar with the notification bell
 *   - Persistent version and documentation footer
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import { overlayAnchor } from './ui/popover.js';

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
      class="haui-toolbar-menu-toggle"
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
    <div class="haui-toolbar-header">
      ${renderMenuButton(host)}
      <div class="haui-toolbar-brand">
        <span class="haui-toolbar-title">${t('NSPanel HAUI')}</span>
        <span class="haui-toolbar-context">${host._route?.view === 'device'
          ? host._panels?.devices?.[host._route.device]?.friendly_name || host._route.device
          : t('Dashboard')}</span>
      </div>
      ${host.entryId ? html`<ha-icon-button
        class="haui-toolbar-notifications-button"
        label=${t('Notifications')}
        title=${t('Notifications')}
        data-overlay-anchor=${overlayAnchor('notification-centre')}
        @click=${() => host._openNotifications()}
      >
        <ha-icon icon="mdi:bell-outline"></ha-icon>
        ${host._notifications?.length ? html`<span class="haui-toolbar-notification-count">${host._notifications.length}</span>` : ''}
      </ha-icon-button>` : ''}
    </div>
  `;
}

/** Read the integration version embedded in the registered frontend asset URL. */
export function getIntegrationVersion(moduleUrl) {
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

/** Render version information alongside the persistent editor links. */
export function renderFooter(host, integrationVersion = INTEGRATION_VERSION) {
  return html`
    <div class="editor-footer">
      ${integrationVersion ? html`
        <span class="footer-version-group">
          <span class="footer-version" title=${t('Integration version')}>v${integrationVersion}</span>
          ${isPrereleaseVersion(integrationVersion) ? html`
            <span class="footer-dev-badge" title=${t('Development prerelease')}>${t('Dev')}</span>
          ` : ''}
        </span>
      ` : ''}
      <a class="footer-link" href="https://github.com/happydasch/nspanel_haui"
        target="_blank" rel="noopener noreferrer" title=${t('GitHub')}>
        <ha-icon icon="mdi:github"></ha-icon><span>${t('GitHub')}</span>
      </a>
      <a class="footer-link" href=${docsUrl(integrationVersion)} target="_blank"
        rel="noopener noreferrer" title=${t('Documentation')}>
        <ha-icon icon="mdi:help-circle-outline"></ha-icon><span>${t('Documentation')}</span>
      </a>
    </div>
  `;
}

const INTEGRATION_VERSION = getIntegrationVersion(import.meta.url);
