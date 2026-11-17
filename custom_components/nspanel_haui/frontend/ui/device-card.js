// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { badge, statusDot } from './badge.js';
import { sortHandle } from './sort-handle.js';
import { isPortraitModel } from '../constants.js';
import { deviceConnectionState } from '../device-status.js';

/**
 * Render a device card whose cover opens the device, with a separate reorder affordance.
 * With `onSelect` the strip under the cover (status and name) toggles the card's selection.
 * @param {{ name: string, device: any, status: any, preview?: any, updates?: boolean, disabled?: boolean, selected?: boolean, dragging?: boolean, dropTarget?: boolean, onOpen: () => void, onSelect?: (() => void)|null, onDragStart?: (event: DragEvent) => void, onDragEnd?: () => void, onDragOver?: (event: DragEvent) => void, onDragLeave?: (event: DragEvent) => void, onDrop?: (event: DragEvent) => void }} data
 */
export function deviceCard({ name, device, status, preview, updates = false, disabled = false, selected = false, dragging = false, dropTarget = false, onOpen, onSelect = null, onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop }) {
  const portrait = isPortraitModel(device.config?.display_model);
  const { tone, label: stateLabel } = deviceConnectionState(status);
  const displayName = device.friendlyName || name;
  const info = html`${statusDot(tone, stateLabel)}
      <span class="haui-device-card-name">${displayName}</span>
      ${disabled ? badge(t('Disabled'), 'neutral') : ''}`;
  return html`<article class=${`haui-device-card ${portrait ? 'is-portrait' : ''} ${selected ? 'is-selected' : ''} ${dragging ? 'is-dragging' : ''} ${dropTarget ? 'is-drop-target' : ''}`}
    role="listitem" aria-label=${displayName} aria-current=${selected ? 'true' : nothing}
    @dragover=${onDragOver ?? nothing} @dragleave=${onDragLeave ?? nothing} @drop=${onDrop ?? nothing}>
    <div class="haui-device-card-cover">
      <button type="button" class="haui-device-card-select" aria-label=${t('Open device {name}').replace('{name}', displayName)} @click=${onOpen}>
        ${preview || html`<span class="haui-device-card-bezel" aria-hidden="true"></span>`}
      </button>
      ${updates ? html`<span class="haui-device-update-badge">${t('Update available')}</span>` : ''}
      ${onDragStart ? html`<div class="haui-device-sort">${sortHandle({
        label: t('Drag to reorder {name}').replace('{name}', displayName),
        onDragStart,
        onDragEnd,
      })}</div>` : ''}
    </div>
    ${onSelect
      ? html`<button type="button" class="haui-device-card-info" aria-pressed=${selected ? 'true' : 'false'} @click=${onSelect}>${info}</button>`
      : html`<div class="haui-device-card-info">${info}</div>`}
  </article>`;
}
