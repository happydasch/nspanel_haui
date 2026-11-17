// @ts-check
import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';

/**
 * One device-settings group as a tile: its icon, its name and one line of what
 * the group holds. A tile is a single native button, so Enter and Space open it
 * and its accessible name is the group name plus that line.
 *
 * @param {{ key: string, iconName: string, label: string, summary?: string,
 *   onClick: () => void }} options
 */
export function settingsTile({ key, iconName, label, summary = '', onClick }) {
  // The name sits between the icon and the chevron, what the group holds beneath it;
  // the title carries the whole name for a tile too narrow to wrap it.
  return html`<button type="button" class="haui-settings-tile"
      data-settings-tile=${key} title=${label} @click=${onClick}>
    <span class="haui-settings-tile-icon">${icon(iconName)}</span>
    <span class="haui-settings-tile-name">${label}</span>
    <span class="haui-settings-tile-go" aria-hidden="true">${icon('chevronRight')}</span>
    ${summary ? html`<span class="haui-settings-tile-value">${summary}</span>` : nothing}
  </button>`;
}
