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

// A row's own controls keep their click; the rest of the row selects the device.
const OWN_CLICK = 'button, a, input, select, textarea, label, [role="menu"], .haui-sort-handle';

/**
 * Render one device inventory entry. With `onSelect` the row selects its device
 * on a click outside its own controls (or on Enter and Space) and marks the
 * selection with `aria-current`; `onSelect` gets the event.
 */
export function deviceRow({ name, device, status, onOpen, onMenu, onSelect = null, selected = false, menuOpen = false, disabled = false, dragging = false, dropTarget = false, onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop }) {
  const { connected, tone, label: stateLabel } = deviceConnectionState(status);
  const info = status?.device_info || {};
  const updates = hasUpdateAvailable(status?.update);
  const versionMismatch = status?.integration_version_mismatch === true;
  const displayName = device.friendlyName || name;
  const connLabel = connected ? `${stateLabel} · ${fmtRssi(info.rssi)}` : stateLabel;
  const selectOnClick = onSelect ? (event) => {
    if (event.target.closest?.(OWN_CLICK)) return;
    onSelect(event);
  } : null;
  const selectOnKey = onSelect ? (event) => {
    if (event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return;
    event.preventDefault();
    onSelect(event);
  } : null;
  return html`<div class=${`haui-device-row ${selected ? 'is-selected' : ''} ${dragging ? 'is-dragging' : ''} ${dropTarget ? 'is-drop-target' : ''}`} role="row"
    aria-current=${selected ? 'true' : nothing} tabindex=${onSelect ? '0' : nothing}
    @click=${selectOnClick ?? nothing} @keydown=${selectOnKey ?? nothing}
    @dragover=${onDragOver ?? nothing} @dragleave=${onDragLeave ?? nothing} @drop=${onDrop ?? nothing}>
    <div class="haui-device-row-identity" role="cell">
      ${onDragStart ? sortHandle({ label: t('Drag to reorder {name}').replace('{name}', displayName), onDragStart, onDragEnd }) : ''}
      <span class=${`haui-conn-status haui-conn-status-icon ${tone}`} role="img" aria-label=${connLabel} title=${connLabel}>
        ${connectionIcon(status)}<span class="haui-conn-status-dot"></span>
      </span>
      <div><button type="button" class="haui-device-row-name" @click=${onOpen}>${displayName}</button></div>
    </div>
    <span class="haui-device-row-ip" role="cell">${info.ip || t('Unknown')}</span>
    <span class=${`haui-device-row-version ${versionMismatch ? 'is-mismatch' : ''}`} role="cell"
      title=${versionMismatch ? t('Firmware version does not match the integration') : nothing}>
      <span>${versionLabel(info.yaml_version)}</span>
      ${versionMismatch ? badge(t('Mismatch'), 'danger', 'haui-device-row-mismatch') : nothing}
    </span>
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
        hasPopup: 'menu',
        // The menu exists only while it is open.
        controls: menuOpen ? `haui-device-menu-${name}` : undefined,
        onClick: onMenu,
      }) : ''}
    </div>
  </div>`;
}
