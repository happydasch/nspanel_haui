// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { uptimeLabel, relativeTime } from './format.js';
import { button, expandToggle } from './button.js';
import { icon } from './icon.js';
import { surface, sectionHeading } from './surface.js';
import {
  connectionTiles, deviceDiagnostics, diagnosticsIcon, diagnosticsModel, diagnosticsSubtitle,
} from './device-diagnostics.js';
import { infoTile, toggleHoverCard, closeHoverCard } from './info-tile.js';
import { rssiBarCount, rssiStrengthClass, fmtRssi } from '../device-info.js';
import { deviceConnectionState } from '../device-status.js';

/**
 * The Device side stack of the Preview view: the connection and device facts,
 * Diagnostics, and below them the buttons that open a sidebar of their own
 * (Themes, Updates and Backups). Device facts and diagnostics come from the
 * real status payload: facts the device did not report stay "Unknown", and
 * while it is offline they are marked stale.
 *
 * @param {{ name: string, status: any, hass?: any,
 *   onLogs: () => void, onBackups?: () => void, onUpdates: () => void, onEditTheme?: () => void,
 *   onCopyReport?: () => void, detailsExpanded?: boolean, onToggleDetails?: () => void,
 *   updatesDetail?: string, themeDetail?: string,
 *   diagnosticsExpanded?: boolean, onToggleDiagnostics?: () => void,
 *   showEntities?: boolean, onShowEntities?: (show: boolean) => void,
 *   previewTools?: import('./device-diagnostics.js').PreviewTools|null,
 *   onOpenPage?: (() => void)|null, statusError?: string|null }} data
 *   `onOpenPage` shows the device's current page in the simulated preview; the
 *   Current page tile runs it on a click. `statusError` says why the last
 *   status poll failed: the facts shown are then the last ones read.
 */
export function deviceDetails({
  name, status, hass, onLogs, onBackups, onUpdates, onEditTheme,
  updatesDetail = '', themeDetail = '',
  onCopyReport,
  detailsExpanded = true, onToggleDetails, diagnosticsExpanded = false, onToggleDiagnostics,
  showEntities = false, onShowEntities, previewTools = null, onOpenPage = null, statusError = null,
}) {
  const info = status?.device_info || {};
  const { connected, tone, label: stateLabel } = deviceConnectionState(status);
  const stale = Boolean(status) && (!connected || Boolean(statusError));
  const unknown = t('Unknown');
  const recency = connected && Number.isFinite(info.connection_uptime)
    ? t('Online for {uptime}').replace('{uptime}', uptimeLabel(info.connection_uptime))
    : !connected && info.disconnected_since
      ? t('Last seen {time}').replace('{time}', relativeTime(info.disconnected_since))
      : '';
  // Expanded, tiles like the Diagnostics card: the connection readings (once there is a status), then
  // the device facts. The card carries no actions: Updates and Themes sit in the buttons below it.
  // The versions stay in Diagnostics and the Updates sidebar.
  const model = status ? diagnosticsModel(status) : null;
  const tiles = [
    ...(model ? connectionTiles(model) : []),
    infoTile({
      key: 'page', label: t('Current page'), value: status?.current_page || unknown,
      facts: [[t('Last panel update'), info.last_panel_update ? relativeTime(info.last_panel_update) : unknown]],
      note: onOpenPage ? t('Click to show this page in the simulated preview.') : '',
      onClick: onOpenPage,
    }),
    infoTile({
      key: 'network', label: t('IP address'), value: info.ip || unknown,
      facts: [[t('SSID'), info.ssid || unknown], [t('Wi-Fi signal'), fmtRssi(info.rssi)]],
    }),
  ];
  return html`${surface({
    title: t('Connection'),
    subtitle: name,
    className: 'haui-device-details',
    leading: connectionStatus({ info, status, tone, stateLabel, recency, stale }),
    actions: expandToggle(detailsExpanded, onToggleDetails),
    onToggle: onToggleDetails,
    body: detailsExpanded ? html`<div class=${`haui-diag-tiles${stale ? ' is-stale' : ''}`} data-stale=${stale ? 'true' : 'false'}>${tiles}</div>${
      statusError ? html`<p class="haui-details-stale" role="status">${
        t('Device status could not be refreshed: {error}').replace('{error}', statusError)}</p>` : nothing}` : undefined,
  })}${model ? surface({
    title: t('Diagnostics'),
    subtitle: diagnosticsSubtitle(model),
    className: 'haui-diagnostics-card',
    leading: diagnosticsIcon(model),
    actions: expandToggle(diagnosticsExpanded, onToggleDiagnostics),
    onToggle: onToggleDiagnostics,
    body: diagnosticsExpanded
      ? deviceDiagnostics({
        status, hass, expanded: true, onLogs, onCopyReport, showEntities, onShowEntities, previewTools,
      })
      : undefined,
  }) : nothing}${sideActions({
    onBackups, onUpdates, onEditTheme, updatesDetail, themeDetail,
  })}`;
}

/**
 * The buttons below the side stack's cards, as content without a card of their
 * own: each spans the whole width on a line of its own. **Themes** and
 * **Updates** also name what they open on their trailing edge — the selected
 * theme's name, what the update settings hold; **Backups** opens the device's
 * YAML export and import, **Themes** the theme library with the device's theme
 * selected.
 *
 * @param {{ onBackups?: () => void, onUpdates: () => void, updatesDetail?: string,
 *   onEditTheme?: (() => void)|null, themeDetail?: string }} data
 */
function sideActions({
  onBackups, onUpdates, onEditTheme, updatesDetail = '', themeDetail = '',
}) {
  return html`<div class="haui-details-actions">${onEditTheme ? button({
    label: t('Themes'), iconName: 'color', detail: themeDetail,
    onClick: onEditTheme,
  }) : nothing}${button({
    label: t('Updates'), iconName: 'update', detail: updatesDetail,
    onClick: onUpdates,
  })}${onBackups ? button({
    label: t('Backups'), iconName: 'backup-restore',
    onClick: onBackups,
  }) : nothing}</div>`;
}

/**
 * The MDI icon of the connection state: the Wi-Fi strength the panel reports,
 * crossed out when there is no reading. A status without a hub connection
 * still shows its reading; the dot beside it keeps the connection tone.
 * Shared by the card heading and the Fleet device table.
 *
 * @param {any} status - the device status payload, or null while unavailable
 */
function connectionIconName(status) {
  const bars = rssiBarCount(status?.device_info?.rssi);
  if (!status) return 'wifi-strength-off-outline';
  if (bars) return `wifi-strength-${bars}`;
  return status.connected === true ? 'wifi-strength-outline' : 'wifi-off';
}

/**
 * The connection icon, coloured by the Wi-Fi strength the panel reports; the
 * status dot beside it keeps the connection tone.
 *
 * @param {any} status - the device status payload, or null while unavailable
 */
export function connectionIcon(status) {
  const bars = rssiBarCount(status?.device_info?.rssi);
  const strength = bars ? rssiStrengthClass(status.device_info.rssi) : '';
  return icon(connectionIconName(status), strength);
}

/**
 * The connection state as one icon in the card heading. Hover, focus or a tap
 * opens the details.
 *
 * @param {{ info: any, status: any, tone: string, stateLabel: string,
 *   recency: string, stale: boolean }} data
 */
function connectionStatus({ info, status, tone, stateLabel, recency, stale }) {
  const unknown = t('Unknown');
  const facts = [
    [t('Wi-Fi signal'), fmtRssi(info.rssi)],
    [t('SSID'), info.ssid || unknown],
    [t('IP address'), info.ip || unknown],
    [t('Last connected'), info.last_connection ? relativeTime(info.last_connection) : unknown],
  ];
  const label = recency ? `${stateLabel} · ${recency}` : stateLabel;
  // The aria-expanded attribute is static so a status poll never closes an open card.
  return html`<div class=${`haui-conn-status ${tone}`}>
    <button type="button" class="haui-conn-status-button" aria-label=${label}
      aria-describedby="haui-conn-card" aria-expanded="false"
      @click=${toggleHoverCard} @blur=${closeHoverCard} @keydown=${closeHoverCard}>
      ${connectionIcon(status)}<span class="haui-conn-status-dot"></span>
    </button>
    <div class="haui-conn-card" id="haui-conn-card" role="tooltip">
      ${sectionHeading({
        title: stateLabel,
        subtitle: recency,
        leading: html`<span class="haui-conn-status-dot"></span>`,
        className: 'haui-conn-card-head',
      })}
      ${status ? html`<dl>${facts.map(([name, value]) => html`<div><dt>${name}</dt><dd>${value}</dd></div>`)}</dl>` : nothing}
      ${stale ? html`<p class="haui-details-stale">${t('These values were reported before the device disconnected.')}</p>` : nothing}
    </div>
  </div>`;
}
