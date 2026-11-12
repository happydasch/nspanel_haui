// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';
import { statusDot } from './badge.js';
import { deviceConnectionState } from '../device-status.js';


/**
 * Device navigator of the Device screen: a row of chips, or a dropdown when the
 * chips do not fit beside the title.
 *
 * Both are rendered; `collapsed` (measured by the shell, see `railOverflows`)
 * decides which one shows. The chips stay in the layout while hidden so the
 * next measurement can tell when they fit again.
 *
 * @param {{ devices: any[], selected: string, collapsed?: boolean, onSelect: (name: string) => void }} options
 */
export function deviceRail({ devices, selected, collapsed = false, onSelect }) {
  const current = devices.find((entry) => entry.name === selected);
  return html`<div class=${`haui-device-switch${collapsed ? ' is-collapsed' : ''}`}>
    <nav class="haui-device-rail" aria-label=${t('Devices')} aria-hidden=${collapsed ? 'true' : 'false'}>
      ${devices.map(({ name, device, status, updates }) => {
        const { tone, label } = deviceConnectionState(status);
        return html`
          <button type="button" class=${`haui-device-rail-item ${name === selected ? 'active' : ''}`}
            aria-current=${name === selected ? 'page' : 'false'}
            tabindex=${collapsed ? '-1' : '0'}
            aria-label=${t('{name}, {status}').replace('{name}', device.friendlyName || name)
              .replace('{status}', label)}
            @click=${() => onSelect(name)}>
            ${statusDot(tone, '')}
            <span>${device.friendlyName || name}</span>
            ${updates ? icon('alert', 'haui-device-rail-update') : ''}
          </button>`;
      })}
    </nav>
    <label class="haui-device-select">
      ${statusDot(deviceConnectionState(current?.status).tone, '')}
      <select aria-label=${t('Devices')} @change=${(event) => onSelect(event.currentTarget.value)}>
        ${devices.map(({ name, device }) => html`<option value=${name}
          ?selected=${name === selected}>${device.friendlyName || name}</option>`)}
      </select>
    </label>
  </div>`;
}

/**
 * Whether the device chips need more room than the head leaves them.
 *
 * @param {ParentNode|null|undefined} root - the editor's render root
 * @returns {boolean|null} null while no rail is rendered
 */
export function railOverflows(root) {
  const rail = /** @type {any} */ (root?.querySelector?.('.haui-device-rail'));
  if (!rail) return null;
  return rail.scrollWidth > rail.clientWidth + 1;
}
