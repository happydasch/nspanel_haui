import { html, nothing } from '../lit-import.js';
import { button } from './button.js';
import { icon } from './icon.js';

export function emptyState({ title, message, iconName = 'info', action = null, actionLabel = '' }) {
  return html`<div class="haui-empty-state">
    ${icon(iconName, 'haui-empty-state-icon')}
    <h2>${title}</h2>
    ${message ? html`<p>${message}</p>` : nothing}
    ${action && actionLabel ? button({ label: actionLabel, variant: 'primary', onClick: action }) : nothing}
  </div>`;
}
