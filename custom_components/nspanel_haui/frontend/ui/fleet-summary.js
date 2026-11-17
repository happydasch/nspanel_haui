// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';
import { deviceConnectionState } from '../device-status.js';

/** The connection tone of one device, as the summary strip paints it. */
function deviceTone(status) {
  return `is-${deviceConnectionState(status).tone}`;
}

/** A labelled figure on the strip's right: updates pending, integration version. */
function fact(label, value) {
  return html`<div><dt>${label}</dt><dd>${value}</dd></div>`;
}

/**
 * Render health and update figures from device status; until the first status
 * arrives (`pending`) the values are placeholders.
 * @param {{ total: number, online: number, updates: number, version: string, heading: unknown,
 *   action?: unknown, pending?: boolean }} stats
 */
export function fleetSummary({ total, online, updates, version, heading, action, pending = false }) {
  const placeholder = html`<span class="haui-stat-placeholder"></span><span class="haui-sr-only">${t('Loading')}</span>`;
  const value = (text) => (pending ? placeholder : text);
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
          <strong>${pending ? placeholder : html`<span aria-hidden="true">${online} / ${total}</span><span class="haui-sr-only">${
            t('{online} of {total} devices connected').replace('{online}', String(online)).replace('{total}', String(total))}</span>`}</strong>
        </div>
        <span>${health}</span>
      </div>
      <dl class="haui-fleet-facts">
        ${fact(t('Updates'), value(String(updates)))}
        ${fact(t('Integration version'), value(version))}
      </dl>
      ${action}
    </div>
  </section>`;
}

/**
 * One segment per device in its connection tone; the Device inventory keeps it
 * in its footer, under the table.
 * @param {{ devices: any[], total: number, online: number }} data
 */
export function fleetBar({ devices, total, online }) {
  if (!total) return nothing;
  return html`<div class="haui-fleet-bar" role="img"
    aria-label=${t('{online} of {total} devices connected')
    .replace('{online}', String(online)).replace('{total}', String(total))}>
    ${devices.map(({ name, status }) => html`<span class=${deviceTone(status)} title=${name}></span>`)}
  </div>`;
}
