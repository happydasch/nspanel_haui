// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { emptyState } from './empty-state.js';
import { icon } from './icon.js';

/**
 * The preview stage: the dark bezel that holds a screen template, the two
 * hardware buttons and the entity tooltip. The preview's tools are the
 * Diagnostics card's.
 *
 * It only draws; the workspace owns the session, the scaling and the handlers.
 *
 * @param {{ screen?: unknown, hardware?: unknown, tooltip?: unknown, live?: boolean,
 *   state?: 'ready'|'loading'|'no-panel'|'error'|'disconnected', framePad?: number,
 *   hardwareHeight?: number, error?: string }} options
 */
export function previewStage({
  screen = nothing, hardware = nothing, tooltip = nothing, live = false,
  state = 'ready', framePad = 8, hardwareHeight = 60, error = '',
}) {
  const body = state === 'no-panel'
    ? emptyState({
      iconName: 'screen',
      title: t('No panel to preview'),
      message: t('Add a panel or assign a home panel to see a preview'),
    })
    : state === 'error'
      ? html`<div class="haui-preview-error" role="alert">
          ${icon('alert-circle-outline')}
          <span>${error || t('The preview could not be rendered')}</span>
        </div>`
      : html`<div class="haui-preview-bezel" style=${`--vp-frame-pad:${framePad}px;--vp-hw-height:${hardwareHeight}px;`}>
          ${screen}
          ${hardware}
          ${tooltip}
        </div>`;
  return html`<section class=${`haui-preview-stage ${live ? 'is-live' : ''}`.trim()}
    aria-label=${t('Panel preview')} aria-busy=${state === 'loading' ? 'true' : 'false'}>
    ${state === 'loading' ? html`<div class="haui-preview-loading" aria-live="polite">${t('Starting the live preview…')}</div>` : body}
  </section>`;
}
