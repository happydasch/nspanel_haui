// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { uptimeLabel, relativeTime } from './format.js';
import { button, expandToggle } from './button.js';
import { icon } from './icon.js';
import { surface } from './surface.js';
import {
  connectionTiles, deviceDiagnostics, diagnosticsIcon, diagnosticsModel, diagnosticsSubtitle,
} from './device-diagnostics.js';
import { infoTile, toggleHoverCard, closeHoverCard } from './info-tile.js';
import { rssiBarCount, rssiStrengthClass, fmtRssi } from '../device-info.js';
import { deviceConnectionState } from '../device-status.js';

/**
 * The Device side stack of the Preview view: connection and device facts with
 * the Updates action, Diagnostics, and YAML backup. Device facts and diagnostics
 * come from the real status payload: facts the device did not report stay
 * "Unknown", and while it is offline they are marked stale.
 *
 * @param {{ name: string, status: any, hass?: any,
 *   onLogs: () => void, onFirmware: () => void, onCopyReport?: () => void, detailsExpanded?: boolean, onToggleDetails?: () => void,
 *   diagnosticsExpanded?: boolean, onToggleDiagnostics?: () => void,
 *   yamlExpanded?: boolean, onToggleYaml?: () => void,
 *   onYamlImport?: () => void, onYamlExport?: () => void,
 *   showEntities?: boolean, onShowEntities?: (show: boolean) => void,
 *   previewTools?: import('./device-diagnostics.js').PreviewTools|null,
 *   onOpenPage?: (() => void)|null }} data
 *   `onOpenPage` shows the device's current page in the simulated preview; the
 *   Current page tile runs it on a click.
 */
export function deviceDetails({
  name, status, hass, onLogs, onFirmware,
  onCopyReport,
  detailsExpanded = true, onToggleDetails, diagnosticsExpanded = false, onToggleDiagnostics,
  yamlExpanded = false, onToggleYaml, onYamlImport, onYamlExport,
  showEntities = false, onShowEntities, previewTools = null, onOpenPage = null,
}) {
  const info = status?.device_info || {};
  const { connected, tone, label: stateLabel } = deviceConnectionState(status);
  const stale = Boolean(status) && !connected;
  const unknown = t('Unknown');
  const recency = connected && Number.isFinite(info.connection_uptime)
    ? t('Online for {uptime}').replace('{uptime}', uptimeLabel(info.connection_uptime))
    : !connected && info.disconnected_since
      ? t('Last seen {time}').replace('{time}', relativeTime(info.disconnected_since))
      : '';
  // Expanded, tiles like the Diagnostics card: the connection readings (once there is a status), then
  // the device facts and, below them, the Updates action. The versions stay in Diagnostics and the
  // Updates sidebar.
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
    title: t('Connection & device'),
    subtitle: name,
    className: 'haui-device-details',
    leading: connectionStatus({ info, status, tone, stateLabel, recency, stale }),
    actions: expandToggle(detailsExpanded, onToggleDetails),
    onToggle: onToggleDetails,
    body: detailsExpanded ? html`<div class=${`haui-diag-tiles${stale ? ' stale' : ''}`}>${tiles}</div>${
      button({ label: t('Updates'), iconName: 'update', onClick: onFirmware, className: 'haui-details-updates' })}` : undefined,
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
  }) : nothing}${onYamlImport || onYamlExport ? surface({
    title: t('Backup'),
    subtitle: t('Back up this device or restore it on another hub.'),
    className: 'haui-yaml-card',
    leading: html`<span class="haui-backup-status" aria-hidden="true">${icon('backup-restore')}</span>`,
    actions: expandToggle(yamlExpanded, onToggleYaml),
    onToggle: onToggleYaml,
    body: yamlExpanded ? html`<div class="haui-card-actions haui-yaml-actions">
      ${onYamlImport ? button({ label: t('Import'), iconName: 'upload', onClick: onYamlImport }) : nothing}
      ${onYamlExport ? button({ label: t('Export'), iconName: 'file', onClick: onYamlExport }) : nothing}
    </div>` : undefined,
  }) : nothing}`;
}

/**
 * The MDI icon of the connection state: the Wi-Fi strength while connected,
 * crossed out while not. Shared by the card heading and the Fleet device table.
 *
 * @param {any} status - the device status payload, or null while unavailable
 */
function connectionIconName(status) {
  const bars = rssiBarCount(status?.device_info?.rssi);
  return !status ? 'wifi-strength-off-outline'
    : status.connected !== true ? 'wifi-off'
      : bars ? `wifi-strength-${bars}` : 'wifi-strength-outline';
}

/**
 * The connection icon, coloured by the Wi-Fi strength while connected; the
 * status dot beside it keeps the connection tone.
 *
 * @param {any} status - the device status payload, or null while unavailable
 */
export function connectionIcon(status) {
  const strength = status?.connected === true ? rssiStrengthClass(status.device_info?.rssi) : '';
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
      <div class="haui-conn-card-head">
        <span class="haui-conn-status-dot"></span>
        <div><strong>${stateLabel}</strong>${recency ? html`<span>${recency}</span>` : nothing}</div>
      </div>
      ${status ? html`<dl>${facts.map(([name, value]) => html`<div><dt>${name}</dt><dd>${value}</dd></div>`)}</dl>` : nothing}
      ${stale ? html`<p class="haui-details-stale">${t('These values were reported before the device disconnected.')}</p>` : nothing}
    </div>
  </div>`;
}
