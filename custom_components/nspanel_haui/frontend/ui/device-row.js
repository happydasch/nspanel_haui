// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { iconButton } from './button.js';
import { badge } from './badge.js';
import { sortHandle } from './sort-handle.js';
import { overlayAnchor } from './popover.js';
import { versionLabel } from './format.js';
import { connectionIcon } from './device-details.js';
import { fmtRssi } from '../device-info.js';
import { deviceConnectionState, hasUpdateAvailable } from '../device-status.js';

/** Render one device inventory entry. */
export function deviceRow({ name, device, status, onOpen, onMenu, menuOpen = false, disabled = false, dragging = false, dropTarget = false, onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop }) {
  const { connected, tone, label: stateLabel } = deviceConnectionState(status);
  const info = status?.device_info || {};
  const updates = hasUpdateAvailable(status?.update);
  const displayName = device.friendlyName || name;
  const connLabel = connected ? `${stateLabel} · ${fmtRssi(info.rssi)}` : stateLabel;
  return html`<div class=${`haui-device-row ${dragging ? 'is-dragging' : ''} ${dropTarget ? 'is-drop-target' : ''}`} role="row"
    @dragover=${onDragOver ?? nothing} @dragleave=${onDragLeave ?? nothing} @drop=${onDrop ?? nothing}>
    <div class="haui-device-row-identity" role="cell">
      ${onDragStart ? sortHandle({ label: t('Drag to reorder {name}').replace('{name}', displayName), onDragStart, onDragEnd }) : ''}
      <span class=${`haui-conn-status haui-conn-status-icon ${tone}`} role="img" aria-label=${connLabel} title=${connLabel}>
        ${connectionIcon(status)}<span class="haui-conn-status-dot"></span>
      </span>
      <div><button type="button" class="haui-device-row-name" @click=${onOpen}>${displayName}</button></div>
    </div>
    <span class="haui-device-row-ip" role="cell">${info.ip || t('Unknown')}</span>
    <span class="haui-device-row-version" role="cell">${versionLabel(status?.haui_version)}</span>
    <span class="haui-device-row-version" role="cell">${versionLabel(info.tft_version)}</span>
    <div class="haui-device-row-actions" role="cell">
      ${disabled ? badge(t('Disabled'), 'neutral') : ''}
      ${updates ? badge(t('Update'), 'warning') : ''}
      ${onMenu ? iconButton({
        label: t('Actions for {name}').replace('{name}', displayName),
        iconName: 'more',
        className: 'haui-row-action',
        anchorKey: overlayAnchor('device-menu-row', name),
        expanded: menuOpen,
        controls: `haui-device-menu-${name}`,
        onClick: onMenu,
      }) : ''}
    </div>
  </div>`;
}
