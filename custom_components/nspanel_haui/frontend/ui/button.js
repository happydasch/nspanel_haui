import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';
import { t } from '../localize.js';

/**
 * Render a native button with shared dashboard classes and semantics.
 * `anchorKey` marks a control that owns an anchored popover. `detail` is
 * secondary text after the label, such as what the setting it opens holds.
 */
export function button({
  label, iconName = null, variant = 'outline', onClick, disabled = false, busy = false,
  type = 'button', className = '', title = '', anchorKey = null, id = null, detail = '',
}) {
  return html`<button type=${type} id=${id ?? nothing}
    class=${`haui-button ${variant ? `haui-button-${variant}` : ''} ${className}`.trim()}
    ?disabled=${disabled || busy} aria-busy=${busy ? 'true' : nothing}
    data-overlay-anchor=${anchorKey ?? nothing}
    title=${title || nothing} @click=${onClick || nothing}>
    ${iconName ? icon(iconName) : nothing}<span>${label}</span>${detail
      ? html` <span class="haui-button-detail">${detail}</span>` : nothing}</button>`;
}

/**
 * Icon-only button; the accessible label is always supplied explicitly.
 * @param {{ label: string, iconName: string, onClick?: ((event: MouseEvent) => void)|null, disabled?: boolean, className?: string, anchorKey?: string|null, expanded?: boolean, controls?: string }} options
 */
export function iconButton({
  label, iconName, onClick, disabled = false, className = '', anchorKey = null,
  expanded, controls,
}) {
  return html`<button type="button" class=${`haui-icon-button ${className}`.trim()}
    aria-label=${label} title=${label} ?disabled=${disabled}
    data-overlay-anchor=${anchorKey ?? nothing}
    aria-expanded=${expanded === undefined ? nothing : String(expanded === true)}
    aria-controls=${controls ?? nothing} @click=${onClick || nothing}>
    ${icon(iconName)}</button>`;
}

/**
 * The "+ Add …" row that appends an entry to a list (list items, schedule
 * entries, gestures). Every add row uses this one dashed, full-width
 * style so they read alike wherever they appear.
 */
export function addButton({ label, onClick, disabled = false, id = null, className = '' }) {
  return html`<button type="button" id=${id ?? nothing}
    class=${`haui-item-add-button ${className}`.trim()} ?disabled=${disabled}
    @click=${onClick || nothing}>+ ${label}</button>`;
}

/** The icon-only arrow that leaves a screen; `label` says where it goes. */
export function backButton({ label, onClick }) {
  return iconButton({ label, iconName: 'back', onClick, className: 'haui-back-button' });
}

/** The card-header chevron that expands or collapses a side-stack card. */
export function expandToggle(/** @type {boolean} */ expanded, /** @type {(() => void)|undefined} */ onToggle) {
  return iconButton({
    label: expanded ? t('Show less') : t('Show more'),
    iconName: expanded ? 'chevron-up' : 'chevron-down',
    onClick: onToggle,
    expanded,
    className: 'haui-expand-toggle',
  });
}
