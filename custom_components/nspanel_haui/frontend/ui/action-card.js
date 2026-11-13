// @ts-check
import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';

/**
 * The lead card of a Device view: what the view is about and the actions to
 * take next. It is tinted and never collapses, so it stands apart from the
 * side-stack cards; the Device layout puts it above the side stack, and above
 * the workspace once the layout is one column.
 *
 * `tool` is an icon-only control at the end of the heading (the device settings).
 *
 * @param {{ iconName: string, title: unknown, subtitle?: unknown, tool?: unknown, primary: unknown,
 *   secondary?: unknown[], stacked?: boolean, inlineActions?: boolean, note?: unknown, management?: unknown }} options
 */
export function actionCard({
  iconName, title, subtitle, tool, primary, secondary = [], stacked = false, inlineActions = false, note, management,
}) {
  const innerClasses = [
    'haui-action-card-inner',
    ...(note ? ['has-note'] : []),
    ...(management ? ['has-management'] : []),
  ].join(' ');
  return html`<section class="haui-action-card">
    <div class=${innerClasses}>
      <span class="haui-action-card-icon">${icon(iconName)}</span>
      <div class="haui-action-card-copy"><h2>${title}</h2>${subtitle ? html`<p>${subtitle}</p>` : nothing}</div>
      ${tool ? html`<div class="haui-action-card-tool">${tool}</div>` : nothing}
      <div class=${`haui-action-card-actions${stacked ? ' is-stacked' : ''}${inlineActions ? ' is-inline' : ''}`}>
        ${primary}
        ${secondary.length ? html`<div class="haui-action-card-secondary">${secondary}</div>` : nothing}
      </div>
      ${note ? html`<p class="haui-action-card-note">${note}</p>` : nothing}
      ${management ? html`<div class="haui-action-card-management">${management}</div>` : nothing}
    </div>
  </section>`;
}
