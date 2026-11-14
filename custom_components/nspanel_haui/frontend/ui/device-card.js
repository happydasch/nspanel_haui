// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { badge, statusDot } from './badge.js';
import { sortHandle } from './sort-handle.js';
import { isPortraitModel } from '../constants.js';
import { deviceConnectionState } from '../device-status.js';

/**
 * Render a device card that opens the device, with a separate reorder affordance.
 * @param {{ name: string, device: any, status: any, preview?: any, updates?: boolean, disabled?: boolean, dragging?: boolean, dropTarget?: boolean, onSelect: () => void, onDragStart?: (event: DragEvent) => void, onDragEnd?: () => void, onDragOver?: (event: DragEvent) => void, onDragLeave?: (event: DragEvent) => void, onDrop?: (event: DragEvent) => void }} data
 */
export function deviceCard({ name, device, status, preview, updates = false, disabled = false, dragging = false, dropTarget = false, onSelect, onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop }) {
  const portrait = isPortraitModel(device.config?.display_model);
  const { tone, label: stateLabel } = deviceConnectionState(status);
  const displayName = device.friendlyName || name;
  return html`<article class=${`haui-device-card ${portrait ? 'is-portrait' : ''} ${dragging ? 'is-dragging' : ''} ${dropTarget ? 'is-drop-target' : ''}`}
    @dragover=${onDragOver ?? nothing} @dragleave=${onDragLeave ?? nothing} @drop=${onDrop ?? nothing}>
    <div class="haui-device-card-cover">
      <button type="button" class="haui-device-card-select" aria-label=${t('Open device {name}').replace('{name}', displayName)} @click=${onSelect}>
        ${preview || html`<span class="haui-device-card-bezel" aria-hidden="true"></span>`}
      </button>
      ${updates ? html`<span class="haui-device-update-badge">${t('Update available')}</span>` : ''}
      ${onDragStart ? html`<div class="haui-device-sort">${sortHandle({
        label: t('Drag to reorder {name}').replace('{name}', displayName),
        onDragStart,
        onDragEnd,
      })}</div>` : ''}
    </div>
    <div class="haui-device-card-info">
      ${statusDot(tone, stateLabel)}
      <button type="button" class="haui-device-card-name" @click=${onSelect}>${displayName}</button>
      ${disabled ? badge(t('Disabled'), 'neutral') : ''}
    </div>
  </article>`;
}
