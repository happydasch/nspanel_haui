import { html, nothing } from '../lit-import.js';

/**
 * @typedef {{ title?: unknown, subtitle?: unknown, leading?: unknown, badge?: unknown, actions?: unknown,
 *   onToggle?: () => void }} SurfaceHeading
 *   `leading` (a status icon) sits before the title, `badge` and `actions` after it.
 */

// Controls in the heading keep their own click; the expand chevron among them toggles once.
const OWN_CLICK = 'button, a, input, select, textarea, label, [role="tooltip"]';

/**
 * With `onToggle`, a click anywhere on the heading outside its controls folds
 * the card; the expand chevron in `actions` stays the keyboard control.
 *
 * @param {SurfaceHeading} options
 */
export function sectionHeading({ title, subtitle, leading, badge: badgeContent, actions, onToggle }) {
  const onClick = onToggle && ((/** @type {Event} */ event) => {
    if (!(/** @type {Element} */ (event.target)).closest(OWN_CLICK)) onToggle();
  });
  return html`<div class=${onToggle ? 'haui-surface-heading haui-surface-heading-toggle' : 'haui-surface-heading'}
    @click=${onClick || nothing}>
    ${leading || nothing}<div class="haui-surface-heading-copy"><h2>${title}</h2>${subtitle ? html`<p>${subtitle}</p>` : nothing}</div>
    ${badgeContent || nothing}${actions || nothing}
  </div>`;
}

/**
 * A dashboard card: an optional heading with actions above its body. Without a
 * body (a collapsed card) only the heading is drawn.
 *
 * @param {SurfaceHeading & { body?: unknown, variant?: string, className?: string }} options
 */
export function surface({
  title, subtitle, leading, badge: badgeContent, actions, onToggle, body, variant = 'plain', className = '',
}) {
  return html`<section class=${`haui-surface haui-surface-${variant} ${className}`.trim()}>
    ${title || subtitle || leading || badgeContent || actions
      ? sectionHeading({ title, subtitle, leading, badge: badgeContent, actions, onToggle }) : nothing}
    ${body ? html`<div class="haui-surface-body">${body}</div>` : nothing}
  </section>`;
}
