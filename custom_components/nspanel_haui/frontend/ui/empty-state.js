import { html, nothing } from '../lit-import.js';
import { button } from './button.js';
import { icon } from './icon.js';

/** Render consistent empty, loading, or informational content. */
export function emptyState({
  title = '', message = '', iconName = 'info', action = null, actionLabel = '', className = '',
}) {
  return html`<div class=${`haui-empty-state ${className}`.trim()}>
    ${iconName ? icon(iconName, 'haui-empty-state-icon') : nothing}
    ${title ? html`<h2>${title}</h2>` : nothing}
    ${message ? html`<p>${message}</p>` : nothing}
    ${action && actionLabel ? button({ label: actionLabel, variant: 'primary', onClick: action }) : nothing}
  </div>`;
}
