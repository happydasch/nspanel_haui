// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';

/**
 * A figure on the strip's right: a tinted glyph, its label and its value. The
 * tone repeats what the value already says, so colour is never the only cue.
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

/**
 * Render health and update figures from device status; until the first status
 * arrives (`pending`) the values are placeholders.
 * @param {{ total: number, online: number, updates: number, version: string, heading: unknown,
 *   action?: unknown, pending?: boolean, mixedVersions?: boolean }} stats
 *   `mixedVersions` says the devices report different integration versions, which the
 *   version figure warns about.
 */
export function fleetSummary({
  total, online, updates, version, heading, action, pending = false, mixedVersions = false,
}) {
  const placeholder = html`<span class="haui-stat-placeholder"></span><span class="haui-sr-only">${t('Loading')}</span>`;
  const value = (text) => (pending ? placeholder : text);
  const tone = pending ? 'neutral' : online === total ? 'success' : online ? 'warning' : 'danger';
  // Zero pending updates reads as healthy; a waiting one takes the warning tone.
  const updatesTone = pending ? 'neutral' : updates ? 'warn' : 'good';
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
          <strong>${pending ? placeholder : html`<span aria-hidden="true">${online} / ${total}</span><span class="haui-sr-only">${
            t('{online} of {total} devices connected').replace('{online}', String(online)).replace('{total}', String(total))}</span>`}</strong>
        </div>
        <span>${health}</span>
      </div>
      <div class="haui-fleet-facts">
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
      </div>
      ${action}
    </div>
  </section>`;
}
