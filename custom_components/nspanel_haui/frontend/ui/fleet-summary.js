// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';

/**
 * A figure on the strip: a tinted glyph, its label and its value. The tone
 * repeats what the value already says, so colour is never the only cue.
 * @param {{ iconName: string, label: string, value: unknown, tone?: string }} options
 */
function fact({ iconName, label, value, tone = 'neutral' }) {
  return html`<div class=${`haui-fleet-fact is-${tone}`}>
    <span class="haui-fleet-fact-icon" aria-hidden="true">${icon(iconName)}</span>
    <span class="haui-fleet-fact-body">
      <span class="haui-fleet-fact-label">${label}</span>
      <span class="haui-fleet-fact-value">${value}</span>
    </span>
  </div>`;
}

/** A value the first status has not filled in yet: a placeholder the size of the number. */
function pendingValue() {
  return html`<span class="haui-stat-placeholder"></span><span class="haui-sr-only">${t('Loading')}</span>`;
}

/**
 * The updates-pending and integration-version figures, which close the inventory
 * as a footer strip under its table. Until the first status arrives (`pending`)
 * both values are placeholders; `mixedVersions` says the devices report different
 * integration versions, which the version figure warns about.
 * @param {{ updates: number, version: string, pending?: boolean, mixedVersions?: boolean }} stats
 */
export function fleetFacts({ updates, version, pending = false, mixedVersions = false }) {
  const value = (text) => (pending ? pendingValue() : text);
  // Zero pending updates reads as healthy; a waiting one takes the warning tone.
  const updatesTone = pending ? 'neutral' : updates ? 'warn' : 'good';
  return html`<div class="haui-fleet-facts">
    ${fact({
      iconName: pending ? 'refresh' : updates ? 'download' : 'check',
      label: t('Updates'),
      value: value(String(updates)),
      tone: updatesTone,
    })}
    ${fact({
      iconName: pending ? 'refresh' : mixedVersions ? 'alert' : 'tag',
      label: t('Integration version'),
      value: value(version),
      tone: mixedVersions && !pending ? 'warn' : 'neutral',
    })}
  </div>`;
}

/**
 * Render the fleet's health as the inventory card's header: the health glyph, the
 * heading with the online count, the sentence under it and the card's action. The
 * update and version figures sit under the table instead (`fleetFacts`), so the
 * header carries what needs no scrolling. Until the first status arrives
 * (`pending`) the count is a placeholder.
 * @param {{ total: number, online: number, heading: unknown, action?: unknown, pending?: boolean }} stats
 */
export function fleetSummary({ total, online, heading, action, pending = false }) {
  const tone = pending ? 'neutral' : online === total ? 'success' : online ? 'warning' : 'danger';
  const health = pending ? ''
    : online === total ? t('All devices connected')
      : online ? t('{count} offline').replace('{count}', String(total - online))
        : t('No device connected');
  return html`<section class=${`haui-fleet-summary haui-fleet-band-${tone} ${
    pending ? 'haui-fleet-summary-pending' : ''}`}
    aria-busy=${pending ? 'true' : 'false'}>
    <div class="haui-fleet-band-top">
      <span class="haui-fleet-orb">${icon('lan-connect')}</span>
      <div class="haui-fleet-lead">
        <div class="haui-fleet-lead-heading">
          ${heading}
          <strong>${pending ? pendingValue() : html`<span aria-hidden="true">${online} / ${total}</span><span class="haui-sr-only">${
            t('{online} of {total} devices connected').replace('{online}', String(online)).replace('{total}', String(total))}</span>`}</strong>
        </div>
        <span>${health}</span>
      </div>
      ${action}
    </div>
  </section>`;
}
