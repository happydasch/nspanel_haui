import { html, nothing } from '../lit-import.js';
import { countBadge } from './badge.js';
import { icon } from './icon.js';

export function segmented({ label, options, value, onSelect, disabled = false }) {
  return html`<div class="haui-segmented" role="group" aria-label=${label}>
    ${options.map((option) => html`<button type="button"
      class=${`haui-segmented-option ${option.value === value ? 'active' : ''}`}
      aria-pressed=${option.value === value ? 'true' : 'false'}
      ?disabled=${disabled || option.disabled === true}
      @click=${() => onSelect?.(option.value)}>
      ${option.icon ? icon(option.icon) : nothing}
      <span>${option.label}</span>${option.count !== undefined ? countBadge(option.count) : nothing}
    </button>`)}
  </div>`;
}
